"""Source-preserving link-node presentation shared by runtime and publisher.

No renderer or optional parser dependencies: a lexical scanner identifies code,
Markdown destinations and HTML attribute spans, and edits only those spans.
Canonical corpus bytes never pass through this module before retrieval.
"""
from __future__ import annotations

import html
from html.parser import HTMLParser
import re
from urllib.parse import unquote, urljoin, urlsplit, urlunsplit


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
_TAG = re.compile(r'''</?[A-Za-z][^<>]*?(?:"[^"]*"|'[^']*'|[^'"<>])*?>''')
_AUTOLINK = re.compile(r"<https?://[^<>\s]+>", re.I)
_FIELD = re.compile(r"(?:Markdown URL|URL|HTML):[ \t]+(https?://[^\s<>]+)")
_FENCE = re.compile(r" {0,3}(`{3,}|~{3,})[^\n]*\n?")
_REF = re.compile(r" {0,3}\[(?:\\.|[^\]\\\n])+\]:[ \t]*(?:\n[ \t]*)?")
_BACKTICKS = re.compile(r"`+")


class LinkCatalog:
    def __init__(self, canonical_site_url, site_url, page_paths):
        self.canonical = canonical_site_url
        self.site = site_url
        self.pages = page_paths
        self.paths = set(AUXILIARY_PATHS)
        for page in page_paths.values():
            self.paths.update((page["site_path"], page["markdown_path"]))

    def link(self, value, *, context=None, validate=False):
        # Decode Markdown escapes/entities only for URL interpretation; preserve
        # the original lexical spelling if this is not an internal link.
        decoded = html.unescape(re.sub(r"\\([!\"#$%&'()*+,\-./:;<=>?@\[\]\\^_`{|}~])", r"\1", value))
        if not decoded or decoded.startswith("#"):
            return value
        base = urlsplit(self.canonical)
        target = urlsplit(urljoin(context or self.canonical, decoded))
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


class _HTMLTag(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=False)
        self.attributes = set()

    def handle_starttag(self, tag, attrs):
        self.attributes = {name for name, _ in attrs if name in {"href", "src", "poster", "action", "cite"}}


def _destination(text, start):
    """Return destination span, respecting escaped/balanced parentheses."""
    if start >= len(text):
        return None
    if text[start] == "<":
        end = start + 1
        while end < len(text):
            if text[end] == "\\":
                end += 2
                continue
            if text[end] == ">":
                return start + 1, end
            if text[end] == "\n":
                return None
            end += 1
        return None
    end, depth = start, 0
    while end < len(text):
        char = text[end]
        if char == "\\":
            end += 2
            continue
        if char.isspace() or (char == ")" and depth == 0):
            break
        if char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
        end += 1
    return (start, end) if end > start and depth == 0 else None


def _markdown(text, catalog, *, context=None, generated_fields=False, validate=False):
    edits = []
    i, bracket_depth = 0, 0

    def link(start, end, *, attribute=False):
        value = text[start:end]
        replacement = catalog.link(value, context=context, validate=validate)
        if replacement != value:
            edits.append((start, end, html.escape(replacement, quote=True) if attribute else replacement))

    while i < len(text):
        line_start = i == 0 or text[i - 1] == "\n"
        if line_start:
            if generated_fields and text.startswith("External sources:", i):
                end = text.find("\n", i)
                i = end + 1 if end >= 0 else len(text)
                while text.startswith("- ", i):
                    end = text.find("\n", i)
                    i = end + 1 if end >= 0 else len(text)
                continue
            fence = _FENCE.match(text, i)
            if fence:
                marker = fence[1]
                closing = re.compile(r"^ {0,3}" + re.escape(marker[0]) + "{" + str(len(marker)) + r",}[ \t]*$", re.M).search(text, fence.end())
                i = closing.end() if closing else len(text)
                continue
            if text.startswith(("    ", "\t"), i):
                end = text.find("\n", i)
                i = end + 1 if end >= 0 else len(text)
                continue
            reference = _REF.match(text, i)
            if reference:
                span = _destination(text, reference.end())
                if span:
                    link(*span)
                    i = span[1] + (text[reference.end()] == "<")
                    continue
        if text[i] == "\\":
            i += 2
            continue
        if text[i] == "`":
            marker = _BACKTICKS.match(text, i)[0]
            closing = re.compile(r"(?<!`)" + re.escape(marker) + r"(?!`)").search(text, i + len(marker))
            i = closing.end() if closing else i + len(marker)
            continue
        if text.startswith("<!--", i):
            end = text.find("-->", i + 4)
            i = end + 3 if end >= 0 else len(text)
            continue
        if text[i] == "<":
            auto = _AUTOLINK.match(text, i)
            if auto:
                link(i + 1, auto.end() - 1)
                i = auto.end()
                continue
            tag = _TAG.match(text, i)
            if tag:
                raw = tag[0]
                protected = re.match(r"<(code|pre|script|style)(?:\s|>)", raw, re.I)
                if protected:
                    closing = re.compile(r"</" + protected[1] + r"\s*>", re.I).search(text, tag.end())
                    i = closing.end() if closing else len(text)
                    continue
                parser = _HTMLTag()
                parser.feed(raw)
                for attr in _ATTR.finditer(raw):
                    if attr[1].lower() in parser.attributes:
                        group = next(n for n in (3, 4, 5) if attr[n] is not None)
                        link(i + attr.start(group), i + attr.end(group), attribute=True)
                i = tag.end()
                continue
        if generated_fields:
            field = _FIELD.match(text, i)
            line_prefix = text[text.rfind("\n", 0, i) + 1:i] if field else ""
            if field and (line_start or (text.startswith("HTML:", i) and line_prefix.startswith("- ["))):
                end = field.end(1)
                # Generated list prose appends a sentence period to HTML URL.
                if text[end - 1] == ".":
                    end -= 1
                if line_start and text.startswith("URL:", i):
                    context = text[field.start(1):end]
                link(field.start(1), end)
                i = field.end()
                continue
        if text[i] == "[":
            bracket_depth += 1
        elif text[i] == "]" and bracket_depth:
            bracket_depth -= 1
            if text.startswith("](", i):
                start = i + 2
                while start < len(text) and text[start].isspace():
                    start += 1
                span = _destination(text, start)
                if span:
                    link(*span)
                    i = span[1] + (text[start] == "<")
                    continue
        i += 1
    parts, previous = [], 0
    for start, end, replacement in edits:
        parts.extend((text[previous:start], replacement))
        previous = end
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
