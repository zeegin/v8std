"""Separate SuperFences placeholders before Markdown builds paragraphs."""

import re
from xml.etree import ElementTree as ET

from markdown import Markdown, util
from markdown.blockprocessors import BlockProcessor
from markdown.extensions import Extension
from markdown.treeprocessors import Treeprocessor
from pymdownx.superfences import SuperFencesCodeExtension


PLACEHOLDER = re.compile(util.HTML_PLACEHOLDER % r'[0-9]+')


def split_fence_blocks(md: Markdown, block: str) -> list[str]:
    """Partition recognized fences without editing their source or HTML stash."""
    return _split_fence_blocks(md, block, in_paragraph=False)


def _split_fence_blocks(md, block, *, in_paragraph):
    # Resolve at parse time: Zensical does not preserve extension registration order.
    extension = next((e for e in md.registeredExtensions
                      if isinstance(e, SuperFencesCodeExtension)), None)
    if extension is None:
        raise RuntimeError('v8std Markdown extension requires pymdownx.superfences')
    parts: list[str] = []
    pending: list[str] = []
    for line in block.split('\n'):
        token = line.strip()
        indent = len(line) - len(line.lstrip(' '))
        recognized = (
            # During block parsing, leave indented-code recovery to SuperFences.
            # Inside a completed paragraph that decision has already been made.
            (in_paragraph or indent < md.tab_length)
            and PLACEHOLDER.fullmatch(token) is not None
            and extension.stash.get(token[1:-1]) is not None
        )
        if recognized:
            if pending:
                parts.append('\n'.join(pending))
                pending = []
            parts.append(line)
        else:
            pending.append(line)
    if pending:
        parts.append('\n'.join(pending))
    return parts if len(parts) > 1 else [block]


class FenceBoundaryProcessor(BlockProcessor):
    def test(self, parent, block):
        return len(split_fence_blocks(self.parser.md, block)) > 1

    def run(self, parent, blocks):
        block = blocks.pop(0)
        self.parser.parseBlocks(parent, split_fence_blocks(self.parser.md, block))


class SetextFenceBoundaryProcessor(BlockProcessor):
    """Keep a recognized fence from becoming the text of a Setext heading."""

    def test(self, parent, block):
        if not self.parser.blockprocessors['setextheader'].test(parent, block):
            return False
        # Only the heading candidate matters; leave the remaining block intact.
        candidate = '\n'.join(block.split('\n', 2)[:2])
        return len(split_fence_blocks(self.parser.md, candidate)) > 1

    def run(self, parent, blocks):
        blocks[:1] = blocks[0].split('\n', 1)


class ListFenceBoundaryProcessor(Treeprocessor):
    """Separate paragraphs created by a later tight-to-loose list transition."""

    def run(self, root):
        for item in root.iter('li'):
            for paragraph in list(item):
                # OListProcessor wraps li.text/last-child.tail in text-only p
                # nodes after the block processor has already run. Inline markup
                # has not been parsed yet, so it stays with its original text.
                if paragraph.tag != 'p' or len(paragraph) or not paragraph.text:
                    continue
                parts = _split_fence_blocks(self.md, paragraph.text, in_paragraph=True)
                if len(parts) == 1:
                    continue
                index = list(item).index(paragraph)
                tail = paragraph.tail
                paragraph.text = parts[0].lstrip()
                paragraph.tail = None
                for offset, part in enumerate(parts[1:], 1):
                    paragraph = ET.Element('p')
                    paragraph.text = part.lstrip()
                    item.insert(index + offset, paragraph)
                paragraph.tail = tail


class FenceBoundaryExtension(Extension):
    def extendMarkdown(self, md):
        md.registerExtension(self)
        # Guard only recognized-marker Setext candidates (Setext is 60).
        # Indented code still runs first; container syntax cannot match this guard.
        md.parser.blockprocessors.register(
            SetextFenceBoundaryProcessor(md.parser), 'v8std_setext_fence_boundary', 61,
        )
        # Containers and indented code run first; the paragraph processor is 10.
        md.parser.blockprocessors.register(
            FenceBoundaryProcessor(md.parser), 'v8std_fence_boundary', 11,
        )
        # Finish boundaries after list wrapping, before inline parsing (20).
        # Placeholder-only paragraphs use the existing RawHtmlPostprocessor.
        md.treeprocessors.register(
            ListFenceBoundaryProcessor(md), 'v8std_list_fence_boundary', 25,
        )


def makeExtension(**kwargs):
    return FenceBoundaryExtension(**kwargs)
