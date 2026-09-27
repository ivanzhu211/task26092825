"""Content-Type / Content-Encoding 判定。"""

from __future__ import annotations

_LANG_PAIRS = frozenset(
    (a, b)
    for a, b in (
        ("en", "es"), ("en", "de"), ("en", "fr"),
        ("es", "en"), ("de", "en"), ("fr", "en"),
    )
)


def is_supported_lang_pair(source_lang: str, target_lang: str) -> bool:
    return (source_lang.lower(), target_lang.lower()) in _LANG_PAIRS


def is_translatable_html(content_type: str | None) -> bool:
    """是否为可处理的 text/html（UTF-8 或未声明字符集）。取值不区分大小写。"""
    if not content_type:
        return False
    parts = content_type.split(";")
    media_type = parts[0].strip().lower()
    if media_type != "text/html":
        return False
    for param in parts[1:]:
        if "=" not in param:
            continue
        name, _, value = param.partition("=")
        if name.strip().lower() != "charset":
            continue
        charset = value.strip().strip('"').strip("'").lower()
        return charset in ("utf-8", "utf8")
    # 未声明字符集
    return True


def normalize_encoding(content_encoding: str | None) -> str | None:
    """归一化压缩方式；返回 'identity'/'gzip'/'deflate'，不认识返回 None。"""
    if content_encoding is None:
        return "identity"
    value = content_encoding.strip().lower()
    if value in ("", "identity"):
        return "identity"
    if value == "gzip":
        return "gzip"
    if value == "deflate":
        return "deflate"
    return None
