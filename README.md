# pagetrans

内网门户 / wiki 的 HTML 页面翻译库。代理由上游拿到响应后调用
`translate_response`，模块抽出正文文字交给调用方传入的批量翻译函数，
再把译文写回页面。无接口层，翻译记忆存本地 SQLite。

## 用法

```python
from pagetrans import translate_response

def my_translate(texts, source_lang, target_lang):
    # 调用本地翻译模型，返回与 texts 等长的译文列表
    ...

new_body = translate_response(
    content_type="text/html; charset=utf-8",   # 响应头取值，不区分大小写
    content_encoding="gzip",                   # gzip / deflate / 无
    body=raw_body_bytes,
    source_lang="en",
    target_lang="es",                          # en 与 es/de/fr 互译，共六组
    translate_fn=my_translate,
    memory_path="/var/cache/translation-memory.sqlite",
)
```

## 行为约定

- 只处理 `text/html` 且字符集为 UTF-8 或未声明的响应；其余一律原样返回。
- 支持 gzip、deflate（zlib 头与裸流都认）和不压缩；解压后翻译，按原方式压回。
- 只翻译标签之间的文字；script/style/code/pre 内容、注释、doctype、
  标签与属性逐字节保留。译文与原文相同的段保留原字节。
- 每次调用翻译函数最多 200 段，每段不超过 5000 字符（超长自动切分拼回）。
- 翻译记忆按「原文 + 语言对」缓存于 SQLite，重启后仍有效。
- 任何无法处理的输入都原样返回，不抛异常。

## 测试

```bash
python3 -m pytest tests/ -q
```
