import os
import json
import logging
from typing import Dict, Any, List, Optional
import requests
from asgiref.sync import sync_to_async

logger = logging.getLogger(__name__)

DEFAULT_OLLAMA_HOST = "http://127.0.0.1:11434"


class OllamaClient:
    """
    Resilient client for communicating with the local Ollama LLM runtime.
    """

    def __init__(self, host: str = DEFAULT_OLLAMA_HOST):
        self.host = host.rstrip("/")

    def check_health(self) -> Dict[str, Any]:
        """
        Synchronously checks if Ollama service is reachable and retrieves version & models.
        """
        try:
            resp = requests.get(f"{self.host}/api/tags", timeout=2)
            if resp.status_code == 200:
                data = resp.json()
                raw_models = data.get("models", [])
                names = [m.get("name") for m in raw_models]
                version = "unknown"
                try:
                    v_resp = requests.get(f"{self.host}/api/version", timeout=1)
                    if v_resp.status_code == 200:
                        version = v_resp.json().get("version", "unknown")
                except Exception:
                    pass

                return {
                    "online": True,
                    "host": self.host,
                    "version": version,
                    "models": raw_models,
                    "model_names": names,
                }
            return {
                "online": False,
                "host": self.host,
                "error": f"Ollama HTTP {resp.status_code}",
                "models": [],
                "model_names": [],
            }
        except requests.exceptions.RequestException as e:
            return {
                "online": False,
                "host": self.host,
                "error": str(e),
                "models": [],
                "model_names": [],
            }

    async def check_health_async(self) -> Dict[str, Any]:
        return await sync_to_async(self.check_health)()

    def chat_sync(
        self,
        messages: List[Dict[str, str]],
        model: str = "hf.co/hugging-quants/Llama-3.2-1B-Instruct-Q8_0-GGUF:Q8_0",
        temperature: float = 0.35,
        system_prompt: Optional[str] = None,
        timeout_seconds: Optional[int] = None,
        format: Optional[str] = "json",
        num_predict: int = 640
    ) -> Dict[str, Any]:
        """
        Sends synchronous chat completion request to Ollama.
        Keeps model in VRAM for 60m to guarantee fast subsequent responses (sub-second).
        Uses format='json' for constrained grammar decoding when JSON output is required.
        """
        timeout = timeout_seconds or int(os.getenv("OLLAMA_TIMEOUT", "90"))
        formatted_messages = []
        has_system = any(m.get("role") == "system" for m in messages)
        if not has_system and system_prompt:
            formatted_messages.append({"role": "system", "content": system_prompt})
        formatted_messages.extend(messages)

        payload = {
            "model": model,
            "messages": formatted_messages,
            "stream": False,
            "keep_alive": "60m",
            "options": {
                "temperature": float(temperature),
                "num_ctx": 2048,
                "num_predict": num_predict,
                "top_k": 40,
                "top_p": 0.9,
            }
        }
        if format:
            payload["format"] = format

        try:
            response = requests.post(
                f"{self.host}/api/chat",
                json=payload,
                timeout=timeout
            )
            if response.status_code == 200:
                data = response.json()
                msg_obj = data.get("message", {})
                return {
                    "success": True,
                    "content": msg_obj.get("content", ""),
                    "thinking": msg_obj.get("thinking", ""),
                    "model": model,
                    "total_duration": data.get("total_duration"),
                }
            elif response.status_code == 404:
                return {
                    "success": False,
                    "error": f"Model '{model}' not found in Ollama library.",
                    "status_code": 404
                }
            else:
                return {
                    "success": False,
                    "error": f"Ollama error HTTP {response.status_code}: {response.text}",
                    "status_code": response.status_code
                }
        except requests.exceptions.RequestException as e:
            return {
                "success": False,
                "error": f"Could not connect to Ollama at {self.host}: {str(e)}",
                "status_code": 503
            }

    async def chat(
        self,
        messages: List[Dict[str, str]],
        model: str = "hf.co/hugging-quants/Llama-3.2-1B-Instruct-Q8_0-GGUF:Q8_0",
        temperature: float = 0.35,
        system_prompt: Optional[str] = None,
        timeout_seconds: Optional[int] = None,
        format: Optional[str] = "json",
        num_predict: int = 640
    ) -> Dict[str, Any]:
        return await sync_to_async(self.chat_sync)(
            messages=messages,
            model=model,
            temperature=temperature,
            system_prompt=system_prompt,
            timeout_seconds=timeout_seconds,
            format=format,
            num_predict=num_predict
        )

