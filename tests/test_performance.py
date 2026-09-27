import time

from pagetrans import translate_response


def test_large_page_within_time_budget(tmp_path):
    # 100k text segments, ~5 MiB page
    segment = '<p class="x">Segment number seven, hello world!!</p>\n'
    repeats = 100_000
    body = (segment * repeats).encode()
    assert len(body) >= 5 * 1024 * 1024

    def instant_translate(texts, src, dst):
        return [t.upper() for t in texts]

    mem = str(tmp_path / "mem.sqlite")
    start = time.monotonic()
    out = translate_response(
        "text/html", None, body, "en", "es", instant_translate, mem
    )
    elapsed = time.monotonic() - start
    assert out != body
    assert elapsed < 3.0, f"took {elapsed:.2f}s"


def test_large_page_identity_roundtrip(tmp_path):
    segment = "<p>Same segment everywhere</p>\n"
    body = (segment * 100_000).encode()
    mem = str(tmp_path / "mem.sqlite")
    out = translate_response(
        "text/html", None, body, "en", "es", lambda t, s, d: list(t), mem
    )
    assert out == body
