import time
import numpy as np
from typing import List, Optional
from app.core.config import settings
from app.core.logging import logger

try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False

class SemanticService:
    def __init__(self):
        if not SENTENCE_TRANSFORMERS_AVAILABLE:
            raise ImportError(
                "sentence-transformers package is not installed. "
                "This is required for all-MiniLM-L6-v2 semantic scoring."
            )
        try:
            logger.info(f"Loading SentenceTransformer model '{settings.embedding_model}'...")
            self.model = SentenceTransformer(settings.embedding_model)
            logger.info("SentenceTransformer model successfully loaded.")
        except Exception as e:
            logger.error(f"Failed to load SentenceTransformer model: {e}")
            raise e

    def get_embedding(self, text: str) -> List[float]:
        if not text:
            return [0.0] * 384  # Return zero vector for all-MiniLM-L6-v2 size (384-dimensional)
        try:
            text_cleaned = text.replace("\n", " ").strip()
            embedding = self.model.encode([text_cleaned])[0]
            return embedding.tolist()
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            raise e

    def compute_similarity(self, text1: str, text2: str) -> float:
        """Computes cosine similarity between two texts."""
        try:
            emb1 = self.get_embedding(text1)
            emb2 = self.get_embedding(text2)
            
            v1 = np.array(emb1)
            v2 = np.array(emb2)
            
            dot_product = np.dot(v1, v2)
            norm_v1 = np.linalg.norm(v1)
            norm_v2 = np.linalg.norm(v2)
            
            if norm_v1 == 0 or norm_v2 == 0:
                return 0.0
                
            return float(dot_product / (norm_v1 * norm_v2))
        except Exception as e:
            logger.error(f"Failed to compute similarity: {e}")
            raise e

