"""
Embedding Provider Abstraction and Factory for MOMO AI Workflow.
Supports DistilBERT (local default) and deterministic Mock embeddings.
"""
import os
import hashlib
import logging
from abc import ABC, abstractmethod
from typing import List, Optional

logger = logging.getLogger(__name__)

DEFAULT_DIM = 384


class EmbeddingProvider(ABC):
    """Abstract interface for dense vector embedding generation."""

    @abstractmethod
    def embed_text(self, text: str) -> List[float]:
        pass

    @abstractmethod
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        pass


class DistilBERTProvider(EmbeddingProvider):
    """Wraps MOMO's local DistilBERT embedding service."""

    def __init__(self, model_name: Optional[str] = None):
        from nlp.distilbert_service import DistilBERTEmbeddingService
        self.service = DistilBERTEmbeddingService(model_name=model_name)

    def embed_text(self, text: str) -> List[float]:
        return self.service.embed_text(text)

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        return self.service.embed_batch(texts)


class MockEmbeddingProvider(EmbeddingProvider):
    """Deterministic hash-based embedding for testing and offline execution."""

    def __init__(self, dim: int = DEFAULT_DIM):
        self.dim = dim

    def embed_text(self, text: str) -> List[float]:
        if not text:
            return [0.0] * self.dim
        # Deterministic float vector from md5 digests
        res = []
        for i in range(self.dim):
            h = hashlib.md5(f"{text}_{i}".encode('utf-8')).hexdigest()
            val = (int(h[:4], 16) / 32768.0) - 1.0
            res.append(round(val, 4))
        # Normalize
        norm = sum(x * x for x in res) ** 0.5 or 1.0
        return [round(x / norm, 4) for x in res]

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        return [self.embed_text(t) for t in texts]


class EmbeddingFactory:
    """Factory selecting the configured embedding provider."""

    @classmethod
    def get_provider(cls) -> EmbeddingProvider:
        mock_mode = os.getenv("AI_MOCK_MODE", "").lower() in ("true", "1", "yes")
        provider_type = os.getenv("EMBEDDING_PROVIDER", "distilbert").lower()

        if mock_mode or provider_type == "mock":
            return MockEmbeddingProvider()

        if provider_type == "distilbert":
            try:
                return DistilBERTProvider()
            except Exception as e:
                logger.warning(f"Failed to initialize DistilBERT ({e}), falling back to MockEmbeddingProvider.")
                return MockEmbeddingProvider()

        raise ValueError(f"Unsupported EMBEDDING_PROVIDER '{provider_type}'. Supported: 'distilbert', 'mock'.")
