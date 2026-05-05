# memory/knowledge_graph.py
"""
Global cross-run citation and related insights graph memory.
"""
import os
import json
import uuid
import asyncio
import networkx as nx
import numpy as np
from pathlib import Path
from typing import List, Dict, Any, Optional
from memory.embeddings import embed

class KnowledgeGraph:
    def __init__(self):
        self._lock = asyncio.Lock()
        base_dir = Path(os.getenv("RUNS_DIR", "./runs")).resolve()
        base_dir.mkdir(parents=True, exist_ok=True)
        self.graph_path = base_dir / "global_graph.json"
        
        if self.graph_path.exists():
            with open(self.graph_path, "r") as f:
                data = json.load(f)
                self.graph = nx.node_link_graph(data)
                for node_id, d in self.graph.nodes(data=True):
                    if "embedding" in d and isinstance(d["embedding"], list):
                        self.graph.nodes[node_id]["embedding"] = np.array(d["embedding"])
        else:
            self.graph = nx.DiGraph()

    def save(self):
        import copy
        data = nx.node_link_data(self.graph)
        for node in data["nodes"]:
            if "embedding" in node and isinstance(node["embedding"], np.ndarray):
                node["embedding"] = node["embedding"].tolist()
        with open(self.graph_path, "w") as f:
            json.dump(data, f)

    async def add_paper(self, title: str, url: str, summary: str, run_id: str):
        async with self._lock:
            node_id = url if url else str(uuid.uuid4())
            if not summary:
                return
                
            new_emb = embed(summary)
            
            self.graph.add_node(
                node_id,
                title=title,
                url=url,
                summary=summary,
                run_id=run_id,
                embedding=new_emb
            )
            
            def cosine_sim(a, b):
                return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-10)

            for other_id, other_data in list(self.graph.nodes(data=True)):
                if other_id == node_id:
                    continue
                if "embedding" in other_data:
                    score = cosine_sim(new_emb, np.array(other_data["embedding"]))
                    if score > 0.75:
                        self.graph.add_edge(node_id, other_id, weight=float(score))
                        self.graph.add_edge(other_id, node_id, weight=float(score))
                        
            self.save()

    def query_related(self, text: str, k: int = 5) -> List[Dict[str, Any]]:
        query_emb = embed(text)
        
        def cosine_sim(a, b):
            return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-10)

        scores = []
        for node_id, data in self.graph.nodes(data=True):
            if "embedding" in data:
                score = cosine_sim(query_emb, np.array(data["embedding"]))
                scores.append((score, node_id, data))
                
        scores.sort(key=lambda x: x[0], reverse=True)
        results = []
        for score, node_id, data in scores[:k]:
            out = data.copy()
            out.pop("embedding", None)
            out["similarity"] = score
            results.append(out)
            
        return results
