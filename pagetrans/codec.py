"""Body (de)compression for gzip / deflate / identity."""

from __future__ import annotations

import gzip
import zlib


def decompress(encoding: str, body: bytes) -> tuple[bytes, str] | None:
    """Decompress body.

    Returns (data, effective_encoding) where effective_encoding is the
    token to pass back to `compress` ('deflate' vs 'deflate-raw').
    None when the encoding is unknown or the data is corrupt.
    """
    try:
        if encoding == "identity":
            return body, "identity"
        if encoding == "gzip":
            return gzip.decompress(body), "gzip"
        if encoding == "deflate":
            try:
                return zlib.decompress(body), "deflate"
            except zlib.error:
                # raw deflate stream without the zlib header
                return zlib.decompress(body, -zlib.MAX_WBITS), "deflate-raw"
        return None
    except Exception:
        return None


def compress(encoding: str, body: bytes) -> bytes:
    """Compress body back with the original encoding."""
    if encoding == "gzip":
        return gzip.compress(body)
    if encoding == "deflate":
        return zlib.compress(body)
    if encoding == "deflate-raw":
        compressor = zlib.compressobj(wbits=-zlib.MAX_WBITS)
        return compressor.compress(body) + compressor.flush()
    return body
