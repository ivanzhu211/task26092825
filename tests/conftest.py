import pytest

from html_translate import HtmlTranslator


def identity_fn(texts, source_lang, target_lang):
    return list(texts)


def marking_fn(texts, source_lang, target_lang):
    return [f"[{target_lang}:{t}]" for t in texts]


# 刁钻页面集：大写标签、属性值含 '>'、未闭合标签、孤立 '<'、
# 脚本含 '</div>' 和 '<!--'、未闭合 pre、各种实体、注释、doctype
TRICKY_PAGES = [
    '<DIV CLASS="a>b" ID=\'x>y\'>Hello World</DIV>',
    '<div><p>First<p>Second<div>Third',
    '<p>1 < 2 and 3 <4 but a<b>bold</b></p>',
    '<script>var s = "</div>"; /* <!-- */ if (a<b) { go(); }</script><p>After</p>',
    '<p>Before</p><pre>line1\nline2 <b>not bold</b>',
    '<p>&amp; &lt; &gt; &quot; &#65; &#x41; &nbsp; &copy; &fake;</p>',
    '<!DOCTYPE html><!-- comment <p> &#65; --><p>Text</p>',
    '<style>.a > .b { content: "</p>"; }</style><code>x < y && z</code><p>Real</p>',
    '<p>  padded\t</p><div>   \n\t  </div>',
    '<p>Text</p><!-- dangling comment',
    '<p>Text <span',
    '<SCRIPT TYPE="text/javascript">document.write("<div><!--");</SCRIPT><B>Up</B>',
    '<input value="a>b" disabled><BR/>done',
    '<p>&Agrave;&ntilde;&#x1F600; mixed</p>',
    '<pre><code>both <b>raw</b></code></pre><p>After</p>',
]


@pytest.fixture
def pages():
    return TRICKY_PAGES


@pytest.fixture
def translator(tmp_path):
    t = HtmlTranslator(str(tmp_path / "tm.sqlite3"))
    yield t
    t.close()
