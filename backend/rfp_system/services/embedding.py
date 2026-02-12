"""
Embedding service - generates vector embeddings for text using sentence-transformers
"""
from typing import List, Union
from sentence_transformers import SentenceTransformer
import numpy as np


class EmbeddingService:
    """Generate embeddings for text chunks using local sentence-transformers"""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """
        Initialize embedding service

        Args:
            model_name: Name of sentence-transformers model to use
                       'all-MiniLM-L6-v2' is fast, lightweight, and good quality
                       384-dimensional embeddings
        """
        self.model_name = model_name
        print(f"Loading embedding model: {model_name}...")
        self.model = SentenceTransformer(model_name)
        print(f"Model loaded. Embedding dimension: {self.model.get_sentence_embedding_dimension()}")

    def embed_text(self, text: str) -> np.ndarray:
        """
        Generate embedding for a single text

        Args:
            text: Text to embed

        Returns:
            Numpy array with embedding vector
        """
        embedding = self.model.encode(text, convert_to_numpy=True)
        return embedding

    def embed_batch(self, texts: List[str], batch_size: int = 32) -> List[np.ndarray]:
        """
        Generate embeddings for multiple texts efficiently

        Args:
            texts: List of texts to embed
            batch_size: Number of texts to process at once

        Returns:
            List of embedding vectors
        """
        embeddings = self.model.encode(
            texts,
            batch_size=batch_size,
            convert_to_numpy=True,
            show_progress_bar=len(texts) > 10
        )
        return embeddings

    def get_embedding_dimension(self) -> int:
        """Get the dimension of embeddings produced by this model"""
        return self.model.get_sentence_embedding_dimension()

    def compute_similarity(self, text1: str, text2: str) -> float:
        """
        Compute cosine similarity between two texts

        Args:
            text1: First text
            text2: Second text

        Returns:
            Similarity score between -1 and 1 (1 = identical)
        """
        emb1 = self.embed_text(text1)
        emb2 = self.embed_text(text2)

        # Cosine similarity
        similarity = np.dot(emb1, emb2) / (np.linalg.norm(emb1) * np.linalg.norm(emb2))
        return float(similarity)


# Singleton instance for reuse across requests
_embedding_service = None

def get_embedding_service() -> EmbeddingService:
    """Get singleton instance of embedding service"""
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    return _embedding_service
