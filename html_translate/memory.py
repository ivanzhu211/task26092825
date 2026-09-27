"""SQLite 翻译记忆：按 (源语言, 目标语言, 原文) 缓存，重启后仍有效。"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterable

_SCHEMA = """
CREATE TABLE IF NOT EXISTS translation_memory (
    source_lang TEXT NOT NULL,
    target_lang TEXT NOT NULL,
    source_text TEXT NOT NULL,
    translated_text TEXT NOT NULL,
    PRIMARY KEY (source_lang, target_lang, source_text)
)
"""


class TranslationMemory:
    def __init__(self, path: str) -> None:
        self._conn = sqlite3.connect(path)
        self._conn.execute(_SCHEMA)
        self._conn.commit()

    def get(self, source_lang: str, target_lang: str, source_text: str) -> str | None:
        row = self._conn.execute(
            "SELECT translated_text FROM translation_memory"
            " WHERE source_lang = ? AND target_lang = ? AND source_text = ?",
            (source_lang, target_lang, source_text),
        ).fetchone()
        return row[0] if row else None

    def get_many(
        self, source_lang: str, target_lang: str, texts: Iterable[str]
    ) -> dict[str, str]:
        result: dict[str, str] = {}
        for text in texts:
            cached = self.get(source_lang, target_lang, text)
            if cached is not None:
                result[text] = cached
        return result

    def put(self, source_lang: str, target_lang: str, source_text: str, translated: str) -> None:
        self.put_many(source_lang, target_lang, [(source_text, translated)])

    def put_many(
        self, source_lang: str, target_lang: str, pairs: Iterable[tuple[str, str]]
    ) -> None:
        self._conn.executemany(
            "INSERT OR REPLACE INTO translation_memory"
            " (source_lang, target_lang, source_text, translated_text)"
            " VALUES (?, ?, ?, ?)",
            ((source_lang, target_lang, src, dst) for src, dst in pairs),
        )
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()
