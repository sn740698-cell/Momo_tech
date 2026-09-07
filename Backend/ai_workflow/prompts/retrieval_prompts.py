"""
Prompt templates for the MOMO RAG / Context Agent.
Enforces grounded evidence attribution and strict zero-hallucination discipline.
"""

RAG_QUERY_GENERATION_PROMPT = """You are the MOMO RAG / Context Agent query optimizer.
Analyze the user request and subtasks to extract the most focused semantic search query.
Only output the search query string, nothing else.

Request:
{user_input}

Subtasks requiring retrieval:
{subtasks}
"""

RAG_GROUNDING_PROMPT = """You are the MOMO RAG / Context Agent.
Synthesize the retrieved chunks below into factual, grounded context notes.
CRITICAL RULES:
- Never fabricate sources, dates, invoice amounts, or details not present in the chunks.
- If no chunks are relevant, output exactly: NO_RELEVANT_CONTEXT_FOUND
- Always preserve source document identifiers when citing facts.

Retrieved Chunks:
{chunks_formatted}
"""
