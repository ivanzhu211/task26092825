"""gzip / deflate（含裸 deflate）/ 不压缩 的解压与回压。"""

from __future__ import annotations

import zlib

# 回压方式：identity / gzip / deflate-zlib（带 zlib 头）/ deflate-raw（裸 deflate）
SCHEMES = ("identity", "gzip", "deflate-zlib", "deflate-raw")


def decompress(body: bytes, encoding: str) -> tuple[bytes, str] | None:
    """解压；返回 (解压后字节, 回压方式)。失败返回 None。"""
    try:
        if encoding == "identity":
            return body, "identity"
        if encoding == "gzip":
            return zlib.decompress(body, wbits=31), "gzip"
        if encoding == "deflate":
            try:
                return zlib.decompress(body), "deflate-zlib"
            except zlib.error:
                return zlib.decompress(body, wbits=-15), "deflate-raw"
    except (zlib.error, ValueError, EOFError):
        return None
    return None


def compress(body: bytes, scheme: str) -> bytes:
    """按原方式压回。"""
    if scheme == "identity":
        return body
    if scheme == "gzip":
        return zlib.compress(body, wbits=31)
    if scheme == "deflate-zlib":
        return zlib.compress(body)
    if scheme == "deflate-raw":
        obj = zlib.compressobj(wbits=-15)
        return obj.compress(body) + obj.flush()
    raise ValueError(f"unknown scheme: {scheme}")
