from pagetrans.textutil import (
    chunk_text,
    decode_entities,
    escape_translation,
    split_edge_whitespace,
)


def test_split_edge_whitespace():
    assert split_edge_whitespace("  hi\t\n") == ("  ", "hi", "\t\n")
    assert split_edge_whitespace("\f\r\nx") == ("\f\r\n", "x", "")
    assert split_edge_whitespace("no-ws") == ("", "no-ws", "")
    assert split_edge_whitespace(" \t\n") == (" \t\n", "", "")
    assert split_edge_whitespace("") == ("", "", "")


def test_decode_entities():
    assert decode_entities("a &amp; b &lt; &#65; &#x42; &nbsp;c") == "a & b < A B \xa0c"
    assert decode_entities("plain") == "plain"
    # HTML5 legacy rule: "&not" is a named reference even without semicolon
    assert decode_entities("&notanentity; &copy") == "¬anentity; ©"
    assert decode_entities("&bogusref;") == "&bogusref;"


def test_escape_translation():
    assert escape_translation("a & <b> 'q' \"d\"") == "a &amp; &lt;b&gt; 'q' \"d\""


def test_chunk_short():
    assert chunk_text("abc", 5000) == ["abc"]


def test_chunk_hard_cut_without_whitespace():
    text = "x" * 12000
    chunks = chunk_text(text, 5000)
    assert [len(c) for c in chunks] == [5000, 5000, 2000]
    assert "".join(chunks) == text


def test_chunk_prefers_last_whitespace_within_limit():
    # whitespace at position 4999 (0-based) inside the first 5000 chars
    text = "a" * 4999 + " " + "b" * 6000
    chunks = chunk_text(text, 5000)
    assert chunks[0] == "a" * 4999 + " "  # whitespace stays with previous piece
    assert "".join(chunks) == text
    assert all(len(c) <= 5000 for c in chunks)


def test_chunk_whitespace_at_boundary():
    text = "a" * 5000 + " " + "b" * 100
    chunks = chunk_text(text, 5000)
    assert chunks[0] == "a" * 5000
    assert "".join(chunks) == text
