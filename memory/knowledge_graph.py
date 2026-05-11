import os, json, uuid
import asyncio
import networkx as nx
import numpy as np
from pathlib import Path
from typing import List, Dict, Any, Optional
from memory.embeddings import embed

EMBEDDING_DIMENSION = 384


def _coerce_embedding(value: Any) -> np.ndarray:
    """Return a 1-D float embedding array, falling back safely on bad values."""
    try:
        arr = np.asarray(value, dtype=float).reshape(-1)
        if arr.size == 0 or not np.all(np.isfinite(arr)):
            raise ValueError("empty or non-finite embedding")
        return arr
    except Exception:
        return np.zeros(EMBEDDING_DIMENSION, dtype=float)


def _embedding_to_json(value: Any) -> List[float]:
    """Convert an embedding-like object to JSON-safe floats."""
    return [float(x) for x in _coerce_embedding(value).tolist()]


def _cosine_sim(a: Any, b: Any) -> float:
    a_arr = _coerce_embedding(a)
    b_arr = _coerce_embedding(b)
    if a_arr.shape != b_arr.shape:
        min_len = min(a_arr.size, b_arr.size)
        if min_len == 0:
            return 0.0
        a_arr = a_arr[:min_len]
        b_arr = b_arr[:min_len]
    denom = np.linalg.norm(a_arr) * np.linalg.norm(b_arr)
    if denom <= 1e-10:
        return 0.0
    return float(np.dot(a_arr, b_arr) / denom)

class KnowledgeGraph:
    _lock: Optional[asyncio.Lock] = None

    def __init__(self):
        base_dir = Path(os.getenv("RUNS_DIR", "./runs")).resolve()
        base_dir.mkdir(parents=True, exist_ok=True)
        self.graph_path = base_dir / "global_graph.json"
        self.graph = self._load_graph()

    def _load_graph(self) -> nx.DiGraph:
        if not self.graph_path.exists():
            return nx.DiGraph()
        try:
            data = json.loads(self.graph_path.read_text())
            edges_key = "links" if "links" in data else "edges"
            graph = nx.node_link_graph(data, edges=edges_key)
            # Normalize any legacy/bad embedding payloads eagerly.
            for _, node_data in graph.nodes(data=True):
                if "embedding" in node_data:
                    node_data["embedding"] = _embedding_to_json(node_data["embedding"])
            return graph
        except Exception:
            backup_path = self.graph_path.with_suffix(".invalid.json")
            try:
                self.graph_path.replace(backup_path)
            except OSError:
                pass
            return nx.DiGraph()

    @classmethod
    def _get_lock(cls) -> asyncio.Lock:
        """Lazily create the asyncio.Lock (must be in a running loop)."""
        if cls._lock is None:
            cls._lock = asyncio.Lock()
        return cls._lock

    def save(self):
        self.graph_path.write_text(json.dumps(nx.node_link_data(self.graph, edges="links")))

    async def add_paper(self, title, url, summary, run_id):
        if not summary: return
        node_id = url if url else str(uuid.uuid4())
        # Compute embedding OUTSIDE the lock to avoid blocking
        new_emb = _coerce_embedding(await asyncio.to_thread(embed, summary))
        
        lock = self._get_lock()
        async with lock:
            self.graph.add_node(node_id, title=title, url=url, summary=summary, run_id=run_id, embedding=_embedding_to_json(new_emb))
            for other_id, other_data in list(self.graph.nodes(data=True)):
                if other_id == node_id or "embedding" not in other_data: continue
                score = _cosine_sim(new_emb, other_data["embedding"])
                if score > 0.75:
                    self.graph.add_edge(node_id, other_id, weight=score)
                    self.graph.add_edge(other_id, node_id, weight=score)
            await asyncio.to_thread(self.save)

    def query_related(self, text, k=5):
        """
        Query related nodes by cosine similarity.
        
        NOTE: This is O(n) over all nodes. For large graphs (>1000 nodes),
        consider replacing with a ChromaDB ANN index for O(log n) queries.
        This method is synchronous — callers should wrap in asyncio.to_thread.
        """
        query_emb = _coerce_embedding(embed(text))
        scores = []
        for node_id, data in self.graph.nodes(data=True):
            if "embedding" in data:
                scores.append((_cosine_sim(query_emb, data["embedding"]), node_id, data))
        scores.sort(reverse=True)
        results = []
        for score, node_id, data in scores[:k]:
            out = {k: v for k, v in data.items() if k != "embedding"}
            out["similarity"] = score
            results.append(out)
        return results
