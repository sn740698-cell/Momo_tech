"""
ChromaDB Vector Memory Service for MOMO.
Indexes multi-turn chat interactions and explicit user-saved memories for semantic recall.
Provides robust in-memory vector fallback when ChromaDB is unavailable.
"""
import time
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

from nlp.distilbert_service import DistilBERTEmbeddingService
from nlp.embeddings import cosine_similarity

logger = logging.getLogger(__name__)

DEFAULT_PERSIST_DIR = Path(__file__).resolve().parent.parent / "data" / "chromadb"


class ChromaMemoryService:
    """
    Manages vector storage and semantic retrieval for:
    1. Past chat history (across sessions) -> collection 'momo_chat_history'
    2. Explicitly saved user memories -> collection 'momo_saved_memories'
    """

    CHAT_COLLECTION = "momo_chat_history"
    SAVED_MEMORIES_COLLECTION = "momo_saved_memories"

    def __init__(self, persist_directory: Optional[str] = None):
        self.persist_dir = Path(persist_directory) if persist_directory else DEFAULT_PERSIST_DIR
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        self.embedding_service = DistilBERTEmbeddingService()

        self.chroma_client = None
        self.chat_collection = None
        self.saved_collection = None

        self._in_memory_chats: Dict[str, Dict[str, Any]] = {}
        self._in_memory_saved: Dict[str, Dict[str, Any]] = {}
        self._initialized = False

    def _init_chroma(self):
        if self._initialized:
            return
        self._initialized = True

        try:
            import chromadb
            from chromadb.config import Settings
            logger.info(f"Connecting ChromaMemoryService to storage at {self.persist_dir}...")
            self.chroma_client = chromadb.PersistentClient(
                path=str(self.persist_dir),
                settings=Settings(anonymized_telemetry=False)
            )
            self.chat_collection = self.chroma_client.get_or_create_collection(
                name=self.CHAT_COLLECTION,
                metadata={"hnsw:space": "cosine"}
            )
            self.saved_collection = self.chroma_client.get_or_create_collection(
                name=self.SAVED_MEMORIES_COLLECTION,
                metadata={"hnsw:space": "cosine"}
            )
            logger.info("ChromaDB memory collections ('momo_chat_history', 'momo_saved_memories') ready.")
        except Exception as e:
            logger.warning(f"ChromaDB memory initialization failed: {e}. Falling back to in-memory vector storage.")
            self.chroma_client = None
            self.chat_collection = None
            self.saved_collection = None

    # --- Chat History Vector Storage ---

    def index_chat_interaction(
        self,
        user_text: str,
        assistant_text: str,
        session_id: str = "default",
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Embeds and indexes a completed Q&A turn into ChromaDB for semantic recall.
        """
        if not user_text or not assistant_text:
            return False

        self._init_chroma()
        doc_text = f"User asked: {user_text.strip()}\nMOMO answered: {assistant_text.strip()}"
        embedding = self.embedding_service.embed_text(doc_text)
        interaction_id = f"chat_{session_id}_{int(time.time() * 1000)}"

        meta = {
            "session_id": session_id,
            "timestamp": time.time(),
            "user_query": user_text[:200],
            "assistant_preview": assistant_text[:200],
        }
        if metadata:
            meta.update(metadata)

        if self.chat_collection is not None:
            try:
                self.chat_collection.upsert(
                    ids=[interaction_id],
                    embeddings=[embedding],
                    documents=[doc_text],
                    metadatas=[meta]
                )
                logger.debug(f"Indexed chat interaction {interaction_id} into ChromaDB.")
                return True
            except Exception as e:
                logger.warning(f"ChromaDB upsert failed for chat turn: {e}")

        # In-memory fallback
        self._in_memory_chats[interaction_id] = {
            "id": interaction_id,
            "document": doc_text,
            "embedding": embedding,
            "metadata": meta,
        }
        return True

    def search_past_chats(
        self,
        query_text: str,
        top_k: int = 3,
        similarity_threshold: float = 0.30
    ) -> List[Dict[str, Any]]:
        """
        Searches past chat interactions across sessions that match the query topic.
        """
        if not query_text.strip():
            return []

        self._init_chroma()
        query_embedding = self.embedding_service.embed_text(query_text)
        results = []

        if self.chat_collection is not None:
            try:
                res = self.chat_collection.query(
                    query_embeddings=[query_embedding],
                    n_results=top_k * 2
                )
                docs = res.get("documents", [[]])[0]
                metas = res.get("metadatas", [[]])[0]
                distances = res.get("distances", [[]])[0] if "distances" in res else []

                for i, doc in enumerate(docs):
                    dist = distances[i] if i < len(distances) else 0.5
                    score = max(0.0, min(1.0, 1.0 - dist))
                    if score >= similarity_threshold:
                        results.append({
                            "document": doc,
                            "score": round(score, 3),
                            "metadata": metas[i] if i < len(metas) else {}
                        })
                results.sort(key=lambda x: x["score"], reverse=True)
                return results[:top_k]
            except Exception as e:
                logger.warning(f"ChromaDB chat query error: {e}")

        # In-memory fallback
        for cid, item in self._in_memory_chats.items():
            sim = cosine_similarity(query_embedding, item["embedding"])
            if sim >= similarity_threshold:
                results.append({
                    "document": item["document"],
                    "score": round(sim, 3),
                    "metadata": item["metadata"]
                })
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]

    # --- Explicit User-Saved Memories Vector Storage ---

    def index_saved_memory(
        self,
        memory_text: str,
        fact_id: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Embeds and indexes an explicitly saved memory into ChromaDB.
        """
        if not memory_text.strip():
            return False

        self._init_chroma()
        clean_text = memory_text.strip()
        embedding = self.embedding_service.embed_text(clean_text)
        memory_id = f"fact_{fact_id}" if fact_id else f"fact_mem_{int(time.time() * 1000)}"

        meta = {
            "fact_id": fact_id or 0,
            "timestamp": time.time(),
            "content": clean_text[:300]
        }
        if metadata:
            meta.update(metadata)

        if self.saved_collection is not None:
            try:
                self.saved_collection.upsert(
                    ids=[memory_id],
                    embeddings=[embedding],
                    documents=[clean_text],
                    metadatas=[meta]
                )
                logger.info(f"Indexed user-saved memory {memory_id} into ChromaDB.")
                return True
            except Exception as e:
                logger.warning(f"ChromaDB upsert failed for saved memory: {e}")

        # In-memory fallback
        self._in_memory_saved[memory_id] = {
            "id": memory_id,
            "document": clean_text,
            "embedding": embedding,
            "metadata": meta,
        }
        return True

    def search_saved_memories(
        self,
        query_text: str,
        top_k: int = 5,
        similarity_threshold: float = 0.30
    ) -> List[Dict[str, Any]]:
        """
        Semantically queries explicit user-saved memories.
        """
        if not query_text.strip():
            return []

        self._init_chroma()
        query_embedding = self.embedding_service.embed_text(query_text)
        results = []

        if self.saved_collection is not None:
            try:
                res = self.saved_collection.query(
                    query_embeddings=[query_embedding],
                    n_results=top_k * 2
                )
                docs = res.get("documents", [[]])[0]
                metas = res.get("metadatas", [[]])[0]
                distances = res.get("distances", [[]])[0] if "distances" in res else []

                for i, doc in enumerate(docs):
                    dist = distances[i] if i < len(distances) else 0.5
                    score = max(0.0, min(1.0, 1.0 - dist))
                    if score >= similarity_threshold:
                        results.append({
                            "content": doc,
                            "score": round(score, 3),
                            "metadata": metas[i] if i < len(metas) else {}
                        })
                results.sort(key=lambda x: x["score"], reverse=True)
                return results[:top_k]
            except Exception as e:
                logger.warning(f"ChromaDB memory query error: {e}")

        # In-memory fallback
        for mid, item in self._in_memory_saved.items():
            sim = cosine_similarity(query_embedding, item["embedding"])
            if sim >= similarity_threshold:
                results.append({
                    "content": item["document"],
                    "score": round(sim, 3),
                    "metadata": item["metadata"]
                })
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]
