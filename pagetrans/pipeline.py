"""Orchestration: decode, scan, translate, reassemble."""

from __future__ import annotations

from typing import Callable

from . import codec, scanner
from .headers import (
    is_translatable_html,
    normalize_content_encoding,
    parse_content_type,
)
from .memory import TranslationMemory
from .textutil import (
    chunk_text,
    decode_entities,
    escape_translation,
    split_edge_whitespace,
)

TranslateFn = Callable[[list[str], str, str], list[str]]

MAX_BATCH = 200

SUPPORTED_LANG_PAIRS = frozenset(
    (a, b)
    for a, b in (("en", "es"), ("en", "de"), ("en", "fr"))
    for a, b in ((a, b), (b, a))
)


def translate_response(
    content_type: str | None,
    content_encoding: str | None,
    body: bytes,
    source_lang: str,
    target_lang: str,
    translate_fn: TranslateFn,
    memory_path: str,
) -> bytes:
    """Translate an HTML response body; return the new body bytes.

    Returns the input unchanged for anything unsupported or unreadable.
    """
    try:
        return _translate(
            content_type,
            content_encoding,
            body,
            source_lang,
            target_lang,
            translate_fn,
            memory_path,
        )
    except Exception:
        return body


def _translate(
    content_type: str | None,
    content_encoding: str | None,
    body: bytes,
    source_lang: str,
    target_lang: str,
    translate_fn: TranslateFn,
    memory_path: str,
) -> bytes:
    if (source_lang, target_lang) not in SUPPORTED_LANG_PAIRS:
        return body
    mime, charset = parse_content_type(content_type)
    if not is_translatable_html(mime, charset):
        return body
    unpacked = codec.decompress(normalize_content_encoding(content_encoding), body)
    if unpacked is None:
        return body
    data, effective_encoding = unpacked
    try:
        html_text = data.decode("utf-8", "strict")
    except UnicodeDecodeError:
        return body

    parts = scanner.scan(html_text)

    # Per text part: (leading_ws, raw_core, trailing_ws, decoded_core).
    # Parts whose core is empty (whitespace only) are left untouched.
    entries: list[tuple[str, str, str, str] | None] = []
    unique: list[str] = []
    seen: set[str] = set()
    for part in parts:
        if not part.is_text:
            entries.append(None)
            continue
        lead, core, trail = split_edge_whitespace(part.raw)
        if not core:
            entries.append(None)
            continue
        decoded = decode_entities(core)
        entries.append((lead, core, trail, decoded))
        if decoded not in seen:
            seen.add(decoded)
            unique.append(decoded)

    translations: dict[str, str] = {}
    if unique:
        lang_pair = f"{source_lang}>{target_lang}"
        memory = TranslationMemory(memory_path)
        try:
            translations.update(memory.get_many(lang_pair, unique))
            missing = [text for text in unique if text not in translations]
            if missing:
                fresh = _translate_texts(
                    missing, source_lang, target_lang, translate_fn
                )
                memory.put_many(lang_pair, fresh)
                translations.update(fresh)
        finally:
            memory.close()

    out: list[str] = []
    append = out.append
    for part, entry in zip(parts, entries):
        if entry is None:
            append(part.raw)
            continue
        lead, core, trail, decoded = entry
        translated = translations.get(decoded)
        if translated is None or translated == decoded:
            # untranslated or identical to the source: keep original bytes
            append(part.raw)
        else:
            append(lead)
            append(escape_translation(translated))
            append(trail)

    return codec.compress(effective_encoding, "".join(out).encode("utf-8"))


def _translate_texts(
    texts: list[str],
    source_lang: str,
    target_lang: str,
    translate_fn: TranslateFn,
) -> dict[str, str]:
    """Translate unique source texts, chunking and batching as required."""
    pieces: list[str] = []
    spans: list[tuple[int, int]] = []  # [start, end) of each text's pieces
    for text in texts:
        chunks = chunk_text(text)
        spans.append((len(pieces), len(pieces) + len(chunks)))
        pieces.extend(chunks)

    translated_pieces: list[str] = []
    for i in range(0, len(pieces), MAX_BATCH):
        batch = pieces[i : i + MAX_BATCH]
        result = translate_fn(batch, source_lang, target_lang)
        if (
            not isinstance(result, (list, tuple))
            or len(result) != len(batch)
            or any(not isinstance(item, str) for item in result)
        ):
            raise ValueError("translate_fn returned an invalid result")
        translated_pieces.extend(result)

    return {
        text: "".join(translated_pieces[start:end])
        for text, (start, end) in zip(texts, spans)
    }
