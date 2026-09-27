from pagetrans.memory import TranslationMemory


def test_put_get_roundtrip(tmp_path):
    mem = TranslationMemory(str(tmp_path / "mem.sqlite"))
    mem.put_many("en>es", {"hello": "hola", "bye": "adiós"})
    assert mem.get_many("en>es", ["hello", "bye", "missing"]) == {
        "hello": "hola",
        "bye": "adiós",
    }
    mem.close()


def test_pairs_are_isolated(tmp_path):
    mem = TranslationMemory(str(tmp_path / "mem.sqlite"))
    mem.put_many("en>es", {"hello": "hola"})
    assert mem.get_many("en>de", ["hello"]) == {}
    mem.close()


def test_persists_across_restarts(tmp_path):
    path = str(tmp_path / "mem.sqlite")
    TranslationMemory(path).put_many("en>fr", {"cat": "chat"})
    mem = TranslationMemory(path)
    assert mem.get_many("en>fr", ["cat"]) == {"cat": "chat"}
    mem.close()


def test_large_batch(tmp_path):
    mem = TranslationMemory(str(tmp_path / "mem.sqlite"))
    pairs = {f"src{i}": f"dst{i}" for i in range(3000)}
    mem.put_many("en>de", pairs)
    assert mem.get_many("en>de", list(pairs)) == pairs
    mem.close()


def test_empty_inputs(tmp_path):
    mem = TranslationMemory(":memory:")
    assert mem.get_many("en>es", []) == {}
    mem.put_many("en>es", {})
    mem.close()
