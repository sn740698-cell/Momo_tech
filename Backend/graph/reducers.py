from typing import List, Union, Any, Dict


def merge_messages(existing: List[Any], new: Union[List[Any], Any]) -> List[Any]:
    """
    Chronologically merges chat messages without duplicates.
    """
    if existing is None:
        existing = []
    if new is None:
        return existing
    
    if not isinstance(new, list):
        new = [new]
    
    result = list(existing)
    existing_ids = {getattr(m, "id", None) or getattr(m, "timestamp", None) for m in result if getattr(m, "id", None) or getattr(m, "timestamp", None)}
    
    for item in new:
        item_id = getattr(item, "id", None) or getattr(item, "timestamp", None)
        if item_id and item_id in existing_ids:
            # Replace existing matching item
            for idx, ex in enumerate(result):
                ex_id = getattr(ex, "id", None) or getattr(ex, "timestamp", None)
                if ex_id == item_id:
                    result[idx] = item
                    break
        else:
            result.append(item)
            if item_id:
                existing_ids.add(item_id)
                
    return result


def merge_documents(existing: List[Any], new: Union[List[Any], Any]) -> List[Any]:
    """
    Merges processed documents by document_id.
    """
    if existing is None:
        existing = []
    if new is None:
        return existing
    
    if not isinstance(new, list):
        new = [new]
        
    doc_map = {getattr(d, "document_id", str(i)): d for i, d in enumerate(existing)}
    for d in new:
        doc_id = getattr(d, "document_id", None)
        if doc_id:
            doc_map[doc_id] = d
        else:
            doc_map[str(len(doc_map))] = d
            
    return list(doc_map.values())


def merge_financial_insights(existing: List[Any], new: Union[List[Any], Any]) -> List[Any]:
    """
    Merges financial insights by invoice_number.
    """
    if existing is None:
        existing = []
    if new is None:
        return existing
    
    if not isinstance(new, list):
        new = [new]
        
    insight_map = {getattr(f, "invoice_number", str(i)): f for i, f in enumerate(existing)}
    for f in new:
        inv_num = getattr(f, "invoice_number", None)
        if inv_num:
            insight_map[inv_num] = f
        else:
            insight_map[str(len(insight_map))] = f
            
    return list(insight_map.values())


def merge_retrieved_context(existing: List[Any], new: Union[List[Any], Any]) -> List[Any]:
    """
    Merges retrieved context chunks, deduplicating by chunk_id.
    """
    if existing is None:
        existing = []
    if new is None:
        return existing
    
    if not isinstance(new, list):
        new = [new]
        
    chunk_map = {getattr(c, "chunk_id", str(i)): c for i, c in enumerate(existing)}
    for c in new:
        cid = getattr(c, "chunk_id", None)
        if cid:
            chunk_map[cid] = c
        else:
            chunk_map[str(len(chunk_map))] = c
            
    return list(chunk_map.values())


def merge_routing_decisions(existing: List[Any], new: Union[List[Any], Any]) -> List[Any]:
    """
    Accumulates routing decisions in chronological execution order.
    """
    if existing is None:
        existing = []
    if new is None:
        return existing
    if not isinstance(new, list):
        new = [new]
    return list(existing) + list(new)


def merge_errors(existing: List[str], new: Union[List[str], str]) -> List[str]:
    """
    Accumulates error messages.
    """
    if existing is None:
        existing = []
    if new is None:
        return existing
    if isinstance(new, str):
        new = [new]
    return list(existing) + [e for e in new if e not in existing]
