import os
import numpy as np

def embed(texts) -> np.ndarray:
    was_single = isinstance(texts, str)
    if was_single:
        texts = [texts]
        
    api_key = os.getenv("OPENAI_API_KEY")
    result = None
    if api_key:
        try:
            import openai
            client = openai.OpenAI(api_key=api_key)
            response = client.embeddings.create(
                input=texts,
                model="text-embedding-3-small"
            )
            embeddings = [data.embedding for data in response.data]
            result = np.array(embeddings)
        except Exception as e:
            print(f"OpenAI embedding error: {e}")
            
    if result is None:
        try:
            from sentence_transformers import SentenceTransformer
            if not hasattr(embed, "_model"):
                embed._model = SentenceTransformer("all-MiniLM-L6-v2")
            result = embed._model.encode(texts)
        except Exception as e:
            print(f"SentenceTransformer error: {e}")
            result = np.zeros((len(texts), 384))
            
    return result[0] if was_single else result
