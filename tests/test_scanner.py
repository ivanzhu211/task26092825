from pagetrans.scanner import scan


def texts(parts):
    return [p.raw for p in parts if p.is_text]


def raws(parts):
    return [p.raw for p in parts if not p.is_text]


def test_roundtrip_concat():
    html = "<p>a</p><!-- c --><b>x</b>"
    assert "".join(p.raw for p in scan(html)) == html


def test_simple_text_between_tags():
    parts = scan("<p>Hello</p>")
    assert texts(parts) == ["Hello"]
    assert raws(parts) == ["<p>", "</p>"]


def test_uppercase_tags_and_attrs_with_gt():
    html = '<DIV CLASS="a>b">Hi</DIV>'
    parts = scan(html)
    assert texts(parts) == ["Hi"]
    assert raws(parts) == ['<DIV CLASS="a>b">', "</DIV>"]


def test_single_quoted_attr_with_gt():
    html = "<a title='x>y'>t</a>"
    assert texts(scan(html)) == ["t"]


def test_lone_lt_in_text_is_text():
    parts = scan("<p>a < b and 1 <2</p>")
    assert texts(parts) == ["a < b and 1 <2"]


def test_comment_doctype_preserved():
    html = "<!DOCTYPE html><!-- <p>not text</p> --><p>real</p>"
    parts = scan(html)
    assert texts(parts) == ["real"]
    assert raws(parts) == ["<!DOCTYPE html>", "<!-- <p>not text</p> -->", "<p>", "</p>"]


def test_unterminated_comment_runs_to_eof():
    html = "<p>a</p><!-- never closed <b>x</b>"
    parts = scan(html)
    assert texts(parts) == ["a"]
    assert "".join(p.raw for p in parts) == html


def test_script_content_not_text():
    html = '<script>if (a</div> && "<!--") { s="x"; }</script><p>yes</p>'
    parts = scan(html)
    assert texts(parts) == ["yes"]
    assert "".join(p.raw for p in parts) == html


def test_script_end_tag_case_insensitive():
    html = "<SCRIPT>var a=1;</ScRiPt>t"
    parts = scan(html)
    assert texts(parts) == ["t"]


def test_style_code_pre_not_translated():
    html = "<style>.a > .b {}</style><code>x < y</code><pre> keep </pre>out"
    parts = scan(html)
    assert texts(parts) == ["out"]
    assert "".join(p.raw for p in parts) == html


def test_unclosed_pre_swallows_rest():
    html = "<p>a</p><pre>never closed <b>bold</b> text"
    parts = scan(html)
    assert texts(parts) == ["a"]
    assert raws(parts)[-1] == "<pre>never closed <b>bold</b> text"


def test_unclosed_code_swallows_rest():
    html = "start<code>rest of page <p>x</p>"
    parts = scan(html)
    assert texts(parts) == ["start"]


def test_unclosed_tag_runs_to_eof():
    html = "<p>a</p><div class='open"
    parts = scan(html)
    assert texts(parts) == ["a"]
    assert "".join(p.raw for p in parts) == html


def test_self_closing_pre_does_not_swallow():
    html = "<pre/>after"
    parts = scan(html)
    assert texts(parts) == ["after"]


def test_bogus_end_tag():
    html = "a</>b</ notatag>c"
    parts = scan(html)
    assert texts(parts) == ["a", "b", "c"]
    assert "".join(p.raw for p in parts) == html


def test_text_outside_and_inside_mixed():
    html = "lead<p>in</p>tail"
    assert texts(scan(html)) == ["lead", "in", "tail"]


def test_empty_and_no_tags():
    assert scan("") == []
    assert texts(scan("just text")) == ["just text"]
