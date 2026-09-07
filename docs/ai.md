# 🧠 MOMO Local AI & GPU Optimization Guide

## 1. Local LLM Architecture (Ollama)

MOMO interfaces with local LLMs via `OllamaClient` (`ai/ollama_client.py`).
- **Default Model**: `qwen3:4b` (or any installed model like `llama3`, `mistral`, `deepseek-r1`).
- **Resilience**: If Ollama is offline, the client falls back to graceful offline responses without crashing.
- **Structured Outputs**: Outputs are parsed via `ai/response_parser.py` into strict `MomoResponse` models.

---

## 2. BERT & DistilBERT Separation of Concerns

- **Hugging Face BERT (`nlp/bert_service.py`)**: Used exclusively for sentence-level contextual semantic analysis. Segments invoice sentences and classifies statements (e.g. Total Due clauses, Payment Received clauses). Never used as a generative model.
- **DistilBERT (`nlp/distilbert_service.py`)**: Used for generating 384-dimensional dense vector embeddings for ChromaDB chunks and user search queries.

---

## 3. RTX 2050 Laptop GPU (4GB VRAM) Optimization

1. **PyTorch Inference Mode**: All inference runs inside `torch.inference_mode()` with gradients disabled.
2. **CUDA Cache Management**: `GPUManager.clear_cache()` invokes `torch.cuda.empty_cache()` and garbage collection.
3. **Explicit CUDA OOM Recovery**: If a CUDA Out-Of-Memory exception occurs during inference:
   - Exception is caught safely.
   - Cache is flushed.
   - The operation gracefully falls back to CPU execution without crashing the server.
