import gzip
import zlib

from pagetrans.codec import compress, decompress


def test_identity():
    assert decompress("identity", b"abc") == (b"abc", "identity")
    assert compress("identity", b"abc") == b"abc"


def test_gzip_roundtrip():
    data = b"hello world" * 100
    packed = gzip.compress(data)
    out, enc = decompress("gzip", packed)
    assert out == data and enc == "gzip"
    assert gzip.decompress(compress("gzip", out)) == data


def test_deflate_zlib_roundtrip():
    data = b"hello world" * 100
    packed = zlib.compress(data)
    out, enc = decompress("deflate", packed)
    assert out == data and enc == "deflate"
    assert zlib.decompress(compress("deflate", out)) == data


def test_deflate_raw_roundtrip():
    data = b"hello world" * 100
    c = zlib.compressobj(wbits=-zlib.MAX_WBITS)
    packed = c.compress(data) + c.flush()
    out, enc = decompress("deflate", packed)
    assert out == data and enc == "deflate-raw"
    repacked = compress("deflate-raw", out)
    assert zlib.decompress(repacked, -zlib.MAX_WBITS) == data


def test_corrupt_and_unknown():
    assert decompress("gzip", b"not gzip") is None
    assert decompress("deflate", b"garbage bytes") is None
    assert decompress("br", b"whatever") is None
