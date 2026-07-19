import logging
import threading
from typing import Optional, TYPE_CHECKING

import numpy as np

from config import get_settings

if TYPE_CHECKING:
    from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

_model: "Optional[SentenceTransformer]" = None
_model_lock = threading.Lock()


def _get_model() -> "SentenceTransformer":
    global _model
    if _model is None:
        with _model_lock:
            if _model is None:
                from sentence_transformers import SentenceTransformer
                _model = SentenceTransformer("all-MiniLM-L6-v2")
    return _model


def embed(texts) -> np.ndarray:
    was_single = isinstance(texts, str)
    if was_single:
        texts = [texts]

    api_key = (get_settings().openai_api_key or "").strip()
    if not api_key.startswith("sk-") or api_key.startswith("sk-or-"):
        # Placeholder text, comments, or an OpenRouter key — not usable for
        # OpenAI embeddings; go straight to the local model.
        api_key = ""
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
            logger.warning("OpenAI embedding error: %s", e)

    if result is None:
        try:
            result = _get_model().encode(texts)
        except Exception as e:
            logger.warning("SentenceTransformer error, falling back to zeros: %s", e)
            result = np.zeros((len(texts), 384))

    return result[0] if was_single else result
