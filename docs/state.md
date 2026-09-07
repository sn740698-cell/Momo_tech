# 📊 MOMO Shared Pydantic State Schema & Reducers

MOMO utilizes a centralized, immutable Pydantic state model (`MomoState`) to coordinate concurrent multi-agent branches within LangGraph.
Nodes communicate exclusively through typed state updates. Arbitrary dictionaries are forbidden.

---

## 1. Schema Definitions (`graph/state.py`)

### `Message`
Represents chronological turns in dialogue:
```python
class Message(BaseModel):
    id: Optional[str] = None
    role: str  # 'user', 'assistant', 'system'
    content: str
    expression: str = "normal"
    animation: str = "none"
    thinking: Optional[str] = None
    timestamp: float = Field(default_factory=time.time)
    metadata: Dict[str, Any] = Field(default_factory=dict)
```

### `FinancialInsight`
Deterministic financial record extracted from invoices and validated mathematically:
```python
class FinancialInsight(BaseModel):
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
```

### `ProcessedDocument`
Structured document representation after parsing and chunking:
```python
class ProcessedDocument(BaseModel):
    document_id: str
    filename: str
    document_type: str = "invoice"
    text: str = ""
    chunks: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    embedding_reference: Optional[str] = None
    processing_status: str = "pending"
```

### `HardwareCommand`
Sanitized command frame for ESP32 actuation:
```python
class HardwareCommand(BaseModel):
    type: str = "device_command"
    device_id: str = "momo-01"
    expression: str = "normal"
    animation: str = "none"
    led: str = "solid"
    servo: Dict[str, Any] = Field(default_factory=lambda: {"pan": 90, "tilt": 90, "action": "hold"})
    oled_display: Optional[str] = None
    speak: bool = False
    timestamp: float = Field(default_factory=time.time)
```

---

## 2. Root State Schema (`MomoState`)

```python
class MomoState(BaseModel):
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
```

---

## 3. Merging Reducers (`graph/reducers.py`)

- `merge_messages`: Merges messages chronologically and deduplicates by `id` / `timestamp`.
- `merge_documents`: Combines document models indexed by `document_id`.
- `merge_financial_insights`: Keyed by `invoice_number`, ensuring verified balance updates overwrite older approximations.
- `merge_retrieved_context`: Aggregates top-k semantic chunks from ChromaDB, deduplicating by `chunk_id`.
- `merge_routing_decisions`: Preserves the complete supervisor traversal trail.
