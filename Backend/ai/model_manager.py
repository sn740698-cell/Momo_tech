from typing import List, Optional
from .ollama_client import OllamaClient


class ModelManager:
    """
    Manages discovery and selection of local Ollama models.
    Exclusively restricts to Llama models for fast, high-quality responses on RTX 2050 laptop GPU.
    All non-Llama models are strictly excluded.
    """

    DEFAULT_PRIMARY_MODEL = "hf.co/hugging-quants/Llama-3.2-1B-Instruct-Q8_0-GGUF:Q8_0"

    RECOMMENDED_MODELS = [
        "hf.co/hugging-quants/Llama-3.2-1B-Instruct-Q8_0-GGUF:Q8_0",
    ]

    def __init__(self, ollama_client: Optional[OllamaClient] = None):
        self.client = ollama_client or OllamaClient()

    def get_installed_models(self) -> List[str]:
        health = self.client.check_health()
        all_models = health.get("model_names", [])
        # Strictly filter to Llama models only, removing any other model families
        llama_models = [m for m in all_models if "llama" in m.lower()]
        return llama_models if llama_models else [self.DEFAULT_PRIMARY_MODEL]

    def is_model_installed(self, model_name: str) -> bool:
        if not model_name or "llama" not in model_name.lower():
            return False
        installed = self.get_installed_models()
        return model_name in installed or any(inst.startswith(model_name) for inst in installed)

    def get_best_available_model(self) -> str:
        installed = self.get_installed_models()
        for inst in installed:
            if "llama" in inst.lower():
                return inst
        return self.DEFAULT_PRIMARY_MODEL
