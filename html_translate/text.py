"""文本段处理：首尾空白剥离、实体解码、超长切分、写回转义。"""

from __future__ import annotations

import html as _html

_WS = " \t\n\r\f"


def split_affixes(segment: str) -> tuple[str, str, str]:
    """拆成 (前空白, 核心, 后空白)。空白：空格、制表、换行、回车、换页。"""
    start = 0
    end = len(segment)
    while start < end and segment[start] in _WS:
        start += 1
    while end > start and segment[end - 1] in _WS:
        end -= 1
    return segment[:start], segment[start:end], segment[end:]


def decode_entities(text: str) -> str:
    """按 HTML5 规则解码字符引用。"""
    return _html.unescape(text)


def escape_translation(text: str) -> str:
    """写回时只转义 & < >。"""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def chunk_text(text: str, limit: int = 5000) -> list[str]:
    """超长切分：limit 内最靠后的空白处切开（空白归前一片），找不到就硬切。"""
    if len(text) <= limit:
        return [text]
    chunks: list[str] = []
    rest = text
    while len(rest) > limit:
        window = rest[:limit]
        cut = -1
        for i in range(len(window) - 1, -1, -1):
            if window[i] in _WS:
                cut = i + 1  # 空白归前一片
                break
        if cut <= 0:
            cut = limit  # 硬切
        chunks.append(rest[:cut])
        rest = rest[cut:]
    if rest:
        chunks.append(rest)
    return chunks
