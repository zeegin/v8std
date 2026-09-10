"""Source-preserving CommonMark link presentation shared by runtime/publisher.

The pinned parser decides syntax; instrumentation retains source offsets through
normalization and container indentation. Only accepted destination spans change.
Neither canonical retrieval input nor non-link prose is rendered/reserialized.
"""
from __future__ import annotations
from array import array
from bisect import bisect_right
from difflib import SequenceMatcher
import html
from html.parser import HTMLParser
import re
from types import SimpleNamespace
from urllib.parse import unquote, urljoin, urlsplit, urlunsplit

from markdown_it import MarkdownIt
from markdown_it.rules_block import StateBlock, reference
from markdown_it.rules_inline import link, image, autolink, html_inline, text as inline_text


class PresentationError(ValueError):
    """Bounded publisher error, with no source URL or document payload."""
    code = "unresolved_internal_link"

    def __init__(self):
        super().__init__(self.code)


# Explicit published auxiliaries, not a prefix allowlist or searchable pages.
AUXILIARY_PATHS = frozenset({"llms.txt", "llms-full.txt", "ai/pages.jsonl",
                           "LICENSES/", "LICENSES/LGPL-3.0.txt",
                           "LICENSES/GPL-3.0.txt", "LICENSES/EPL-2.0.txt"})

_ATTR = re.compile(r'''([^\s=<>/]+)(\s*=\s*)(?:"([^"]*)"|'([^']*)'|([^\s>]+))''')
_FIELD = re.compile(r"(?:Markdown URL|URL|HTML):[ \t]+(https?://[^\s<>]+)")
_PROVENANCE = re.compile(r"^External sources:[^\n]*(?:\n- [^\n]*)*", re.M)
_PROTECTED_TAGS = {"code", "pre", "script", "style"}


class LinkCatalog:
    def __init__(self, canonical_site_url, site_url, page_paths):
        self.canonical = canonical_site_url
        self.site = site_url
        self.pages = page_paths
        self.paths = set(AUXILIARY_PATHS)
        for page in page_paths.values():
            self.paths.update((page["site_path"], page["markdown_path"]))

    def link(self, value, *, context=None, validate=False):
        # Callers supply the value interpreted in its own Markdown/HTML/JSON
        # context. Applying a second universal unescape corrupts URL suffixes.
        if not value or value.startswith("#"):
            return value
        base = urlsplit(self.canonical)
        target = urlsplit(urljoin(context or self.canonical, value))
        if (target.scheme, target.netloc) != (base.scheme, base.netloc):
            return value
        path = target.path
        # Encoded separators/dot traversal must not turn a known path into an
        # alternate route. Relative ../ links resolve normally inside the base.
        unsafe = re.search(r"%(?:2f|5c|25|2e)", path, re.I) or "\\" in path
        relative = unquote(path[len(base.path):]) if path.startswith(base.path) else None
        if unsafe or relative not in self.paths:
            if validate:
                raise PresentationError()
            return value
        result = urlsplit(urljoin(self.site, relative))
        return urlunsplit((result.scheme, result.netloc, result.path, target.query, target.fragment))

    def lookup(self, value):
        """Translate configured local page URLs to the original lookup key."""
        target, base = urlsplit(value), urlsplit(self.site)
        if (target.scheme, target.netloc) == (base.scheme, base.netloc) and target.path.startswith(base.path):
            path = target.path[len(base.path):]
            if path in self.paths - AUXILIARY_PATHS:
                return urljoin(self.canonical, path)
        return value


class _MappedText(str):
    """Original offsets survive parser slicing and container indentation.

    Contiguous slices use ranges; arrays join lines across removed prefixes.
    Virtual indentation has offset -1. This is source mapping, not a grammar.
    """
    def __new__(cls, value, offsets=None):
        obj = super().__new__(cls, value)
        obj.offsets = range(len(value)) if offsets is None else offsets
        return obj

    def __getitem__(self, key):
        value = super().__getitem__(key)
        return _MappedText(value, self.offsets[key]) if isinstance(key, slice) else value

    def __add__(self, other):
        return self.combine((self, other))

    def __radd__(self, other):
        return self.combine((other, self))

    @classmethod
    def combine(cls, parts):
        parts = list(parts)
        if len(parts) == 1:
            return parts[0]
        offsets = array("i")
        for part in parts:
            offsets.extend(part.offsets if isinstance(part, cls) else [-1] * len(part))
        return cls("".join(parts), offsets)

    def strip(self, chars=None):
        start = len(self) - len(str.lstrip(self, chars))
        end = len(str.rstrip(self, chars))
        return self[start:max(start, end)]

    def span(self, start=0, end=None):
        end = len(self) if end is None else end
        if end <= start:
            return None
        offsets = self.offsets[start:end]
        # Never delete a removed container prefix with a destination edit.
        if offsets[0] < 0 or offsets[-1] - offsets[0] != len(offsets) - 1:
            return None
        return offsets[0], offsets[-1] + 1


def _normalize(state):
    source = state.src
    parts, previous = [], 0
    for match in re.finditer(r"\r\n?|\x00", source):
        parts.append(_MappedText(source[previous:match.start()], range(previous, match.start())))
        parts.append(_MappedText("\ufffd" if match[0] == "\x00" else "\n", [match.start()]))
        previous = match.end()
    parts.append(_MappedText(source[previous:], range(previous, len(source))))
    state.src = _MappedText.combine(parts)


def _block(state):
    block = StateBlock(state.src, state.md, state.env, state.tokens)
    original = block.getLines

    def get_lines(begin, end, indent, keep_last):
        parts = []
        for line in range(begin, end):
            keep = line + 1 < end or keep_last
            rendered = original(line, line + 1, indent, keep)
            raw = block.src[block.bMarks[line]:block.eMarks[line] + int(keep)]
            if raw.endswith(rendered):
                parts.append(raw[len(raw) - len(rendered):])
                continue
            common = 0
            while common < min(len(raw), len(rendered)) and raw[-common - 1] == rendered[-common - 1]:
                common += 1
            parts.append(_MappedText.combine((
                rendered[:len(rendered) - common],
                raw[len(raw) - common:] if common else _MappedText(""),
            )))
        return _MappedText.combine(parts)

    block.getLines = get_lines
    try:
        state.md.block.tokenize(block, block.line, block.lineMax)
    finally:
        # The adapter closes over StateBlock; detach it even on parser failure
        # so source maps and token trees do not wait for cyclic GC.
        del block.getLines


class _HTMLNodes(HTMLParser):
    """HTML decides attributes; edits retain their original quoting context."""
    def __init__(self, source, nodes, tags):
        super().__init__(convert_charrefs=False)
        self.source, self.nodes, self.tags = source, nodes, tags
        self.lines = [0] + [match.end() for match in re.finditer("\n", source)]

    def source_offset(self):
        line, column = self.getpos()
        return self.lines[line - 1] + column

    def handle_starttag(self, tag, attrs):
        start = self.source_offset()
        raw = self.get_starttag_text()
        # Only the tag's start anchors protection. A multiline opening tag
        # may cross removed quote/list prefixes without making its code live.
        span = self.source.span(start, start + 1)
        if span:
            self.tags.append((*span, tag, False))
        allowed = {key for key, _ in attrs if key in {"href", "src", "poster", "action", "cite"}}
        for match in _ATTR.finditer(raw):
            if match[1].lower() not in allowed:
                continue
            group = next(n for n in (3, 4, 5) if match[n] is not None)
            raw_value = self.source[start + match.start(group):start + match.end(group)]
            span = raw_value.span()
            value = html.unescape(match[group])
            if not span and raw_value and raw_value.offsets[0] >= 0 and raw_value.offsets[-1] >= 0:
                # Multiline quoted destinations can cross container prefixes.
                # Retain their source map for edit projection, not a broad cut.
                span = raw_value.offsets[0], raw_value.offsets[-1] + 1
                value = _HTMLValue(value, raw_value)
            if span:
                self.nodes.append((*span, value, "html_unquoted" if group == 5 else "html"))

    def handle_endtag(self, tag):
        start = self.source_offset()
        span = self.source.span(start, start + 1)
        if span:
            self.tags.append((*span, tag, True))


class _HTMLValue(str):
    def __new__(cls, value, raw):
        obj = super().__new__(cls, value)
        obj.raw = raw
        return obj

    def edits(self, replacement):
        """Project destination-only edits around structural source gaps.

        URL parsing ignores literal CR/LF. Keep those physical line breaks and
        removed container markers so rebasing never joins Markdown containers.
        Entity escaping still follows the attribute's actual quoting context.
        """
        for operation, start, end, new_start, new_end in SequenceMatcher(
                None, str(self.raw), replacement).get_opcodes():
            if operation == "equal":
                continue
            value = replacement[new_start:new_end]
            if start == end:
                offset = self.raw.offsets[start] if start < len(self.raw) else self.raw.offsets[-1] + 1
                if offset >= 0:
                    yield offset, offset, value
                continue
            spans = []
            for position in range(start, end):
                offset = self.raw.offsets[position]
                if offset < 0 or self.raw[position] == "\n":
                    continue
                if spans and spans[-1][1] == offset:
                    spans[-1] = (spans[-1][0], offset + 1)
                else:
                    spans.append((offset, offset + 1))
            for number, (begin, finish) in enumerate(spans):
                yield begin, finish, value if number == 0 else ""


class _FirstHTMLTag(HTMLParser):
    """Recognize HTML attributes also accepted by HTML outside CommonMark's
    stricter inline-tag grammar (notably unquoted query '=' characters).
    """
    def handle_starttag(self, tag, attrs):
        if self.getpos() == (1, 0):
            self.first = self.get_starttag_text()
        raise _TagFinished

    def handle_data(self, data):
        raise _TagFinished


class _TagFinished(Exception):
    pass


def _merged_spans(spans):
    merged = []
    for start, end in sorted(spans):
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(end, merged[-1][1]))
        else:
            merged.append((start, end))
    return merged


def _covered(offset, spans):
    position = bisect_right(spans, (offset, float("inf"))) - 1
    return position >= 0 and offset < spans[position][1]


def _html_inline(state, silent):
    if html_inline(state, silent):
        return True
    if not re.match(r"<[A-Za-z]", state.src[state.pos:state.pos + 2]):
        return False
    parser = _FirstHTMLTag()
    parser.first = None
    try:
        parser.feed(str(state.src[state.pos:]))
    except _TagFinished:
        pass
    if parser.first is None:
        return False
    end = state.pos + len(parser.first)
    if not silent:
        token = state.push("html_inline", "", 0)
        token.content = state.src[state.pos:end]
    state.pos = end
    return True


def _link_nodes(source, generated_fields):
    """Instrument successful parser rules, never error-recovery guesses."""
    md = MarkdownIt("commonmark")
    nodes, tags, text_spans, frames = [], [], [], []
    md.core.ruler.at("normalize", _normalize)
    md.core.ruler.at("block", _block)
    helpers = md.helpers
    md.helpers = SimpleNamespace(parseLinkLabel=helpers.parseLinkLabel,
                                 parseLinkTitle=helpers.parseLinkTitle)

    def destination(src, pos, maximum):
        result = helpers.parseLinkDestination(src, pos, maximum)
        if result.ok and frames and isinstance(src, _MappedText):
            angle = src[pos:pos + 1] == "<"
            span = src.span(pos + int(angle), result.pos - int(angle))
            if span:
                frames[-1].append((*span, result.str, "angle" if angle else "markdown"))
        return result

    md.helpers.parseLinkDestination = destination

    def ref_rule(state, begin, end, silent):
        frames.append([])
        accepted = reference(state, begin, end, silent)
        candidates = frames.pop()
        if accepted and not silent:
            nodes.extend(candidates)
        return accepted

    md.block.ruler.at("reference", ref_rule)

    def wrap(rule, kind):
        def run(state, silent):
            start, count = state.pos, len(state.tokens)
            frames.append([])
            accepted = rule(state, silent)
            candidates = frames.pop()
            if not accepted or silent:
                return accepted
            src = state.src
            emitted = state.tokens[count:]
            if kind in {"link", "image"}:
                urls = {token.attrGet("href") or token.attrGet("src") for token in emitted
                        if token.type in {"link_open", "image"}}
                end_offset = src.offsets[state.pos - 1] + 1
                nodes.extend(candidate for candidate in candidates
                             if candidate[1] <= end_offset and state.md.normalizeLink(candidate[2]) in urls)
            elif kind == "autolink":
                span = src.span(start + 1, state.pos - 1)
                if span:
                    nodes.append((*span, str(src[start + 1:state.pos - 1]), "autolink"))
            elif kind == "html_inline":
                _HTMLNodes(src[start:state.pos], nodes, tags).feed(str(src[start:state.pos]))
            elif generated_fields:
                span = src.span(start, state.pos)
                if span:
                    text_spans.append(span)
            return accepted
        return run

    for name, rule in (("link", link), ("image", image), ("autolink", autolink),
                       ("html_inline", _html_inline), ("text", inline_text)):
        md.inline.ruler.at(name, wrap(rule, name))
    tokens = md.parse(source)
    for token in tokens:
        if token.type == "html_block":
            _HTMLNodes(token.content, nodes, tags).feed(str(token.content))
    protected, opened = [], []
    for start, end, tag, closing in sorted(tags):
        if tag not in _PROTECTED_TAGS:
            continue
        if not closing:
            opened.append(start)
        elif opened:
            protected.append((opened.pop(), end))
    protected.extend((start, len(source)) for start in opened)
    if generated_fields:
        protected.extend(match.span() for match in _PROVENANCE.finditer(source))
        text_spans = _merged_spans(text_spans)
        for match in _FIELD.finditer(source):
            prefix = source[source.rfind("\n", 0, match.start()) + 1:match.start()]
            if prefix and not (match[0].startswith("HTML:") and prefix.startswith("- [")):
                continue
            if not _covered(match.start(), text_spans):
                continue
            start, end = match.span(1)
            if source[end - 1] == ".":
                end -= 1
            nodes.append((start, end, source[start:end], "context" if match[0].startswith("URL:") else "field"))
    protected = _merged_spans(protected)
    return [node for node in sorted(set(nodes)) if not _covered(node[0], protected)], md


def _escape_destination(value, kind, md):
    if kind.startswith("html"):
        value = html.escape(value, quote=True)
        if kind == "html_unquoted":
            value = re.sub(r"[\s=\x60]", lambda m: "&#" + str(ord(m[0])) + ";", value)
        return value
    if kind in {"field", "context"}:
        return value
    value = md.normalizeLink(value)
    if kind != "autolink":
        value = value.replace("&", "&amp;")
        if kind == "markdown":
            value = re.sub(r"[\\()]", lambda m: "\\" + m[0], value)
    return value


def _markdown(text, catalog, *, context=None, generated_fields=False, validate=False):
    nodes, md = _link_nodes(text, generated_fields)
    parts, previous = [], 0
    for start, end, value, kind in nodes:
        if kind == "context":
            context = value
        replacement = catalog.link(value, context=context, validate=validate)
        if replacement == value:
            continue
        if start < previous:
            continue
        escaped = _escape_destination(replacement, kind, md)
        edits = value.edits(escaped) if isinstance(value, _HTMLValue) else [(start, end, escaped)]
        for begin, finish, content in edits:
            parts.extend((text[previous:begin], content))
            previous = finish
    parts.append(text[previous:])
    return "".join(parts)


def present_markdown(text, *, canonical_site_url, site_url, page_paths,
                     context=None, generated_fields=False):
    return _markdown(text, LinkCatalog(canonical_site_url, site_url, page_paths),
                     context=context, generated_fields=generated_fields)


def validate_links(text, *, canonical_site_url, page_paths, context=None, generated_fields=False):
    _markdown(text, LinkCatalog(canonical_site_url, canonical_site_url, page_paths),
              context=context, generated_fields=generated_fields, validate=True)


def present_result(value, *, canonical_site_url, site_url, page_paths):
    catalog = LinkCatalog(canonical_site_url, site_url, page_paths)

    def visit(item, context=None):
        if isinstance(item, list):
            return [visit(child, context) for child in item]
        if not isinstance(item, dict):
            return item
        page = page_paths.get(item.get("id"))
        if page:
            context = urljoin(canonical_site_url, page["site_path"])
        result = {}
        for key, child in item.items():
            if key in {"url", "markdown_url"} and isinstance(child, str):
                path_key = "site_path" if key == "url" else "markdown_path"
                if page:
                    base, suffix = urlsplit(urljoin(site_url, page[path_key])), urlsplit(child)
                    result[key] = urlunsplit((base.scheme, base.netloc, base.path, suffix.query, suffix.fragment))
                else:
                    result[key] = catalog.link(child, context=context)
            elif key == "body_markdown" and isinstance(child, str):
                result[key] = _markdown(child, catalog, context=context)
            else:
                result[key] = visit(child, context)
        return result

    return visit(value)
