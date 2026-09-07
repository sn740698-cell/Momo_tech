"""
GPU & Model Memory Manager for MOMO.
Optimized for NVIDIA RTX 2050 laptop GPU (4GB VRAM) with automatic CPU fallback.
"""
import os
import gc
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class GPUManager:
    """
    Manages VRAM allocations, CUDA cache reclamation, and OOM recovery.
    """

    _torch = None
    _torch_checked = False

    @classmethod
    def _get_torch(cls):
        if not cls._torch_checked:
            cls._torch_checked = True
            try:
                import torch
                cls._torch = torch
            except ImportError:
                cls._torch = None
        return cls._torch

    @classmethod
    def is_cuda_available(cls) -> bool:
        torch = cls._get_torch()
        if torch is not None:
            return torch.cuda.is_available()
        return False

    @classmethod
    def get_preferred_device(cls) -> str:
        env_dev = os.getenv("DEVICE", "").lower()
        if env_dev in ("cuda", "gpu") and cls.is_cuda_available():
            return "cuda"
        if env_dev == "cpu":
            return "cpu"
        return "cuda" if cls.is_cuda_available() else "cpu"

    @classmethod
    def get_vram_telemetry(cls) -> Dict[str, Any]:
        torch = cls._get_torch()
        if torch is None or not torch.cuda.is_available():
            return {
                "cuda_available": False,
                "device_name": "CPU",
                "allocated_mb": 0,
                "reserved_mb": 0,
                "total_mb": 0,
            }

        try:
            device_id = torch.cuda.current_device()
            props = torch.cuda.get_device_properties(device_id)
            allocated = torch.cuda.memory_allocated(device_id) / (1024 * 1024)
            reserved = torch.cuda.memory_reserved(device_id) / (1024 * 1024)
            total = props.total_memory / (1024 * 1024)
            return {
                "cuda_available": True,
                "device_name": props.name,
                "allocated_mb": round(allocated, 1),
                "reserved_mb": round(reserved, 1),
                "total_mb": round(total, 1),
                "free_mb": round(total - reserved, 1),
            }
        except Exception as e:
            logger.warning(f"Failed to read CUDA memory telemetry: {e}")
            return {"cuda_available": True, "error": str(e)}

    @classmethod
    def clear_cache(cls):
        """
        Reclaims unreferenced memory and clears the CUDA memory allocator cache.
        """
        gc.collect()
        torch = cls._get_torch()
        if torch is not None and torch.cuda.is_available():
            try:
                torch.cuda.empty_cache()
                logger.info("CUDA memory cache cleared successfully.")
            except Exception as e:
                logger.warning(f"Error clearing CUDA cache: {e}")

    @classmethod
    def handle_cuda_oom(cls, operation_name: str = "inference"):
        """
        Explicit CUDA Out-Of-Memory exception handler.
        Logs details, releases memory buffers, and warns the pipeline to fallback.
        """
        logger.error(
            f"CUDA Out-Of-Memory (OOM) encountered during {operation_name}! "
            f"Executing emergency cache flush and falling back to CPU."
        )
        cls.clear_cache()
