"""性能：5 MiB、十万段文字，不计翻译函数耗时，3 秒内处理完。"""

import time

import conftest


def _make_page(n_segments=100_000):
    parts = []
    for i in range(n_segments):
        parts.append(f'<p class="x">Segment number {i} with some realistic text content here</p>')
    return "".join(parts)


def test_perf_100k_segments(translator):
    html = _make_page()
    body = html.encode("utf-8")
    assert len(body) >= 5 * 1024 * 1024, f"page too small: {len(body)}"

    start = time.perf_counter()
    out = translator.translate_response(
        "text/html", None, body, "en", "fr", conftest.identity_fn
    )
    elapsed = time.perf_counter() - start

    assert out == body
    assert elapsed < 3.0, f"took {elapsed:.2f}s"


def test_perf_100k_segments_marking(translator):
    html = _make_page()
    body = html.encode("utf-8")

    start = time.perf_counter()
    out = translator.translate_response(
        "text/html", None, body, "en", "fr", conftest.marking_fn
    )
    elapsed = time.perf_counter() - start

    assert b"[fr:Segment number 0" in out
    assert elapsed < 3.0, f"took {elapsed:.2f}s"
