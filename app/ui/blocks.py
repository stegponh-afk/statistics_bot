"""HTML-ish screen text (see app.texts.ru) -> Bot API rich blocks.

Ported from the reference bot's app/branding.py: the first line becomes a
SectionHeading when it's a single bold span (every screen title follows that
shape), SEPARATOR lines become real dividers, <blockquote> spans become
block quotations, and everything else is one paragraph per non-blank line.
"""

import re
from html.parser import HTMLParser

from aiogram.types import (
    InputRichBlockBlockQuotation,
    InputRichBlockDivider,
    InputRichBlockParagraph,
    InputRichBlockSectionHeading,
    InputRichBlockTable,
    InputRichBlockUnion,
    RichBlockTableCell,
    RichTextBold,
    RichTextCode,
    RichTextItalic,
    RichTextUnion,
)

from app.texts.ru import SEPARATOR

_INLINE_TAGS = {"b": RichTextBold, "code": RichTextCode, "i": RichTextItalic}
# A title line: exactly one bold span with only plain text around it,
# e.g. "📊 <b>Статистика</b>" or "🎫 <b>Тикет #5</b> — Открыт".
_TITLE_RE = re.compile(r"^[^<]*<b>[^<]*</b>[^<]*$")
_BLOCKQUOTE_RE = re.compile(r"<blockquote>(.*?)</blockquote>", re.DOTALL)
_TAG_RE = re.compile(r"</?(b|i|code|blockquote)>")


class _InlineParser(HTMLParser):
    """Parses one line of HTML-ish text into a RichTextUnion."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._stack: list[list] = [[]]

    def handle_starttag(self, tag: str, attrs: list) -> None:
        if tag in _INLINE_TAGS:
            self._stack.append([])

    def handle_endtag(self, tag: str) -> None:
        if tag in _INLINE_TAGS and len(self._stack) > 1:
            children = self._stack.pop()
            inner = children[0] if len(children) == 1 else children
            self._stack[-1].append(_INLINE_TAGS[tag](text=inner))

    def handle_data(self, data: str) -> None:
        if data:
            self._stack[-1].append(data)

    def result(self) -> RichTextUnion:
        segments = self._stack[0]
        if not segments:
            return ""
        return segments[0] if len(segments) == 1 else segments


def parse_inline(line: str) -> RichTextUnion:
    parser = _InlineParser()
    parser.feed(line)
    parser.close()
    return parser.result()


def rich_blocks_from_legacy_text(text: str) -> list[InputRichBlockUnion]:
    blocks: list[InputRichBlockUnion] = []
    title_done = False
    skip_next_separator = False

    pos = 0
    chunks: list[tuple[str, str]] = []
    for m in _BLOCKQUOTE_RE.finditer(text):
        if m.start() > pos:
            chunks.append(("text", text[pos : m.start()]))
        chunks.append(("blockquote", m.group(1)))
        pos = m.end()
    if pos < len(text):
        chunks.append(("text", text[pos:]))

    for kind, chunk in chunks:
        if kind == "blockquote":
            paragraphs = [
                InputRichBlockParagraph(text=parse_inline(line.strip()))
                for line in chunk.split("\n")
                if line.strip()
            ]
            if paragraphs:
                blocks.append(InputRichBlockBlockQuotation(blocks=paragraphs))
            title_done = True
            skip_next_separator = False
            continue

        for line in chunk.split("\n"):
            stripped = line.strip()
            if not stripped:
                continue
            if skip_next_separator:
                skip_next_separator = False
                if stripped == SEPARATOR:
                    continue
            if stripped == SEPARATOR:
                blocks.append(InputRichBlockDivider())
                continue
            if not title_done and _TITLE_RE.match(stripped):
                blocks.append(InputRichBlockSectionHeading(text=parse_inline(stripped), size=2))
                blocks.append(InputRichBlockDivider())
                title_done = True
                skip_next_separator = True
                continue
            title_done = True
            blocks.append(InputRichBlockParagraph(text=parse_inline(stripped)))

    return blocks


def strip_tags(text: str) -> str:
    """Plain text (no HTML) — for callback toasts and logs."""
    return _TAG_RE.sub("", text)


def table_block(
    header: list[str], rows: list[list[str]], *, compact: bool = True
) -> InputRichBlockTable:
    """A left-aligned table; cells may use the same inline tags as screens."""

    def cell(text: str, *, is_header: bool = False) -> RichBlockTableCell:
        return RichBlockTableCell(
            align="left", valign="middle", text=parse_inline(text), is_header=is_header
        )

    cells = [[cell(h, is_header=True) for h in header]]
    cells.extend([cell(value) for value in row] for row in rows)
    return InputRichBlockTable(cells=cells, is_bordered=False, is_striped=True, is_compact=compact)
