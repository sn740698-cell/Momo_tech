export type MomoExpression =
  | 'normal'
  | 'happy'
  | 'thinking'
  | 'confused'
  | 'sleepy'
  | 'excited'
  | 'sad'
  | 'angry'
  | 'surprised'
  | 'proud'
  | 'embarrassed'
  | 'playful'
  | 'tired'
  | 'stressed';

export interface VisionTelemetry {
  camera_available: boolean;
  privacy_blocked: boolean;
  face_detected: boolean;
  face_count: number;
  emotion: string;
  emotion_confidence: number;
  looking_at_camera: boolean;
  head_pose: string;
  work_duration_minutes: number;
  sad_tired_minutes?: number;
  is_sad_and_tired?: boolean;
  fatigue_detected: boolean;
  proactive_event?: {
    trigger: string;
    message: string;
    suggested_expression: string;
    suggested_animation: string;
    work_minutes: number;
    sad_tired_minutes?: number;
  } | null;
  sensors?: Record<string, number>;
  expression_summary?: string;
  recognized_user?: string;
  recognition_confidence?: number;
  recognition?: {
    recognized: boolean;
    user_name: string;
    confidence: number;
    status: string;
  };
  enhancement?: {
    clarity_boosted: boolean;
    upscaled: boolean;
    laplacian_var: number;
  };
  clarity_score?: number;
  enhancement_active?: boolean;
  timestamp?: number;
}

export type MomoAnimation =
  | 'none'
  | 'nod'
  | 'tilt_left'
  | 'tilt_right'
  | 'blink'
  | 'celebrate'
  | 'wave'
  | 'shake'
  | 'sleep';

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  expression?: MomoExpression;
  animation?: MomoAnimation;
  thinking?: string;
  model?: string;
  timestamp: string;
}

export interface FinancialInsight {
  invoice_number: string;
  invoice_total: number;
  amount_paid: number;
  balance_due: number;
  currency: string;
  due_date?: string | null;
  payment_status: 'paid' | 'partially_paid' | 'unpaid' | 'overdue';
  confidence: number;
  line_items?: Array<{ description: string; amount: number }>;
  notes?: string | null;
}

export interface ProcessedDocument {
  document_id: string;
  filename: string;
  document_type: string;
  text: string;
  chunks: string[];
  metadata: Record<string, any>;
  embedding_reference?: string;
  processing_status: 'pending' | 'processing' | 'completed' | 'failed';
}

export interface DeviceTelemetry {
  device_id: string;
  status: 'online' | 'disconnected';
  connection_type?: 'websocket' | 'usb_serial';
  port?: string;
  battery_pct?: number;
  rssi?: number;
  last_seen?: number;
}

export interface SystemStatus {
  backend: boolean;
  langgraph: boolean;
  ollama: boolean;
  llm_model: boolean;
  bert: boolean;
  distilbert: boolean;
  chromadb: boolean;
  camera: boolean;
  microphone: boolean;
  tts: boolean;
  esp32: boolean;
  gpu: boolean;
  gpu_telemetry?: {
    cuda_available: boolean;
    device_name?: string;
    allocated_mb?: number;
    reserved_mb?: number;
    total_mb?: number;
  };
  timestamp?: string;
}

export interface PrivacySettings {
  camera_enabled: boolean;
  microphone_enabled: boolean;
  memory_enabled: boolean;
  activity_tracking_enabled: boolean;
}
