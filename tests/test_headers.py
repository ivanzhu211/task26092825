from pagetrans.headers import (
    is_translatable_html,
    normalize_content_encoding,
    parse_content_type,
)


def test_parse_mime_and_charset_case_insensitive():
    assert parse_content_type("Text/HTML; Charset=UTF-8") == ("text/html", "utf-8")
    assert parse_content_type('text/html; charset="UTF-8"') == ("text/html", "utf-8")
    assert parse_content_type("text/html") == ("text/html", None)
    assert parse_content_type(None) == ("", None)
    assert parse_content_type("text/html; charset=gb2312") == ("text/html", "gb2312")


def test_is_translatable_html():
    assert is_translatable_html("text/html", None)
    assert is_translatable_html("text/html", "utf-8")
    assert not is_translatable_html("text/html", "gb2312")
    assert not is_translatable_html("text/plain", None)
    assert not is_translatable_html("application/json", None)


def test_normalize_content_encoding():
    assert normalize_content_encoding(None) == "identity"
    assert normalize_content_encoding("") == "identity"
    assert normalize_content_encoding("GZip") == "gzip"
    assert normalize_content_encoding(" DEFLATE ") == "deflate"
    assert normalize_content_encoding("br") == "br"
