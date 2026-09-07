from typing import Annotated, List, Optional, Dict, Any
from pydantic import BaseModel, Field
import time

from .reducers import (
    merge_messages,
    merge_documents,
    merge_financial_insights,
    merge_retrieved_context,
    merge_routing_decisions,
    merge_errors,
)


class Message(BaseModel):
    """
    Standard message model representing turns in conversation.
    """
    id: Optional[str] = None
    role: str = Field(description="Role: 'user', 'assistant', 'system'")
    content: str = Field(default="", description="Text content of the message")
    expression: str = Field(default="normal", description="Avatar facial expression")
    animation: str = Field(default="none", description="Servo / avatar animation")
    thinking: Optional[str] = Field(default=None, description="Model internal chain-of-thought")
    timestamp: float = Field(default_factory=time.time)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ProcessedDocument(BaseModel):
    """
    Structured representation of an ingested document.
    """
    document_id: str
    filename: str
    document_type: str = "invoice"  # e.g., 'invoice', 'receipt', 'contract', 'text'
    text: str = ""
    chunks: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    embedding_reference: Optional[str] = None
    processing_status: str = "pending"  # 'pending', 'processing', 'completed', 'failed'


class FinancialInsight(BaseModel):
    """
    Deterministic extracted financial data model.
    Never fabricated by LLM; validated by python calculator.
    """
    invoice_number: str
    invoice_total: float = 0.0
    amount_paid: float = 0.0
    balance_due: float = 0.0
    currency: str = "INR"
    due_date: Optional[str] = None
    payment_status: str = "unpaid"  # 'paid', 'partially_paid', 'unpaid', 'overdue'
    confidence: float = 1.0
    line_items: List[Dict[str, Any]] = Field(default_factory=list)
    notes: Optional[str] = None


class RetrievedChunk(BaseModel):
    """
    A chunk retrieved via semantic similarity search.
    """
    chunk_id: str
    document_id: str
    content: str
    score: float = 0.0
    page: Optional[int] = 1
    metadata: Dict[str, Any] = Field(default_factory=dict)


class RoutingDecision(BaseModel):
    """
    Record of routing performed by supervisors.
    """
    supervisor: str
    target_agent: str
    reason: str = ""
    confidence: float = 1.0
    timestamp: float = Field(default_factory=time.time)


class HardwareCommand(BaseModel):
    """
    Validated hardware actuation command for ESP32.
    Only predefined allowlisted values are permissible.
    """
    type: str = "device_command"
    device_id: str = "momo-01"
    expression: str = "normal"
    animation: str = "none"
    led: str = "solid"
    servo: Dict[str, Any] = Field(default_factory=lambda: {"pan": 90, "tilt": 90, "action": "hold"})
    oled_display: Optional[str] = None
    speak: bool = False
    timestamp: float = Field(default_factory=time.time)


class MomoResponse(BaseModel):
    """
    Standard output schema for MOMO responses.
    """
    message: str = ""
    expression: str = "normal"
    animation: str = "none"
    speak: bool = True
    priority: str = "normal"
    ascii: str = "◕ᴗ◕"
    thinking: Optional[str] = None
    model: Optional[str] = None
    timestamp: float = Field(default_factory=time.time)


class VoiceRequest(BaseModel):
    """
    Inbound voice transcription request payload.
    """
    audio_bytes: Optional[bytes] = None
    format: str = "wav"
    sample_rate: int = 16000
    session_id: str = "default"


class VisionState(BaseModel):
    """
    Live computer vision perception state.
    Strictly observes privacy permissions.
    """
    camera_available: bool = False
    privacy_shutter_closed: bool = True
    person_present: bool = False
    face_detected: bool = False
    head_orientation: str = "center"  # 'center', 'left', 'right', 'down'
    attention_state: str = "screen"   # 'screen', 'away', 'idle'
    confidence: float = 0.0


class UserContext(BaseModel):
    """
    Deterministic user session and activity metrics.
    """
    active_app: Optional[str] = None
    idle_seconds: int = 0
    session_duration_minutes: int = 0
    interaction_count: int = 0
    current_activity: str = "active"


class DeviceState(BaseModel):
    """
    Status of the physical ESP32 companion.
    """
    device_id: str = "momo-01"
    online: bool = False
    last_seen: float = 0.0
    battery_pct: Optional[int] = None
    rssi: Optional[int] = None
    status: str = "disconnected"


class MomoState(BaseModel):
    """
    Root shared Pydantic state for the LangGraph multi-supervisor workflow.
    Uses Annotated reducers to allow clean concurrent branch contributions.
    """
    messages: Annotated[List[Message], merge_messages] = Field(default_factory=list)
    documents: Annotated[List[ProcessedDocument], merge_documents] = Field(default_factory=list)
    financial_insights: Annotated[List[FinancialInsight], merge_financial_insights] = Field(default_factory=list)
    retrieved_context: Annotated[List[RetrievedChunk], merge_retrieved_context] = Field(default_factory=list)
    supervisor_decisions: Annotated[List[RoutingDecision], merge_routing_decisions] = Field(default_factory=list)
    errors: Annotated[List[str], merge_errors] = Field(default_factory=list)

    conversation_context: Optional[str] = None
    current_route: Optional[str] = None
    current_agent: Optional[str] = None
    draft_text: Optional[str] = None
    user_intent: Optional[str] = None

    momo_expression: str = "normal"
    momo_animation: str = "none"
    hardware_command: Optional[HardwareCommand] = None
    voice_input: Optional[str] = None
    response: Optional[MomoResponse] = None

    user_context: Optional[UserContext] = None
    vision_state: Optional[VisionState] = None
    device_state: Optional[DeviceState] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
