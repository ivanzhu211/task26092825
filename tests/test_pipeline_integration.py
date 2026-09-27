import gzip
import zlib

import pytest

from pagetrans import translate_response


def identity(texts, src, dst):
    return list(texts)


def marker(texts, src, dst):
    return [f"[{dst}:{t}]" for t in texts]


@pytest.fixture
def mem(tmp_path):
    return str(tmp_path / "mem.sqlite")


def run(body, fn, mem, ctype="text/html", cenc=None, src="en", dst="es"):
    return translate_response(ctype, cenc, body, src, dst, fn, mem)


# ---------- compression round-trips ----------

PAGE = b'<html><body><p>Hello world</p><div id="x">Bye</div></body></html>'
PAGE_OUT = b'<html><body><p>[es:Hello world]</p><div id="x">[es:Bye]</div></body></html>'


def _raw_deflate(data):
    c = zlib.compressobj(wbits=-zlib.MAX_WBITS)
    return c.compress(data) + c.flush()


def _raw_inflate(data):
    return zlib.decompress(data, -zlib.MAX_WBITS)


@pytest.mark.parametrize(
    "pack,unpack",
    [
        (gzip.compress, gzip.decompress),
        (zlib.compress, zlib.decompress),
        (_raw_deflate, _raw_inflate),
    ],
    ids=["gzip", "deflate-zlib", "deflate-raw"],
)
def test_compressed_marker_roundtrip(pack, unpack, mem):
    cenc = "gzip" if pack is gzip.compress else "deflate"
    out = run(pack(PAGE), marker, mem, cenc=cenc)
    assert unpack(out) == PAGE_OUT


@pytest.mark.parametrize(
    "pack,unpack",
    [
        (gzip.compress, gzip.decompress),
        (zlib.compress, zlib.decompress),
        (_raw_deflate, _raw_inflate),
    ],
    ids=["gzip", "deflate-zlib", "deflate-raw"],
)
def test_compressed_identity_decompresses_identical(pack, unpack, mem):
    cenc = "gzip" if pack is gzip.compress else "deflate"
    out = run(pack(PAGE), identity, mem, cenc=cenc)
    assert unpack(out) == PAGE


def test_corrupt_gzip_passthrough(mem):
    body = b"\x1f\x8b broken"
    assert run(body, marker, mem, cenc="gzip") == body


def test_corrupt_deflate_passthrough(mem):
    body = b"definitely not deflate"
    assert run(body, marker, mem, cenc="deflate") == body


# ---------- chunking and batch limits ----------


def test_long_text_chunked_and_reassembled(mem):
    calls = []

    def recording(texts, src, dst):
        calls.append(list(texts))
        return list(texts)

    # 12000 chars, no whitespace -> hard cuts at 5000
    long_text = "x" * 12000
    body = f"<p>{long_text}</p>".encode()
    out = run(body, recording, mem)
    assert out == body  # identity -> byte identical
    pieces = [t for call in calls for t in call]
    assert [len(p) for p in pieces] == [5000, 5000, 2000]


def test_long_text_split_at_whitespace(mem):
    calls = []

    def recording(texts, src, dst):
        calls.append(list(texts))
        return list(texts)

    long_text = "a" * 4999 + " " + "b" * 6000
    body = f"<p>{long_text}</p>".encode()
    assert run(body, recording, mem) == body
    pieces = [t for call in calls for t in call]
    assert pieces[0] == "a" * 4999 + " "
    assert all(len(p) <= 5000 for p in pieces)
    assert "".join(pieces) == long_text


def test_batch_size_limit(mem):
    calls = []

    def recording(texts, src, dst):
        calls.append(list(texts))
        assert len(texts) <= 200
        return list(texts)

    body = "".join(f"<p>seg {i}</p>" for i in range(450)).encode()
    assert run(body, recording, mem) == body
    assert [len(c) for c in calls] == [200, 200, 50]


def test_chunk_pieces_count_towards_batch_limit(mem):
    calls = []

    def recording(texts, src, dst):
        calls.append(list(texts))
        assert len(texts) <= 200
        return list(texts)

    # 150 normal segments + one 12000-char segment (3 pieces) = 153 pieces
    body = "".join(f"<p>seg {i}</p>" for i in range(150))
    body += f"<p>{'y' * 12000}</p>"
    assert run(body.encode(), recording, mem) == body.encode()
    assert sum(len(c) for c in calls) == 153


# ---------- translation memory ----------


def test_repeated_text_sent_once_per_page(mem):
    calls = []

    def recording(texts, src, dst):
        calls.append(list(texts))
        return list(texts)

    body = b"<p>same</p><div>same</div><span>same</span><b>other</b>"
    run(body, recording, mem)
    pieces = [t for call in calls for t in call]
    assert sorted(pieces) == ["other", "same"]


def test_cache_hit_skips_translate_fn(mem):
    calls = []

    def recording(texts, src, dst):
        calls.append(list(texts))
        return [f"[{dst}:{t}]" for t in texts]

    body = b"<p>Hello</p>"
    assert run(body, recording, mem) == b"<p>[es:Hello]</p>"
    assert len(calls) == 1
    # second run: everything cached, translate_fn never called
    assert run(body, recording, mem) == b"<p>[es:Hello]</p>"
    assert len(calls) == 1


def test_cache_persists_across_instances(tmp_path):
    mem = str(tmp_path / "mem.sqlite")
    calls = []

    def recording(texts, src, dst):
        calls.append(list(texts))
        return [f"[{dst}:{t}]" for t in texts]

    body = b"<p>persistent</p>"
    run(body, recording, mem)
    run(body, recording, mem)  # new TranslationMemory on the same file
    assert len(calls) == 1


def test_cache_keyed_by_lang_pair(mem):
    calls = []

    def recording(texts, src, dst):
        calls.append((src, dst, list(texts)))
        return [f"[{dst}:{t}]" for t in texts]

    body = b"<p>Hello</p>"
    run(body, recording, mem, src="en", dst="es")
    run(body, recording, mem, src="en", dst="de")
    assert len(calls) == 2  # different pair -> translated again
    run(body, recording, mem, src="en", dst="es")
    assert len(calls) == 2
