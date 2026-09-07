from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
import time


class MomoEvent(BaseModel):
    event_type: str  # e.g., 'USER_RETURNED', 'LONG_SESSION', 'LONG_IDLE', 'BUILD_SUCCESS', etc.
    source: str = "system"  # 'system', 'hardware', 'desktop', 'user'
    payload: Dict[str, Any] = Field(default_factory=dict)
    timestamp: float = Field(default_factory=time.time)
