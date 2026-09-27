"""压缩往返、超长切分、批量上限、翻译记忆、健壮性。"""

import zlib

import conftest
from html_translate import HtmlTranslator


def _gzip(data):
    return zlib.compress(data, wbits=31)


def _deflate_zlib(data):
    return zlib.compress(data)


def _deflate_raw(data):
    obj = zlib.compressobj(wbits=-15)
    return obj.compress(data) + obj.flush()


def test_compression_roundtrip(translator):
    html = "<p>Hello <b>World</b></p>".encode()
    expected = "<p>[fr:Hello] <b>[fr:World]</b></p>".encode()
    for encode, encoding, decode in (
        (lambda b: b, None, lambda b: b),
        (lambda b: b, "identity", lambda b: b),
        (_gzip, "gzip", lambda b: zlib.decompress(b, wbits=31)),
        (_deflate_zlib, "deflate", zlib.decompress),
        (_deflate_raw, "deflate", lambda b: zlib.decompress(b, wbits=-15)),
    ):
        out = translator.translate_response(
            "text/html", encoding, encode(html), "en", "fr", conftest.marking_fn
        )
        assert decode(out) == expected, encoding


def test_deflate_form_preserved(translator):
    html = b"<p>Hi</p>"
    out = translator.translate_response(
        "text/html", "deflate", _deflate_raw(html), "en", "fr", conftest.identity_fn
    )
    assert zlib.decompress(out, wbits=-15) == html  # 裸 deflate 压回仍是裸 deflate
    out = translator.translate_response(
        "text/html", "deflate", _deflate_zlib(html), "en", "fr", conftest.identity_fn
    )
    assert zlib.decompress(out) == html  # 带 zlib 头的压回仍带头


def test_bad_inputs_returned_as_is(translator):
    fn = conftest.marking_fn
    assert translator.translate_response("text/html", "gzip", b"junk", "en", "fr", fn) == b"junk"
    assert translator.translate_response("text/html", "deflate", b"\xff\x00", "en", "fr", fn) == b"\xff\x00"
    assert translator.translate_response("text/html", "br", b"<p>x</p>", "en", "fr", fn) == b"<p>x</p>"
    assert translator.translate_response("text/html", None, b"\xc3\x28", "en", "fr", fn) == b"\xc3\x28"
    assert translator.translate_response("application/json", None, b"{}", "en", "fr", fn) == b"{}"
    assert translator.translate_response("text/html; charset=GB2312", None, b"x", "en", "fr", fn) == b"x"
    assert translator.translate_response("text/html", None, b"x", "es", "de", fn) == b"x"
    assert translator.translate_response(None, None, b"x", "en", "fr", fn) == b"x"
    # 翻译函数抛异常也不能炸
    def boom(texts, s, t):
        raise RuntimeError("model down")
    body = b"<p>Hi</p>"
    assert translator.translate_response("text/html", None, body, "en", "fr", boom) == body


def test_long_text_chunking(translator):
    seen = []

    def recording_fn(texts, s, t):
        seen.extend(texts)
        return [f"⟦{x}⟧" for x in texts]

    # 4999 个 a + 空格 + 6000 个 b：在 5000 内的空白处切，空白归前片
    text = "a" * 4999 + " " + "b" * 6000
    body = f"<p>{text}</p>".encode()
    out = translator.translate_response("text/html", None, body, "en", "fr", recording_fn)
    assert len(seen) == 3
    assert seen[0] == "a" * 4999 + " "
    assert seen[1] == "b" * 5000
    assert seen[2] == "b" * 1000
    assert all(len(p) <= 5000 for p in seen)
    expected = "<p>" + "".join(f"⟦{p}⟧" for p in seen) + "</p>"
    assert out.decode() == expected


def test_long_text_hard_cut(translator):
    seen = []

    def recording_fn(texts, s, t):
        seen.extend(texts)
        return list(texts)

    text = "x" * 5000 + "y" * 5000 + "z" * 2000  # 无空白：硬切（各片内容不同，避免去重）
    body = f"<p>{text}</p>".encode()
    translator.translate_response("text/html", None, body, "en", "fr", recording_fn)
    assert [len(p) for p in seen] == [5000, 5000, 2000]


def test_batch_limit(translator):
    batches = []

    def recording_fn(texts, s, t):
        batches.append(list(texts))
        return list(texts)

    body = "".join(f"<p>seg{i}</p>" for i in range(450)).encode()
    translator.translate_response("text/html", None, body, "en", "fr", recording_fn)
    assert [len(b) for b in batches] == [200, 200, 50]
    assert all(len(b) <= 200 for b in batches)


def test_dedup_within_page(translator):
    seen = []

    def recording_fn(texts, s, t):
        seen.extend(texts)
        return [x.upper() for x in texts]

    body = b"<p>same</p><div>same</div><span>same</span><b>other</b>"
    out = translator.translate_response("text/html", None, body, "en", "fr", recording_fn)
    assert seen == ["same", "other"]  # 重复文字只送一次
    assert out == b"<p>SAME</p><div>SAME</div><span>SAME</span><b>OTHER</b>"


def test_cache_hit_skips_translate_fn(tmp_path):
    path = str(tmp_path / "tm.sqlite3")
    t1 = HtmlTranslator(path)
    body = b"<p>cached</p>"
    out1 = t1.translate_response("text/html", None, body, "en", "fr", conftest.marking_fn)
    assert out1 == b"<p>[fr:cached]</p>"
    t1.close()

    # 重启后（新实例、同一文件）缓存仍命中，翻译函数不被调用
    t2 = HtmlTranslator(path)

    def must_not_call(texts, s, t):
        raise AssertionError("translate fn called despite cache")

    out2 = t2.translate_response("text/html", None, body, "en", "fr", must_not_call)
    assert out2 == b"<p>[fr:cached]</p>"
    # 其他语言对不命中
    out3 = t2.translate_response("text/html", None, body, "en", "de", conftest.marking_fn)
    assert out3 == b"<p>[de:cached]</p>"
    t2.close()


def test_identity_preserves_entities(translator):
    # 译文与解码后原文相同：保留原始字节（实体写法不动）
    body = "<p>&Agrave;&amp;&#65;</p>".encode()
    out = translator.translate_response("text/html", None, body, "en", "fr", conftest.identity_fn)
    assert out == body
