# memory/vector_store.py
"""
Vector memory module supporting ChromaDB and Pinecone globally.
"""
import uuid
from typing import List, Dict, Any
from pydantic import BaseModel

from config import get_settings

class Hit(BaseModel):
    id: str
    text: str
    metadata: Dict[str, Any]
    score: float

class VectorStore:
    def __init__(self, run_id: str):
        settings = get_settings()
        self.run_id = run_id
        self.backend = settings.vector_backend

        if self.backend == "chroma":
            import chromadb
            run_chroma_dir = settings.runs_dir / run_id / "chroma"
            run_chroma_dir.mkdir(parents=True, exist_ok=True)
            self.client = chromadb.PersistentClient(path=str(run_chroma_dir))
            self.collection = self.client.get_or_create_collection("research_context")
        elif self.backend == "pinecone":
            from pinecone import Pinecone, ServerlessSpec
            pc = Pinecone(api_key=settings.pinecone_api_key)
            index_name = settings.pinecone_index
            if index_name not in [i.name for i in pc.list_indexes()]:
                pc.create_index(
                    name=index_name,
                    dimension=1536,
                    metric="cosine",
                    spec=ServerlessSpec(cloud="aws", region="us-east-1")
                )
            self.index = pc.Index(index_name)

    def add(self, texts: List[str], metadatas: List[Dict[str, Any]], ids: List[str] = None):
        if not texts:
            return
        if not ids:
            ids = [str(uuid.uuid4()) for _ in texts]
            
        if self.backend == "chroma":
            self.collection.add(documents=texts, metadatas=metadatas, ids=ids)
        elif self.backend == "pinecone":
            from memory.embeddings import embed
            embeddings = [embed(t) for t in texts]
            vectors = []
            for id_, emb, meta, text in zip(ids, embeddings, metadatas, texts):
                m = meta.copy()
                m["text"] = text
                vectors.append({"id": id_, "values": emb.tolist(), "metadata": m})
            self.index.upsert(vectors=vectors)

    def query(self, text: str, k: int = 5) -> List[Hit]:
        if self.backend == "chroma":
            results = self.collection.query(query_texts=[text], n_results=k)
            hits = []
            if results and results.get("documents") and results["documents"][0]:
                docs = results["documents"][0]
                metas = results["metadatas"][0]
                distances = results["distances"][0] if "distances" in results and results["distances"] else [0.0]*len(docs)
                ids = results["ids"][0]
                for d, m, dist, id_ in zip(docs, metas, distances, ids):
                    hits.append(Hit(id=id_, text=d, metadata=m or {}, score=dist))
            return hits
        elif self.backend == "pinecone":
            from memory.embeddings import embed
            query_emb = embed(text).tolist()
            response = self.index.query(vector=query_emb, top_k=k, include_metadata=True)
            hits = []
            for match in response.matches:
                m = match.metadata or {}
                t = m.get("text", "")
                hits.append(Hit(id=match.id, text=t, metadata=m, score=match.score))
            return hits
        raise RuntimeError(f"Unknown vector backend: {self.backend}")
