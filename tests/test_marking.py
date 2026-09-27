"""加标记的翻译函数：结果必须与手写期望完全一致，不该翻的一处不动。"""

import conftest

# 与 conftest.TRICKY_PAGES 一一对应的期望输出
EXPECTED = [
    '<DIV CLASS="a>b" ID=\'x>y\'>[fr:Hello World]</DIV>',
    '<div><p>[fr:First]<p>[fr:Second]<div>[fr:Third]',
    '<p>[fr:1 &lt; 2 and 3 &lt;4 but a]<b>[fr:bold]</b></p>',
    '<script>var s = "</div>"; /* <!-- */ if (a<b) { go(); }</script><p>[fr:After]</p>',
    '<p>[fr:Before]</p><pre>line1\nline2 <b>not bold</b>',
    '<p>[fr:&amp; &lt; &gt; " A A \xa0 © &amp;fake;]</p>',
    '<!DOCTYPE html><!-- comment <p> &#65; --><p>[fr:Text]</p>',
    '<style>.a > .b { content: "</p>"; }</style><code>x < y && z</code><p>[fr:Real]</p>',
    '<p>  [fr:padded]\t</p><div>   \n\t  </div>',
    '<p>[fr:Text]</p><!-- dangling comment',
    '<p>[fr:Text] <span',
    '<SCRIPT TYPE="text/javascript">document.write("<div><!--");</SCRIPT><B>[fr:Up]</B>',
    '<input value="a>b" disabled><BR/>[fr:done]',
    '<p>[fr:Àñ\U0001F600 mixed]</p>',
    '<pre><code>both <b>raw</b></code></pre><p>[fr:After]</p>',
]

assert len(EXPECTED) == len(conftest.TRICKY_PAGES)


def test_marking_exact(pages, translator):
    for html, expected in zip(pages, EXPECTED):
        out = translator.translate_response(
            "text/html", None, html.encode("utf-8"), "en", "fr", conftest.marking_fn
        )
        assert out.decode("utf-8") == expected, html
