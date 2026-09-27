"""HTML 词法切分：区分「原文保留」与「待翻译文本段」。

所有 token 的 raw 拼接起来必须与原串完全一致；不做任何规范化。
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_RAW_TEXT_TAGS = ("script", "style", "code", "pre")
_CLOSE_RE = {
    name: re.compile(r"</" + name + r"(?=[\t\n\f\r />])", re.IGNORECASE)
    for name in _RAW_TEXT_TAGS
}
_TAG_NAME_CHARS = frozenset("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-")


@dataclass
class Token:
    raw: str          # 原文片段（逐字节保留）
    is_text: bool     # True 表示这是标签之间的文字，可翻译


def _scan_tag_end(html: str, i: int, n: int) -> int:
    """从标签名之后扫描到标签结束（引号内的 '>' 不算）。返回结束后的下标。"""
    quote = ""
    while i < n:
        c = html[i]
        if quote:
            if c == quote:
                quote = ""
        elif c == '"' or c == "'":
            quote = c
        elif c == ">":
            return i + 1
        i += 1
    return n


def _scan_markup(html: str, lt: int, n: int) -> int:
    """从 '<' 处扫描一段原样保留的标记，返回结束后的下标。"""
    c1 = html[lt + 1]
    if c1 == "!":
        if html.startswith("<!--", lt):
            end = html.find("-->", lt + 4)
            return n if end == -1 else end + 3
        end = html.find(">", lt + 2)
        return n if end == -1 else end + 1
    if c1 == "?":
        end = html.find(">", lt + 2)
        return n if end == -1 else end + 1
    if c1 == "/":
        end = html.find(">", lt + 2)
        return n if end == -1 else end + 1

    # 开始标签：先取标签名
    i = lt + 1
    while i < n and html[i] in _TAG_NAME_CHARS:
        i += 1
    name = html[lt + 1:i].lower()
    tag_end = _scan_tag_end(html, i, n)

    if name in _CLOSE_RE:
        # 原始文本元素：内容到匹配的闭合标签为止都不翻译
        close = _CLOSE_RE[name].search(html, tag_end)
        if close is None:
            return n
        gt = html.find(">", close.start())
        return n if gt == -1 else gt + 1
    return tag_end


def tokenize(html: str) -> list[Token]:
    """把 HTML 切成 token 序列，所有 raw 拼接等于原串。"""
    tokens: list[Token] = []
    n = len(html)
    pos = 0
    text_start = 0
    while pos < n:
        lt = html.find("<", pos)
        if lt == -1:
            break
        nxt = html[lt + 1] if lt + 1 < n else ""
        if nxt and (nxt.isalpha() or nxt in "/!?"):
            if lt > text_start:
                tokens.append(Token(html[text_start:lt], True))
            end = _scan_markup(html, lt, n)
            tokens.append(Token(html[lt:end], False))
            pos = end
            text_start = end
        else:
            # 孤立的 '<'，按普通文字处理
            pos = lt + 1
    if text_start < n:
        tokens.append(Token(html[text_start:n], True))
    return tokens
