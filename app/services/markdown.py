"""Telegram-style Markdown -> HTML (what sendMessage(parse_mode=HTML) takes).

Supported, in the spirit of Telegram's MarkdownV2 but without its
mandatory escaping:

    **жирный** или *жирный*        <b>
    _курсив_                       <i>
    __подчёркнутый__               <u>
    ~~зачёркнутый~~ или ~x~        <s>
    ||спойлер||                    <tg-spoiler>
    `код`                          <code>
    ```код блоком```               <pre>
    [текст](https://ссылка)        <a href>
    > цитата (строки с >)          <blockquote>

Everything else is HTML-escaped, so a message with no markup at all comes
through unchanged.
"""

import html
import re

_FENCE_RE = re.compile(r"```(?:([\w+-]+)\n)?(.*?)```", re.DOTALL)
_CODE_RE = re.compile(r"`([^`\n]+)`")
_LINK_RE = re.compile(r"\[([^\]\n]+)\]\((https?://[^)\s]+|tg://[^)\s]+)\)")
_BOLD2_RE = re.compile(r"\*\*(\S(?:.*?\S)?)\*\*", re.DOTALL)
_BOLD_RE = re.compile(r"(?<![\w*])\*(\S(?:.*?\S)?)\*(?![\w*])", re.DOTALL)
_UNDER_RE = re.compile(r"__(\S(?:.*?\S)?)__", re.DOTALL)
_ITALIC_RE = re.compile(r"(?<![\w_])_(\S(?:.*?\S)?)_(?![\w_])", re.DOTALL)
_STRIKE2_RE = re.compile(r"~~(\S(?:.*?\S)?)~~", re.DOTALL)
_STRIKE_RE = re.compile(r"(?<![\w~])~(\S(?:.*?\S)?)~(?![\w~])", re.DOTALL)
_SPOILER_RE = re.compile(r"\|\|(\S(?:.*?\S)?)\|\|", re.DOTALL)
_MARKER = "\x00"


def _placeholder(store: list[str], value: str) -> str:
    store.append(value)
    return f"{_MARKER}{len(store) - 1}{_MARKER}"


def markdown_to_html(text: str) -> str:
    protected: list[str] = []

    def fence(m: re.Match) -> str:
        lang, code = m.group(1), m.group(2).strip("\n")
        escaped = html.escape(code, quote=False)
        if lang:
            return _placeholder(
                protected, f'<pre><code class="language-{lang}">{escaped}</code></pre>'
            )
        return _placeholder(protected, f"<pre>{escaped}</pre>")

    def code(m: re.Match) -> str:
        return _placeholder(protected, f"<code>{html.escape(m.group(1), quote=False)}</code>")

    def link(m: re.Match) -> str:
        label = html.escape(m.group(1), quote=False)
        return _placeholder(protected, f'<a href="{html.escape(m.group(2))}">{label}</a>')

    text = _FENCE_RE.sub(fence, text)
    text = _CODE_RE.sub(code, text)
    text = _LINK_RE.sub(link, text)

    text = html.escape(text, quote=False)

    text = _BOLD2_RE.sub(r"<b>\1</b>", text)
    text = _BOLD_RE.sub(r"<b>\1</b>", text)
    text = _UNDER_RE.sub(r"<u>\1</u>", text)
    text = _ITALIC_RE.sub(r"<i>\1</i>", text)
    text = _STRIKE2_RE.sub(r"<s>\1</s>", text)
    text = _STRIKE_RE.sub(r"<s>\1</s>", text)
    text = _SPOILER_RE.sub(r"<tg-spoiler>\1</tg-spoiler>", text)

    text = _blockquotes(text)

    for i, value in enumerate(protected):
        text = text.replace(f"{_MARKER}{i}{_MARKER}", value)
    return text


def _blockquotes(text: str) -> str:
    """Consecutive lines starting with '>' become one <blockquote>."""
    out: list[str] = []
    quote: list[str] = []

    def flush() -> None:
        if quote:
            out.append("<blockquote>" + "\n".join(quote) + "</blockquote>")
            quote.clear()

    for line in text.split("\n"):
        # '>' was escaped to '&gt;' above.
        if line.startswith("&gt;"):
            quote.append(line[4:].lstrip())
        else:
            flush()
            out.append(line)
    flush()
    return "\n".join(out)


def has_markup(text: str) -> bool:
    """True if markdown_to_html would produce any tag."""
    return markdown_to_html(text) != html.escape(text, quote=False)
