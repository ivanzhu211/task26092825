"""编排：解压 -> 切分 -> 批量翻译 -> 写回 -> 回压。任何异常都原样返回。"""

from __future__ import annotations

from collections.abc import Callable, Sequence

from .compression import compress, decompress
from .headers import is_supported_lang_pair, is_translatable_html, normalize_encoding
from .memory import TranslationMemory
from .text import chunk_text, decode_entities, escape_translation, split_affixes
from .tokenizer import tokenize

TranslateFn = Callable[[list[str], str, str], Sequence[str]]

MAX_BATCH = 200
MAX_CHARS = 5000


class HtmlTranslator:
    def __init__(self, cache_path: str = "translation_memory.sqlite3") -> None:
        self._tm = TranslationMemory(cache_path)

    def close(self) -> None:
        self._tm.close()

    def translate_response(
        self,
        content_type: str | None,
        content_encoding: str | None,
        body: bytes,
        source_lang: str,
        target_lang: str,
        translate_fn: TranslateFn,
    ) -> bytes:
        """翻译响应体；任何无法处理的情况原样返回。"""
        try:
            return self._translate(
                content_type, content_encoding, body, source_lang, target_lang, translate_fn
            )
        except Exception:
            return body

    def _translate(
        self,
        content_type: str | None,
        content_encoding: str | None,
        body: bytes,
        source_lang: str,
        target_lang: str,
        translate_fn: TranslateFn,
    ) -> bytes:
        if not isinstance(body, (bytes, bytearray)):
            return body
        body = bytes(body)
        source_lang = (source_lang or "").lower()
        target_lang = (target_lang or "").lower()
        if not is_supported_lang_pair(source_lang, target_lang):
            return body
        if not is_translatable_html(content_type):
            return body
        encoding = normalize_encoding(content_encoding)
        if encoding is None:
            return body
        unpacked = decompress(body, encoding)
        if unpacked is None:
            return body
        raw, scheme = unpacked
        try:
            html = raw.decode("utf-8")
        except UnicodeDecodeError:
            return body
        new_html = self._translate_html(html, source_lang, target_lang, translate_fn)
        return compress(new_html.encode("utf-8"), scheme)

    def _translate_html(
        self, html: str, source_lang: str, target_lang: str, translate_fn: TranslateFn
    ) -> str:
        tokens = tokenize(html)

        # 每个文本 token -> (前空白, 切分后的片列表, 后空白)；译文与原文相同则置 None 保留原字节
        plan: list[list | None] = []
        unique_pieces: list[str] = []
        seen: set[str] = set()
        for token in tokens:
            if not token.is_text:
                plan.append(None)
                continue
            prefix, core, suffix = split_affixes(token.raw)
            if not core:
                plan.append(None)
                continue
            decoded = decode_entities(core)
            if not decoded:
                plan.append(None)
                continue
            pieces = chunk_text(decoded, MAX_CHARS)
            plan.append([prefix, pieces, suffix])
            for piece in pieces:
                if piece not in seen:
                    seen.add(piece)
                    unique_pieces.append(piece)

        translations = self._tm.get_many(source_lang, target_lang, unique_pieces)
        missing = [p for p in unique_pieces if p not in translations]
        for start in range(0, len(missing), MAX_BATCH):
            batch = missing[start:start + MAX_BATCH]
            try:
                results = list(translate_fn(batch, source_lang, target_lang))
            except Exception:
                results = []
            pairs = []
            for piece, translated in zip(batch, results):
                if not isinstance(translated, str):
                    translated = piece
                translations[piece] = translated
                pairs.append((piece, translated))
            for piece in batch[len(results):]:
                translations[piece] = piece
            if pairs:
                try:
                    self._tm.put_many(source_lang, target_lang, pairs)
                except Exception:
                    pass

        parts: list[str] = []
        for token, entry in zip(tokens, plan):
            if entry is None:
                parts.append(token.raw)
                continue
            prefix, pieces, suffix = entry
            joined = "".join(translations.get(p, p) for p in pieces)
            if joined == "".join(pieces):
                parts.append(token.raw)  # 译文与原文相同：保留原字节
            else:
                parts.append(prefix + escape_translation(joined) + suffix)
        return "".join(parts)


def translate_response(
    content_type: str | None,
    content_encoding: str | None,
    body: bytes,
    source_lang: str,
    target_lang: str,
    translate_fn: TranslateFn,
    cache_path: str = "translation_memory.sqlite3",
) -> bytes:
    """一次性便捷入口。"""
    translator = HtmlTranslator(cache_path)
    try:
        return translator.translate_response(
            content_type, content_encoding, body, source_lang, target_lang, translate_fn
        )
    finally:
        translator.close()
