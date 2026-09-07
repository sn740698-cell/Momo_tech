import os
import json
import time
import asyncio
import logging
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from asgiref.sync import sync_to_async

from graph.state import MomoState, Message, UserContext, MomoResponse
from graph.graph import momo_graph
from iot.protocol import ESP32Protocol
from iot.heartbeat import HeartbeatMonitor
from iot.serial_bridge import get_serial_bridge
from security.permissions import PermissionManager
from memory.repository import MemoryRepository
from memory.memory_manager import MemoryManager

logger = logging.getLogger(__name__)


class MomoConsumer(AsyncJsonWebsocketConsumer):
    """
    Unified WebSocket gateway for MOMO.
    Synchronizes React Desktop, LangGraph Brain Core, and ESP32 Physical Body.
    Endpoint: /ws/momo/
    """

    COMPANION_GROUP = "momo_companion_group"
    DEVICE_GROUP = "momo_device_group"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.memory_repo = MemoryRepository()
        self.memory_manager = MemoryManager()
        self.serial_bridge = get_serial_bridge()

    async def connect(self):
        await self.channel_layer.group_add(self.COMPANION_GROUP, self.channel_name)
        await self.channel_layer.group_add(self.DEVICE_GROUP, self.channel_name)
        await self.accept()

        logger.info(f"WebSocket client connected: {self.channel_name}")
        await self.send_json({
            "type": "connection_established",
            "status": "online",
            "message": "Connected to MOMO Brain Core WebSocket gateway.",
            "timestamp": time.time(),
        })

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.COMPANION_GROUP, self.channel_name)
        await self.channel_layer.group_discard(self.DEVICE_GROUP, self.channel_name)
        logger.info(f"WebSocket client disconnected: {self.channel_name} (code: {close_code})")

    async def receive_json(self, content: dict, **kwargs):
        msg_type = content.get("type", "")

        # 1. Ping / Pong
        if msg_type == "ping":
            await self.send_json({"type": "pong", "timestamp": time.time()})
            return

        # 2. Chat Message -> Route through LangGraph Multi-Supervisor Workflow
        elif msg_type == "chat_message":
            user_text = content.get("message", "").strip()
            session_id = content.get("session_id", "default")
            if not user_text:
                return

            try:
                # Safely record user message in DB without failing if table is locked
                try:
                    await sync_to_async(self.memory_repo.record_message)(
                        role="user",
                        content=user_text,
                        session_id=session_id
                    )
                except Exception as db_err:
                    logger.warning(f"Could not record user turn in DB: {db_err}")

                # Emit thinking indicator to desktop companion
                await self.channel_layer.group_send(
                    self.COMPANION_GROUP,
                    {
                        "type": "broadcast_message",
                        "payload": {
                            "type": "momo_thinking",
                            "is_thinking": True,
                            "timestamp": time.time()
                        }
                    }
                )

                # Load recent conversation turns so LangGraph agents have multi-turn context
                history_turns = []
                try:
                    recent_chat = await sync_to_async(self.memory_repo.get_recent_chat)(session_id=session_id, limit=6)
                    for h in recent_chat:
                        if h.get("content"):
                            history_turns.append(Message(
                                role=h.get("role", "user"),
                                content=h.get("content", ""),
                                expression=h.get("expression", "normal"),
                                animation=h.get("animation", "none")
                            ))
                except Exception as hist_err:
                    logger.warning(f"Could not load conversation history: {hist_err}")

                # Append current user message
                user_msg = Message(role="user", content=user_text)
                history_turns.append(user_msg)

                metadata = dict(content.get("metadata", {}))
                if content.get("model"):
                    metadata["requested_model"] = content.get("model")

                initial_state = MomoState(
                    messages=history_turns,
                    user_context=UserContext(
                        active_app=content.get("active_app", "Desktop"),
                        idle_seconds=content.get("idle_seconds", 0)
                    ),
                    metadata=metadata
                )

                try:
                    # Invoke compiled multi-supervisor LangGraph with 90s timeout (allows model cold-loading)
                    workflow_timeout = float(os.getenv("LANGGRAPH_TIMEOUT", "90.0"))
                    final_state = await asyncio.wait_for(
                        momo_graph.ainvoke(initial_state),
                        timeout=workflow_timeout
                    )
                except asyncio.TimeoutError:
                    logger.error("LangGraph ainvoke timed out after 90s")
                    final_state = initial_state
                    final_state.response = MomoResponse(
                        message="My local AI model took longer than expected to load into memory. I'm warm and ready now — please try asking your question again!",
                        expression="tired",
                        animation="sigh",
                        speak=True,
                        priority="normal",
                        model=content.get("model", "hf.co/hugging-quants/Llama-3.2-1B-Instruct-Q8_0-GGUF:Q8_0")
                    )
                except Exception as e:
                    logger.error(f"LangGraph execution error: {e}", exc_info=True)
                    final_state = initial_state
                    final_state.response = MomoResponse(
                        message="My brain hit a temporary glitch. Please ensure Ollama is running and try again!",
                        expression="confused",
                        animation="shake",
                        speak=True,
                        priority="normal",
                        model=content.get("model", "hf.co/hugging-quants/Llama-3.2-1B-Instruct-Q8_0-GGUF:Q8_0")
                    )

                # Extract response details (handles both dict and MomoState object)
                if isinstance(final_state, dict):
                    resp = final_state.get("response")
                    expr = final_state.get("momo_expression") or "normal"
                    anim = final_state.get("momo_animation") or "none"
                    draft = final_state.get("draft_text")
                else:
                    resp = getattr(final_state, "response", None)
                    expr = getattr(final_state, "momo_expression", "normal")
                    anim = getattr(final_state, "momo_animation", "none")
                    draft = getattr(final_state, "draft_text", None)

                if resp and hasattr(resp, "message"):
                    msg_text = resp.message
                    thinking_text = getattr(resp, "thinking", None)
                    speak = getattr(resp, "speak", True)
                    model_used = getattr(resp, "model", None) or "hf.co/hugging-quants/Llama-3.2-1B-Instruct-Q8_0-GGUF:Q8_0"
                elif isinstance(resp, dict):
                    msg_text = resp.get("message", "I received your message.")
                    thinking_text = resp.get("thinking", None)
                    speak = resp.get("speak", True)
                    model_used = resp.get("model") or "hf.co/hugging-quants/Llama-3.2-1B-Instruct-Q8_0-GGUF:Q8_0"
                else:
                    msg_text = "I received your message."
                    thinking_text = None
                    speak = True
                    model_used = "hf.co/hugging-quants/Llama-3.2-1B-Instruct-Q8_0-GGUF:Q8_0"

                # Safely record assistant turn in DB
                try:
                    await sync_to_async(self.memory_repo.record_message)(
                        role="assistant",
                        content=msg_text,
                        session_id=session_id,
                        expression=expr,
                        animation=anim,
                        thinking=thinking_text or ""
                    )
                except Exception as db_err:
                    logger.warning(f"Could not record assistant turn in DB: {db_err}")

                response_payload = {
                    "type": "momo_response",
                    "message": msg_text,
                    "expression": expr,
                    "animation": anim,
                    "speak": speak,
                    "draft_text": draft,
                    "thinking": thinking_text,
                    "is_thinking": False,
                    "model": model_used,
                    "timestamp": time.time(),
                }

                # Broadcast to desktop React clients
                await self.channel_layer.group_send(
                    self.COMPANION_GROUP,
                    {
                        "type": "broadcast_message",
                        "payload": response_payload
                    }
                )

                # Index completed interaction turn into ChromaDB for future semantic recall
                try:
                    asyncio.create_task(
                        self.memory_manager.record_and_index_interaction(
                            user_text=user_text,
                            assistant_text=msg_text,
                            session_id=session_id
                        )
                    )
                except Exception as index_err:
                    logger.warning(f"Could not vector index conversation turn: {index_err}")

                # Format and send validated hardware command to ESP32 physical companion
                raw_cmd = {
                    "expression": expr,
                    "animation": anim,
                    "device_id": "momo-01",
                    "speak": speak
                }
                valid, hw_cmd, _ = PermissionManager.validate_hardware_command(raw_cmd)
                device_cmd = ESP32Protocol.create_device_command(
                    expression=expr,
                    animation=anim,
                    device_id="momo-01"
                )

                # 1. Send over WebSocket to WiFi-connected ESP32
                await self.channel_layer.group_send(
                    self.DEVICE_GROUP,
                    {
                        "type": "broadcast_message",
                        "payload": device_cmd
                    }
                )

                # 2. Send over USB-C Serial if ESP32 is plugged into USB-C
                if self.serial_bridge and self.serial_bridge.running:
                    self.serial_bridge.send_command(device_cmd)

            except Exception as outer_err:
                logger.error(f"Critical error in chat_message handler: {outer_err}")
                await self.channel_layer.group_send(
                    self.COMPANION_GROUP,
                    {
                        "type": "broadcast_message",
                        "payload": {
                            "type": "momo_response",
                            "message": "I encountered an error connecting to my brain. Please ensure Ollama is running!",
                            "expression": "sad",
                            "animation": "shake",
                            "speak": True,
                            "is_thinking": False,
                            "timestamp": time.time(),
                        }
                    }
                )
            finally:
                # Guarantee thinking state is turned off on all clients
                await self.channel_layer.group_send(
                    self.COMPANION_GROUP,
                    {
                        "type": "broadcast_message",
                        "payload": {
                            "type": "momo_thinking",
                            "is_thinking": False,
                            "timestamp": time.time()
                        }
                    }
                )

        # 3. Direct Manual Hardware Command from UI
        elif msg_type == "device_command":
            valid, hw_cmd, _ = PermissionManager.validate_hardware_command(content)
            if valid:
                cmd = ESP32Protocol.create_device_command(
                    expression=hw_cmd["expression"],
                    animation=hw_cmd["animation"],
                    led=hw_cmd.get("led"),
                    device_id="momo-01"
                )
                await self.channel_layer.group_send(
                    self.DEVICE_GROUP,
                    {"type": "broadcast_message", "payload": cmd}
                )
                if self.serial_bridge and self.serial_bridge.running:
                    self.serial_bridge.send_command(cmd)

        # 4. Inbound Hardware Button Event from ESP32
        elif msg_type == "button_event":
            btn = content.get("button", "action")
            logger.info(f"Hardware button pressed: {btn}")
            reaction_msg = "You pressed my button! I am ready to help. ★ᴗ★"
            await self.channel_layer.group_send(
                self.COMPANION_GROUP,
                {
                    "type": "broadcast_message",
                    "payload": {
                        "type": "momo_response",
                        "source": "hardware_button",
                        "message": reaction_msg,
                        "expression": "excited",
                        "animation": "celebrate",
                        "speak": True,
                        "timestamp": time.time(),
                    }
                }
            )

        # 5. Heartbeat Telemetry from ESP32
        elif msg_type == "heartbeat":
            device_id = content.get("device_id", "momo-01")
            battery = content.get("battery_pct")
            rssi = content.get("rssi")
            HeartbeatMonitor.record_heartbeat(
                device_id=device_id,
                battery_pct=battery,
                rssi=rssi
            )

        else:
            logger.warning(f"Unhandled WebSocket message type: {msg_type}")

    async def broadcast_message(self, event):
        payload = event.get("payload", {})
        await self.send_json(payload)
