"""
ChromaDB Vector Retrieval Service.
Handles local collection creation, chunk upserts, metadata management,
and similarity queries with DistilBERT embeddings.
"""
import os
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path

from nlp.distilbert_service import DistilBERTEmbeddingService
from nlp.embeddings import cosine_similarity
from .filters import filter_by_similarity_threshold, rank_and_deduplicate

logger = logging.getLogger(__name__)

DEFAULT_PERSIST_DIR = Path(__file__).resolve().parent.parent / "data" / "chromadb"


class ChromaRetrievalService:
    """
    Manages vector storage and retrieval using ChromaDB with an in-memory fallback.
    """

    def __init__(self, persist_directory: Optional[str] = None):
        self.persist_dir = Path(persist_directory) if persist_directory else DEFAULT_PERSIST_DIR
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        self.embedding_service = DistilBERTEmbeddingService()
        self.collection_name = "momo_documents"
        self.chroma_client = None
        self.collection = None
        self._in_memory_docs: Dict[str, Dict[str, Any]] = {}
        self._initialized = False

    def _init_chroma(self):
        if self._initialized:
            return
        self._initialized = True

        try:
            import chromadb
            from chromadb.config import Settings
            logger.info(f"Connecting to ChromaDB persistent storage at {self.persist_dir}...")
            self.chroma_client = chromadb.PersistentClient(
                path=str(self.persist_dir),
                settings=Settings(anonymized_telemetry=False)
            )
            self.collection = self.chroma_client.get_or_create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"}
            )
            logger.info(f"ChromaDB collection '{self.collection_name}' ready.")
        except Exception as e:
            logger.warning(f"ChromaDB initialization failed ({e}). Operating in memory vector store mode.")
            self.chroma_client = None
            self.collection = None

    def add_chunks(
        self,
        document_id: str,
        chunks: List[str],
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Embeds and indexes document chunks.
        """
        if not chunks:
            return False

        self._init_chroma()
        embeddings = self.embedding_service.embed_batch(chunks)
        ids = [f"{document_id}_chunk_{i}" for i in range(len(chunks))]
        metadatas = []
        base_meta = metadata or {}

        for i in range(len(chunks)):
            m = dict(base_meta)
            m.update({
                "document_id": document_id,
                "chunk_id": ids[i],
                "chunk_index": i
            })
            metadatas.append(m)

        if self.collection is not None:
            try:
                self.collection.upsert(
                    ids=ids,
                    embeddings=embeddings,
                    documents=chunks,
                    metadatas=metadatas
                )
                logger.info(f"Indexed {len(chunks)} chunks for doc {document_id} into ChromaDB.")
                return True
            except Exception as e:
                logger.error(f"Failed to upsert to ChromaDB: {e}")

        # Store in memory fallback
        for i, cid in enumerate(ids):
            self._in_memory_docs[cid] = {
                "chunk_id": cid,
                "document_id": document_id,
                "content": chunks[i],
                "embedding": embeddings[i],
                "metadata": metadatas[i]
            }
        logger.info(f"Stored {len(chunks)} chunks in memory vector store fallback.")
        return True

    def query(
        self,
        query_text: str,
        top_k: int = 4,
        similarity_threshold: float = 0.60,
        filter_document_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Performs semantic retrieval against stored chunks.
        """
        self._init_chroma()
        query_embedding = self.embedding_service.embed_text(query_text)

        if self.collection is not None:
            try:
                where_clause = {"document_id": filter_document_id} if filter_document_id else None
                res = self.collection.query(
                    query_embeddings=[query_embedding],
                    n_results=top_k * 2,
                    where=where_clause
                )
                results = []
                docs = res.get("documents", [[]])[0]
                metas = res.get("metadatas", [[]])[0]
                distances = res.get("distances", [[]])[0] if "distances" in res else []

                for i, doc_text in enumerate(docs):
                    # Chroma cosine distance = 1 - cosine_similarity
                    dist = distances[i] if i < len(distances) else 0.5
                    score = max(0.0, min(1.0, 1.0 - dist))
                    m = metas[i] if i < len(metas) else {}
                    results.append({
                        "chunk_id": m.get("chunk_id", f"c_{i}"),
                        "document_id": m.get("document_id", "unknown"),
                        "content": doc_text,
                        "score": round(score, 3),
                        "page": m.get("page", 1),
                        "metadata": m
                    })

                filtered = filter_by_similarity_threshold(results, similarity_threshold)
                return rank_and_deduplicate(filtered, top_k)
            except Exception as e:
                logger.error(f"ChromaDB query error: {e}")

        # In-memory cosine similarity fallback
        results = []
        for cid, item in self._in_memory_docs.items():
            if filter_document_id and item.get("document_id") != filter_document_id:
                continue
            sim = cosine_similarity(query_embedding, item["embedding"])
            results.append({
                "chunk_id": cid,
                "document_id": item["document_id"],
                "content": item["content"],
                "score": round(sim, 3),
                "page": item["metadata"].get("page", 1),
                "metadata": item["metadata"]
            })

        filtered = filter_by_similarity_threshold(results, similarity_threshold)
        return rank_and_deduplicate(filtered, top_k)
