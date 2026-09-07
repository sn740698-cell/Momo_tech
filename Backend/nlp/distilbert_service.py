"""
DistilBERT Semantic Embedding Service for ChromaDB and Retrieval.
Generates dense vector embeddings for documents and search queries.
Features graceful fallback and torch inference_mode for low VRAM usage.
"""
import os
import re
import hashlib
import logging
from typing import List, Optional

from ai.gpu_manager import GPUManager

logger = logging.getLogger(__name__)

DEFAULT_DISTILBERT_MODEL = "distilbert-base-uncased"
EMBEDDING_DIM = 384


class DistilBERTEmbeddingService:
    """
    DistilBERT embedding generator with CUDA acceleration and CPU fallback.
    """

    def __init__(self, model_name: Optional[str] = None):
        self.model_name = model_name or os.getenv("DISTILBERT_MODEL", DEFAULT_DISTILBERT_MODEL)
        self.tokenizer = None
        self.model = None
        self._initialized = False
        self._device = GPUManager.get_preferred_device()

    def _lazy_init(self):
        if self._initialized:
            return
        self._initialized = True

        try:
            from transformers import AutoTokenizer, AutoModel
            import torch

            logger.info(f"Loading DistilBERT model '{self.model_name}' on device '{self._device}'...")
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_name, local_files_only=False)
            self.model = AutoModel.from_pretrained(self.model_name, local_files_only=False)
            self.model.to(self._device)
            self.model.eval()
            logger.info("DistilBERT initialized successfully.")
        except Exception as e:
            logger.warning(
                f"Could not load Hugging Face DistilBERT ({e}). "
                f"Using deterministic lightweight pseudo-embedding fallback."
            )
            self.model = None
            self.tokenizer = None

    def embed_text(self, text: str) -> List[float]:
        """
        Embeds a single string into a normalized dense vector.
        """
        results = self.embed_batch([text])
        return results[0] if results else [0.0] * EMBEDDING_DIM

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generates embeddings for a batch of text chunks.
        """
        if not texts:
            return []

        self._lazy_init()

        if self.model is not None and self.tokenizer is not None:
            try:
                import torch
                with torch.inference_mode():
                    inputs = self.tokenizer(
                        texts,
                        padding=True,
                        truncation=True,
                        max_length=512,
                        return_tensors="pt"
                    ).to(self._device)

                    outputs = self.model(**inputs)
                    # Mean pooling over token embeddings
                    attention_mask = inputs['attention_mask'].unsqueeze(-1)
                    embeddings = torch.sum(outputs.last_hidden_state * attention_mask, dim=1) / torch.clamp(attention_mask.sum(dim=1), min=1e-9)
                    # Normalize
                    embeddings = torch.nn.functional.normalize(embeddings, p=2, dim=1)
                    return embeddings.cpu().tolist()
            except Exception as e:
                logger.error(f"Error during DistilBERT inference: {e}")
                GPUManager.handle_cuda_oom("DistilBERT")

        # Deterministic lightweight fallback (hashing to dense vector)
        return [self._fallback_embed(t) for t in texts]

    def _fallback_embed(self, text: str) -> List[float]:
        """
        Generates a 384-dimensional deterministic token-hashed unit vector for testing or offline mode.
        Ensures semantic overlap between related phrases.
        """
        vec = [0.0] * EMBEDDING_DIM
        words = re.findall(r"\w+", text.lower())
        if not words:
            words = [text.lower()]
        for word in words:
            h = hashlib.sha256(word.encode("utf-8")).digest()
            for idx in range(EMBEDDING_DIM):
                byte_val = h[idx % len(h)]
                vec[idx] += (byte_val - 128) / 128.0
        # Normalize
        norm = sum(x * x for x in vec) ** 0.5 or 1.0
        return [x / norm for x in vec]
