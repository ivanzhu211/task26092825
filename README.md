# html-translate

内网翻译代理用的 HTML 页面翻译库。代理拿到上游响应后，把
Content-Type、Content-Encoding、响应体字节和语言对交给本模块，
模块抽出正文文字交给上层传入的批量翻译函数，再把译文写回页面。

## 用法

```python
from html_translate import HtmlTranslator

translator = HtmlTranslator("translation_memory.sqlite3")  # 翻译记忆，重启后仍有效

def my_translate(texts, source_lang, target_lang):
    # 调用本地翻译模型；len(texts) <= 200，每段 <= 5000 字符
    return model.translate(texts, source_lang, target_lang)

new_body = translator.translate_response(
    content_type="text/html; charset=UTF-8",
    content_encoding="gzip",
    body=raw_body,
    source_lang="en",
    target_lang="fr",
    translate_fn=my_translate,
)
```

也有一次性入口 `html_translate.translate_response(..., cache_path=...)`。

## 行为约定

- 只处理 `text/html` 且字符集为 UTF-8 或未声明的响应；头部取值不区分大小写。
- 支持的语言对：en↔es、en↔de、en↔fr（共六组）。
- 压缩：gzip、deflate（带 zlib 头和裸 deflate 都认）、不压缩；按原方式压回。
- 标签、属性、注释、doctype 以及 script/style/code/pre 的内容逐字节保留；
  code/pre 未闭合时从它开始到文末都不翻。
- 文本段首尾空白不送翻译；字符引用按 HTML5 解码后送翻译，
  写回时只转义 `&` `<` `>`；译文与原文相同的段保留原字节。
- 超长文本在 5000 字符内最靠后的空白处切开（空白归前一片），找不到空白就硬切；
  每次调用翻译函数最多 200 段。
- 翻译记忆按 (源语言, 目标语言, 原文) 缓存在本地 SQLite；
  同一页面里重复出现的文字只送一次。
- 任何无法处理的输入（不支持的类型/语言对/字符集/压缩、非法 UTF-8、
  解压失败、翻译函数抛异常等）一律原样返回，不抛异常。

## 测试

```bash
python3 -m pytest tests/ -q
```
