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


# ---------- pass-through cases ----------


def test_unsupported_lang_pair_passthrough(mem):
    body = b"<p>Hello</p>"
    assert run(body, marker, mem, src="en", dst="ja") == body
    assert run(body, marker, mem, src="es", dst="de") == body


def test_all_six_pairs_supported(mem):
    body = b"<p>Hi</p>"
    for src, dst in [
        ("en", "es"), ("es", "en"), ("en", "de"),
        ("de", "en"), ("en", "fr"), ("fr", "en"),
    ]:
        out = run(body, marker, mem, src=src, dst=dst)
        assert out == f"<p>[{dst}:Hi]</p>".encode()


def test_non_html_passthrough(mem):
    body = b"<p>Hello</p>"
    assert run(body, marker, mem, ctype="text/plain") == body
    assert run(body, marker, mem, ctype="application/json") == body
    assert run(body, marker, mem, ctype=None) == body


def test_non_utf8_charset_passthrough(mem):
    body = b"<p>Hello</p>"
    assert run(body, marker, mem, ctype="text/html; charset=gb2312") == body
    assert run(body, marker, mem, ctype="text/html; charset=utf-16") == body


def test_case_insensitive_headers(mem):
    body = b"<p>Hi</p>"
    out = run(body, marker, mem, ctype='Text/HTML; Charset="UTF-8"')
    assert out == b"<p>[es:Hi]</p>"


def test_invalid_utf8_passthrough(mem):
    body = b"<p>bad \xff\xfe bytes</p>"
    assert run(body, marker, mem) == body


def test_unknown_content_encoding_passthrough(mem):
    body = b"<p>Hello</p>"
    assert run(body, marker, mem, cenc="br") == body
    assert run(body, marker, mem, cenc="zstd") == body


def test_broken_translate_fn_returns_original(mem):
    def bad(texts, src, dst):
        return ["only one"]  # wrong length

    body = b"<p>Hello</p><p>World</p>"
    assert run(body, bad, mem) == body

    def boom(texts, src, dst):
        raise RuntimeError("model exploded")

    assert run(body, boom, mem) == body


# ---------- identity translation keeps bytes ----------


TRICKY_PAGES = [
    # uppercase tags, attribute value containing '>'
    b'<!DOCTYPE HTML>\n<HTML><BODY><DIV CLASS="a>b" ID=\'x\'>Hello</DIV></BODY></HTML>',
    # unclosed tags
    b"<p>first<p>second<b>bold never closed",
    # lone '<' in text
    b"<p>a < b and 1 <2 and x<y</p>",
    # script containing '</div>' and '<!--'
    b'<script>var s = "</div>"; if (a<!--b) {}</script><p>text</p>',
    # unclosed pre swallows the rest
    b"<p>before</p><pre>keep <b>this</b> &amp; that",
    # entities of every flavour
    b"<p>&amp; &lt; &gt; &#65; &#x42; &copy; &copy &nbsp; &bogus;</p>",
    # comments and doctype
    b"<!doctype html><!-- <p>hidden</p> &amp; --><p>shown</p>",
    # style and code
    b"<style>a > b { color: red }</style><code>x < y</code><p>t</p>",
    # lone '<' at end of file, '<!' and '</' oddities
    b"<p>odd</p>text < another </> bogus </ notatag> tail <",
    # utf-8 multibyte content
    "<p>héllo wörld — 中文</p>".encode(),
]


@pytest.mark.parametrize("body", TRICKY_PAGES)
def test_identity_translation_byte_identical(body, mem):
    assert run(body, identity, mem) == body


# ---------- marker translation matches handwritten expectations ----------


def test_marker_basic(mem):
    body = b"<p>Hello</p>"
    assert run(body, marker, mem) == b"<p>[es:Hello]</p>"


def test_marker_preserves_edge_whitespace(mem):
    body = b"<p>  Hello\tworld \n</p>"
    assert run(body, marker, mem) == b"<p>  [es:Hello\tworld] \n</p>"


def test_marker_whitespace_only_untouched(mem):
    body = b"<p> \t\n </p>"
    assert run(body, marker, mem) == body


def test_marker_entities_decoded_then_escaped(mem):
    body = b"<p>Fish &amp; Chips &#8212; &#x2014;</p>"
    # decoded core: 'Fish & Chips — —' -> marker -> re-escape only & < >
    assert run(body, marker, mem) == b"<p>[es:Fish &amp; Chips \xe2\x80\x94 \xe2\x80\x94]</p>"


def test_marker_translation_escapes_specials(mem):
    def specials(texts, src, dst):
        return ["a <b> & 'c' \"d\"" for _ in texts]

    body = b"<p>x</p>"
    assert run(body, specials, mem) == b"<p>a &lt;b&gt; &amp; 'c' \"d\"</p>"


def test_marker_full_tricky_page(mem):
    body = (
        b'<!DOCTYPE html>\n'
        b'<DIV CLASS="a>b"> Hello </DIV>\n'
        b'<script>var s = "</div>"; /* <!-- */</script>\n'
        b'<!-- a comment <p>x</p> -->\n'
        b'<p>a < b</p>\n'
        b'<pre>not <b>translated</b>'
    )
    expected = (
        b'<!DOCTYPE html>\n'
        b'<DIV CLASS="a>b"> [es:Hello] </DIV>\n'
        b'<script>var s = "</div>"; /* <!-- */</script>\n'
        b'<!-- a comment <p>x</p> -->\n'
        b'<p>[es:a &lt; b]</p>\n'
        b'<pre>not <b>translated</b>'
    )
    assert run(body, marker, mem) == expected


def test_marker_script_style_code_pre_untouched(mem):
    body = (
        b"<script>var x = 1;</script>"
        b"<style>.a { color: red }</style>"
        b"<code>y = x</code>"
        b"<pre> z </pre>"
        b"<p>real</p>"
    )
    expected = (
        b"<script>var x = 1;</script>"
        b"<style>.a { color: red }</style>"
        b"<code>y = x</code>"
        b"<pre> z </pre>"
        b"<p>[es:real]</p>"
    )
    assert run(body, marker, mem) == expected


def test_translation_equal_to_source_keeps_original_bytes(mem):
    # translate returns the decoded text unchanged: original entity
    # spellings must survive byte-for-byte
    def echo_decoded(texts, src, dst):
        return list(texts)

    body = b"<p>Fish &amp; Chips &#65;</p>"
    assert run(body, echo_decoded, mem) == body


def test_attributes_never_translated(mem):
    body = b'<a href="hello" title="world">link</a>'
    assert run(body, marker, mem) == b'<a href="hello" title="world">[es:link]</a>'
