"""SQLite-backed translation memory."""

from __future__ import annotations

import sqlite3

_SCHEMA = """
CREATE TABLE IF NOT EXISTS translation_memory (
    lang_pair TEXT NOT NULL,
    source TEXT NOT NULL,
    translation TEXT NOT NULL,
    PRIMARY KEY (lang_pair, source)
)
"""

_BATCH_VARS = 500  # stay well under SQLite's host-parameter limit


class TranslationMemory:
    def __init__(self, path: str) -> None:
        self._conn = sqlite3.connect(path)
        self._conn.execute(_SCHEMA)
        self._conn.commit()

    def get_many(self, lang_pair: str, texts: list[str]) -> dict[str, str]:
        found: dict[str, str] = {}
        if not texts:
            return found
        cursor = self._conn.cursor()
        for i in range(0, len(texts), _BATCH_VARS):
            batch = texts[i : i + _BATCH_VARS]
            marks = ",".join("?" * len(batch))
            cursor.execute(
                f"SELECT source, translation FROM translation_memory"
                f" WHERE lang_pair = ? AND source IN ({marks})",
                [lang_pair, *batch],
            )
            found.update(cursor.fetchall())
        return found

    def put_many(self, lang_pair: str, pairs: dict[str, str]) -> None:
        if not pairs:
            return
        with self._conn:
            self._conn.executemany(
                "INSERT OR REPLACE INTO translation_memory"
                " (lang_pair, source, translation) VALUES (?, ?, ?)",
                [(lang_pair, src, dst) for src, dst in pairs.items()],
            )

    def close(self) -> None:
        self._conn.close()
