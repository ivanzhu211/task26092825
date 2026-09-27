"""Text-node helpers: whitespace trimming, entity decoding, escaping, chunking."""

from __future__ import annotations

import html

MAX_CHUNK_CHARS = 5000

_WS = " \t\n\r\f"


def split_edge_whitespace(raw: str) -> tuple[str, str, str]:
    """Split raw text node into (leading_ws, core, trailing_ws)."""
    start = 0
    end = len(raw)
    while start < end and raw[start] in _WS:
        start += 1
    while end > start and raw[end - 1] in _WS:
        end -= 1
    return raw[:start], raw[start:end], raw[end:]


def decode_entities(core: str) -> str:
    """Decode HTML5 character references."""
    if "&" not in core:
        return core
    return html.unescape(core)


def escape_translation(text: str) -> str:
    """Escape only &, < and >."""
    if "&" in text:
        text = text.replace("&", "&amp;")
    if "<" in text:
        text = text.replace("<", "&lt;")
    if ">" in text:
        text = text.replace(">", "&gt;")
    return text


def chunk_text(core: str, limit: int = MAX_CHUNK_CHARS) -> list[str]:
    """Split core into pieces of at most `limit` Unicode characters.

    Splits at the last whitespace within the limit (whitespace stays with
    the preceding piece); hard-cuts at the limit when no whitespace exists.
    """
    if len(core) <= limit:
        return [core]
    chunks: list[str] = []
    pos = 0
    total = len(core)
    while pos < total:
        end = min(pos + limit, total)
        if end < total:
            cut = -1
            for idx in range(end - 1, pos - 1, -1):
                if core[idx] in _WS:
                    cut = idx + 1  # whitespace belongs to the preceding piece
                    break
            if cut > pos:
                end = cut
        chunks.append(core[pos:end])
        pos = end
    return chunks
