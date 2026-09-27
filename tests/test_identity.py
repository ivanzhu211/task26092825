"""原样返回的翻译函数：输出必须与解压后的输入逐字节相同。"""

import conftest


def test_identity_byte_for_byte(pages, translator):
    for html in pages:
        body = html.encode("utf-8")
        out = translator.translate_response(
            "text/html", None, body, "en", "fr", conftest.identity_fn
        )
        assert out == body, html


def test_identity_gzip(pages, translator):
    import zlib
    for html in pages:
        body = html.encode("utf-8")
        gz = zlib.compress(body, wbits=31)
        out = translator.translate_response(
            "text/html", "gzip", gz, "en", "es", conftest.identity_fn
        )
        assert zlib.decompress(out, wbits=31) == body, html
