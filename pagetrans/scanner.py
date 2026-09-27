"""HTML scanner: split decoded text into raw parts and translatable text parts.

Everything that is not a text node (tags, comments, doctype, and the
contents of script/style/code/pre) is preserved byte-for-byte.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_WS = " \t\n\r\f"

# Raw-text elements: their content is never translated. script/style follow
# the HTML5 rule (a self-closing slash does not end them); code/pre honour
# an explicit "/>" so XML-ish pages stay sane.
_RAWTEXT = frozenset({"script", "style", "code", "pre"})
_RAWTEXT_NO_SELF_CLOSE = frozenset({"script", "style"})

_END_TAG_RES = {
    name: re.compile(r"</" + name + r"(?=[\t\n\f\r />]|$)")
    for name in _RAWTEXT
}


@dataclass
class Part:
    is_text: bool
    raw: str  # exact original substring


def _scan_tag(lower: str, start: int) -> tuple[int, int, bool]:
    """Scan a tag whose name begins at `start` (index of first name char).

    Returns (name_end, tag_end, self_closing). Quoted attribute values may
    contain '>'. An unterminated tag or quote runs to EOF.
    """
    n = len(lower)
    i = start
    while i < n and lower[i] not in _WS + "/>":
        i += 1
    name_end = i
    self_closing = False
    while i < n:
        c = lower[i]
        if c == ">":
            return name_end, i + 1, self_closing
        if c == '"' or c == "'":
            close = lower.find(c, i + 1)
            if close == -1:
                return name_end, n, False
            i = close + 1
            continue
        self_closing = c == "/"
        i += 1
    return name_end, n, False


def scan(html: str) -> list[Part]:
    """Split html into parts; concatenating all raw fields yields html."""
    n = len(html)
    lower = html.lower()
    parts: list[Part] = []
    text_start = 0
    pos = 0
    while pos < n:
        lt = lower.find("<", pos)
        if lt == -1:
            break
        nxt = lower[lt + 1] if lt + 1 < n else ""
        if "a" <= nxt <= "z":
            name_end, tag_end, self_closing = _scan_tag(lower, lt + 1)
            end = tag_end
            name = lower[lt + 1 : name_end]
            if name in _RAWTEXT and not (
                self_closing and name not in _RAWTEXT_NO_SELF_CLOSE
            ):
                match = _END_TAG_RES[name].search(lower, tag_end)
                # raw content runs to the end tag, or to EOF when unclosed
                end = match.start() if match else n
            if lt > text_start:
                parts.append(Part(True, html[text_start:lt]))
            parts.append(Part(False, html[lt:end]))
            pos = text_start = end
        elif nxt == "!":
            if lower.startswith("<!--", lt):
                close = lower.find("-->", lt + 4)
                end = n if close == -1 else close + 3
            else:
                close = lower.find(">", lt + 2)
                end = n if close == -1 else close + 1
            if lt > text_start:
                parts.append(Part(True, html[text_start:lt]))
            parts.append(Part(False, html[lt:end]))
            pos = text_start = end
        elif nxt == "?" or nxt == "/":
            # processing instruction / bogus comment (incl. "</" + non-letter)
            close = lower.find(">", lt + 2)
            end = n if close == -1 else close + 1
            if lt > text_start:
                parts.append(Part(True, html[text_start:lt]))
            parts.append(Part(False, html[lt:end]))
            pos = text_start = end
        else:
            # a lone '<' is ordinary text; keep the text run going
            pos = lt + 1
    if text_start < n:
        parts.append(Part(True, html[text_start:]))
    return parts
