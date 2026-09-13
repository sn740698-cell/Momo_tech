import os
import json
import time
import asyncio
import logging
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from asgiref.sync import sync_to_async

from graph.state import MomoState, Message, UserContext, MomoResponse, VisionState
from graph.graph import momo_graph
from iot.protocol import ESP32Protocol
from iot.heartbeat import HeartbeatMonitor
from iot.serial_bridge import get_serial_bridge
from security.permissions import PermissionManager
from memory.repository import MemoryRepository
from memory.memory_manager import MemoryManager
from ai.response_parser import ResponseParser
from vision import get_proactive_monitor

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
        self.proactive_monitor = get_proactive_monitor()

    def _on_proactive_alert(self, telemetry: dict):
        """Callback invoked when ProactiveMonitor detects fatigue or sustained emotional state."""
        evt = telemetry.get("proactive_event")
        if not evt:
            return
        from channels.layers import get_channel_layer
        from asgiref.sync import async_to_sync
        layer = get_channel_layer()
        if layer:
            expr = evt.get("suggested_expression", "happy")
            anim = evt.get("suggested_animation", "tilt_left")
            payload = {
                "type": "momo_response",
                "source": "proactive_monitor",
                "message": evt.get("message", "Hey! How is your day going?"),
                "expression": expr,
                "animation": anim,
                "speak": True,
                "is_thinking": False,
                "model": "MomoProactiveCompanion",
                "timestamp": time.time(),
            }
            try:
                async_to_sync(layer.group_send)(
                    self.COMPANION_GROUP,
                    {"type": "broadcast_message", "payload": payload}
                )
                device_cmd = ESP32Protocol.create_device_command(
                    expression=expr,
                    animation=anim,
                    device_id="momo-01"
                )
                async_to_sync(layer.group_send)(
                    self.DEVICE_GROUP,
                    {"type": "broadcast_message", "payload": device_cmd}
                )
                if self.serial_bridge and self.serial_bridge.running:
                    self.serial_bridge.send_command(device_cmd)
            except Exception as e:
                logger.debug(f"Error dispatching proactive alert: {e}")

    async def connect(self):
        await self.channel_layer.group_add(self.COMPANION_GROUP, self.channel_name)
        await self.channel_layer.group_add(self.DEVICE_GROUP, self.channel_name)
        await self.accept()

        self.proactive_monitor.add_listener(self._on_proactive_alert)
        if PermissionManager.is_camera_enabled():
            self.proactive_monitor.start()

        logger.info(f"WebSocket client connected: {self.channel_name}")
        await self.send_json({
            "type": "connection_established",
            "status": "online",
            "message": "Connected to MOMO Brain Core WebSocket gateway.",
            "timestamp": time.time(),
        })

    async def disconnect(self, close_code):
        self.proactive_monitor.remove_listener(self._on_proactive_alert)
        await self.channel_layer.group_discard(self.COMPANION_GROUP, self.channel_name)
        await self.channel_layer.group_discard(self.DEVICE_GROUP, self.channel_name)
        logger.info(f"WebSocket client disconnected: {self.channel_name} (code: {close_code})")

    async def receive_json(self, content: dict, **kwargs):
        msg_type = content.get("type", "")

        # 1. Ping / Pong
        if msg_type == "ping":
            await self.send_json({"type": "pong", "timestamp": time.time()})
            return

        # 1.5. Live Vision Perception Poll
        elif msg_type == "poll_vision":
            telemetry = self.proactive_monitor.get_latest_telemetry()
            await self.send_json({
                "type": "vision_telemetry",
                "telemetry": telemetry,
                "timestamp": time.time()
            })
            return

        # 1.8. Launch Mindful Game Break Automation
        elif msg_type == "launch_game":
            from automation import get_game_controller
            game = content.get("game", "2048")
            ctrl = get_game_controller()
            res = ctrl.launch_game(game_key=game, auto_scroll=True)
            await self.send_json({
                "type": "game_launched",
                "result": res,
                "timestamp": time.time()
            })
            return

        # 1.9. Clear Chat & Purge Session Memory
        elif msg_type == "clear_chat":
            session_id = content.get("session_id", "default")
            res = await self.memory_manager.clear_session_memory(session_id=session_id)
            await self.send_json({
                "type": "chat_cleared",
                "session_id": session_id,
                "db_messages_deleted": res.get("db_messages_deleted", 0),
                "vector_chats_deleted": res.get("vector_chats_deleted", 0),
                "message": "Conversation history and memory have been cleared.",
                "timestamp": time.time()
            })
            return

        # 2. Chat Message -> Route through LangGraph Multi-Supervisor Workflow
        elif msg_type == "chat_message":
            user_text = content.get("message", "").strip()
            session_id = content.get("session_id", "default")
            if not user_text:
                return

            try:
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

                # 1. Load prior conversation turns so LangGraph agents have multi-turn context
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

                # 2. Safely record current user message in DB without failing if table is locked
                try:
                    await sync_to_async(self.memory_repo.record_message)(
                        role="user",
                        content=user_text,
                        session_id=session_id
                    )
                except Exception as db_err:
                    logger.warning(f"Could not record user turn in DB: {db_err}")

                # 3. Append current user message as the final active turn
                user_msg = Message(role="user", content=user_text)
                history_turns.append(user_msg)

                metadata = dict(content.get("metadata", {}))
                if content.get("model"):
                    metadata["requested_model"] = content.get("model")

                # Fetch live vision & emotional perception telemetry
                vision_tel = self.proactive_monitor.get_latest_telemetry()
                vision_obj = VisionState(
                    camera_available=vision_tel.get("camera_available", False),
                    privacy_shutter_closed=vision_tel.get("privacy_blocked", True),
                    person_present=vision_tel.get("face_detected", False),
                    face_detected=vision_tel.get("face_detected", False),
                    head_orientation=vision_tel.get("head_pose", "center"),
                    emotion=vision_tel.get("emotion", "neutral"),
                    emotion_confidence=vision_tel.get("emotion_confidence", 0.0),
                    looking_at_camera=vision_tel.get("looking_at_camera", False),
                    work_duration_minutes=vision_tel.get("work_duration_minutes", 0.0),
                    fatigue_detected=vision_tel.get("fatigue_detected", False),
                    expression_summary=vision_tel.get("expression_summary")
                )

                initial_state = MomoState(
                    messages=history_turns,
                    user_context=UserContext(
                        active_app=content.get("active_app", "Desktop"),
                        idle_seconds=content.get("idle_seconds", 0)
                    ),
                    vision_state=vision_obj,
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

                # Guaranteed guard: strip any residual JSON scaffolding or cutoff excuses
                msg_text = ResponseParser.clean_text(str(msg_text))
                if not msg_text or msg_text.strip() in ["{", "}", '""', "..."]:
                    msg_text = "I am at your service. Please let me know what you would like to explore."

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
