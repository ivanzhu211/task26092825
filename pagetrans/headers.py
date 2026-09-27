"""Content-Type / Content-Encoding parsing."""

from __future__ import annotations


def parse_content_type(value: str | None) -> tuple[str, str | None]:
    """Return (mime, charset) lowercased; charset is None when undeclared."""
    if not value:
        return "", None
    parts = value.split(";")
    mime = parts[0].strip().lower()
    charset: str | None = None
    for param in parts[1:]:
        name, sep, raw = param.partition("=")
        if not sep:
            continue
        if name.strip().lower() != "charset":
            continue
        token = raw.strip().strip('"').strip("'").strip().lower()
        charset = token or None
    return mime, charset


def is_translatable_html(mime: str, charset: str | None) -> bool:
    """True only for text/html with UTF-8 or undeclared charset."""
    if mime != "text/html":
        return False
    return charset is None or charset in ("utf-8", "utf8")


def normalize_content_encoding(value: str | None) -> str:
    """Return normalized encoding token: 'identity', 'gzip' or 'deflate'."""
    if not value:
        return "identity"
    token = value.strip().lower()
    if token in ("", "identity"):
        return "identity"
    if token in ("gzip", "x-gzip"):
        return "gzip"
    if token == "deflate":
        return "deflate"
    return token
