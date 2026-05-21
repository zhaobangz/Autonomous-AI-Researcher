"""Tests for memory/embeddings.py — fallback paths and thread-safe model caching."""
import threading
from unittest.mock import MagicMock, patch

import numpy as np
import pytest


@pytest.fixture(autouse=True)
def _reset_model_cache():
    """Reset the module-level model singleton between tests."""
    import memory.embeddings as emb
    emb._model = None
    yield
    emb._model = None


class TestEmbedShape:
    def _settings_without_openai(self):
        """Return a settings stub whose openai_api_key is None, bypassing .env."""
        stub = MagicMock()
        stub.openai_api_key = None
        return stub

    def test_returns_384_when_openai_unavailable_and_st_fails(self):
        with patch("memory.embeddings.get_settings", return_value=self._settings_without_openai()), \
             patch("memory.embeddings._get_model", side_effect=RuntimeError("no model")):
            from memory.embeddings import embed
            result = embed("hello world")
        assert isinstance(result, np.ndarray)
        assert result.shape == (384,)

    def test_uses_mocked_sentence_transformer(self):
        fake_model = MagicMock()
        fake_model.encode.return_value = np.ones((1, 384), dtype=float)
        with patch("memory.embeddings.get_settings", return_value=self._settings_without_openai()), \
             patch("memory.embeddings._get_model", return_value=fake_model):
            from memory.embeddings import embed
            result = embed("hello world")
        assert result.shape == (384,)
        assert np.all(result == 1)


class TestThreadSafety:
    def test_concurrent_get_model_initializes_once(self):
        """Many threads racing on _get_model() must call the constructor exactly once."""
        call_count = {"n": 0}

        class FakeST:
            def __init__(self, _name):
                call_count["n"] += 1
                # Small sleep widens the race window
                import time
                time.sleep(0.01)

            def encode(self, texts):
                return np.zeros((len(texts), 384))

        # Patch the lazy import inside _get_model
        with patch.dict(
            "sys.modules",
            {"sentence_transformers": MagicMock(SentenceTransformer=FakeST)},
        ):
            from memory.embeddings import _get_model

            errors = []

            def worker():
                try:
                    _get_model()
                except Exception as e:  # pragma: no cover - assertion below
                    errors.append(e)

            threads = [threading.Thread(target=worker) for _ in range(16)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()

        assert errors == []
        assert call_count["n"] == 1
