"""Tests for memory/vector_store.py — the Pinecone index dimension contract.

embed() chooses its model at call time (1536-wide via OpenAI, 384-wide via the
local model), so the index has to be built at whatever width is actually in use.
A hard-coded width silently rejects every upsert.
"""
import sys
from unittest.mock import MagicMock, patch

import numpy as np
import pytest


@pytest.fixture(autouse=True)
def _reset_dimension_cache():
    """Drop the probed-dimension singleton between tests."""
    import memory.embeddings as emb
    emb._dimension = None
    yield
    emb._dimension = None


class _IndexDescription:
    """Stands in for the index objects pinecone's list_indexes() returns."""

    def __init__(self, name, dimension):
        self.name = name
        self.dimension = dimension


def _fake_pinecone(existing=()):
    """A stand-in pinecone module, plus the dict recording create_index kwargs."""
    created = {}

    class FakePinecone:
        def __init__(self, api_key=None):
            self.api_key = api_key

        def list_indexes(self):
            return list(existing)

        def create_index(self, **kwargs):
            created.update(kwargs)

        def Index(self, name):
            return MagicMock()

    return MagicMock(Pinecone=FakePinecone, ServerlessSpec=MagicMock()), created


def _pinecone_settings():
    stub = MagicMock()
    stub.vector_backend = "pinecone"
    stub.pinecone_api_key = "pc-test-key"
    stub.pinecone_index = "research-context"
    return stub


def _build_store(module, width):
    """Construct a VectorStore against the fake module and a fixed embed width."""
    from memory.vector_store import VectorStore

    with patch.dict(sys.modules, {"pinecone": module}), \
         patch("memory.vector_store.get_settings", return_value=_pinecone_settings()), \
         patch("memory.embeddings.embed", return_value=np.zeros(width)):
        return VectorStore(run_id="test-run")


class TestEmbeddingDimension:
    def test_probes_the_live_embedder(self):
        from memory.embeddings import embedding_dimension

        with patch("memory.embeddings.embed", return_value=np.zeros(384)):
            assert embedding_dimension() == 384

    def test_result_is_cached(self):
        from memory.embeddings import embedding_dimension

        with patch("memory.embeddings.embed", return_value=np.zeros(384)) as probe:
            embedding_dimension()
            embedding_dimension()
        assert probe.call_count == 1


class TestPineconeIndexCreation:
    def test_creates_index_at_local_model_width(self):
        module, created = _fake_pinecone()
        _build_store(module, width=384)
        assert created["dimension"] == 384
        assert created["name"] == "research-context"
        assert created["metric"] == "cosine"

    def test_creates_index_at_openai_width(self):
        """Same code path must follow the embedder up to 1536, not pin to one width."""
        module, created = _fake_pinecone()
        _build_store(module, width=1536)
        assert created["dimension"] == 1536

    def test_reuses_index_of_matching_width(self):
        module, created = _fake_pinecone(
            existing=[_IndexDescription("research-context", 384)]
        )
        _build_store(module, width=384)
        assert created == {}

    def test_run_id_namespaces_reads_and_writes(self):
        """One shared index must still isolate runs, as the chroma backend does."""
        module, _ = _fake_pinecone(
            existing=[_IndexDescription("research-context", 384)]
        )
        store = _build_store(module, width=384)
        store.index = MagicMock()
        store.index.query.return_value = MagicMock(matches=[])

        with patch("memory.embeddings.embed", return_value=np.zeros(384)):
            store.add(texts=["a note"], metadatas=[{"source": "t"}])
            store.query("a note")

        assert store.index.upsert.call_args.kwargs["namespace"] == "test-run"
        assert store.index.query.call_args.kwargs["namespace"] == "test-run"

    def test_rejects_index_of_mismatched_width(self):
        module, _ = _fake_pinecone(
            existing=[_IndexDescription("research-context", 1536)]
        )
        with pytest.raises(RuntimeError) as excinfo:
            _build_store(module, width=384)
        message = str(excinfo.value)
        assert "1536" in message and "384" in message
