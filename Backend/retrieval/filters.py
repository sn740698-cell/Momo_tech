"""
Filtering and thresholding utilities for document retrieval.
"""
from typing import List, Dict, Any


def filter_by_similarity_threshold(
    chunks: List[Dict[str, Any]],
    threshold: float = 0.60
) -> List[Dict[str, Any]]:
    """
    Retains only chunks whose similarity score exceeds the threshold.
    """
    return [c for c in chunks if c.get("score", 0.0) >= threshold]


def rank_and_deduplicate(
    chunks: List[Dict[str, Any]],
    top_k: int = 5
) -> List[Dict[str, Any]]:
    """
    Sorts chunks by score descending and deduplicates by chunk_id or content prefix.
    """
    sorted_chunks = sorted(chunks, key=lambda x: x.get("score", 0.0), reverse=True)
    seen_ids = set()
    seen_prefixes = set()
    result = []

    for c in sorted_chunks:
        cid = c.get("chunk_id")
        content = c.get("content", "").strip()
        prefix = content[:50].lower()

        if cid and cid in seen_ids:
            continue
        if prefix and prefix in seen_prefixes:
            continue

        if cid:
            seen_ids.add(cid)
        if prefix:
            seen_prefixes.add(prefix)

        result.append(c)
        if len(result) >= top_k:
            break

    return result
