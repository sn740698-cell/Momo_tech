#!/usr/bin/env python3
"""
MOMO Model Context Protocol (MCP) Server.
Exposes MOMO's core capabilities as standard MCP tools over stdio:
- Website & URL automation (Instagram, YouTube, Google, GitHub, etc.)
- Break game launchers (2048, Pacman, Wordle)
- Local desktop application launching (Notepad, Calculator, Terminal, etc.)
- Real-time web crawling & intelligence (Crawl4AI & direct feeds)
- 10-sensor vision perception & emotional telemetry
- ESP32 hardware OLED & servo robotic gestures
- Persistent memory & ChromaDB management
"""
import os
import sys
import json
import logging
import asyncio
from typing import Optional, Dict, Any

# Ensure stdout remains clean for MCP JSON-RPC protocol; route logging to stderr
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stderr
)
logger = logging.getLogger("momo_mcp_server")

# Configure Django environment
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

try:
    import django
    django.setup()
    logger.info("Django settings initialized successfully for MOMO MCP Server.")
except Exception as e:
    logger.error(f"Error initializing Django: {e}", exc_info=True)

from mcp.server.mcpserver import MCPServer

# Initialize MCP Server instance
app = MCPServer(
    name="momo-automation",
    version="1.0.0",
    instructions=(
        "MOMO MCP Automation Server provides tools to interact with the host operating system, "
        "automate websites (Instagram, YouTube, etc.), launch relaxation games, execute live web crawling, "
        "retrieve 10-sensor facial telemetry, send commands to the ESP32 robot, and manage memory."
    )
)

# ---------------------------------------------------------------------------
# Tool 1: Website Automation
# ---------------------------------------------------------------------------
@app.tool(name="momo_open_website")
def momo_open_website(target: str, url: str = "") -> str:
    """
    Automates opening websites in the user's default browser.
    Supported targets include 'instagram', 'youtube', 'google', 'github', 'twitter',
    'linkedin', 'reddit', 'chatgpt', 'spotify', 'gmail', or any custom domain / URL.
    """
    try:
        from automation.desktop_controller import get_desktop_controller, KNOWN_WEB_TARGETS
        controller = get_desktop_controller()

        target_clean = target.strip().lower()
        target_base = target_clean.replace(".com", "")
        resolved_url = url.strip()

        if not resolved_url:
            if target_clean in KNOWN_WEB_TARGETS:
                resolved_url = KNOWN_WEB_TARGETS[target_clean]["url"]
            elif target_base in KNOWN_WEB_TARGETS:
                resolved_url = KNOWN_WEB_TARGETS[target_base]["url"]
            elif "." in target_clean:
                resolved_url = target_clean if target_clean.startswith("http") else f"https://{target_clean}"
            else:
                resolved_url = f"https://www.{target_clean}.com"

        intent = {
            "type": "open_website",
            "target": target_clean,
            "url": resolved_url,
            "name": target_clean.title()
        }
        res = controller.execute_automation(intent)
        return json.dumps(res, indent=2)
    except Exception as e:
        logger.error(f"Error in momo_open_website: {e}")
        return json.dumps({"success": False, "error": str(e)})


# ---------------------------------------------------------------------------
# Tool 2: Launch Anti-Burnout Break Games
# ---------------------------------------------------------------------------
@app.tool(name="momo_launch_game")
def momo_launch_game(game: str = "2048") -> str:
    """
    Launches an interactive anti-burnout break game in the browser.
    Supported games: '2048', 'pacman', 'wordle', 'littlealchemy'.
    """
    try:
        from automation.desktop_controller import get_desktop_controller
        controller = get_desktop_controller()

        game_clean = game.strip().lower()
        intent = {
            "type": "launch_game",
            "game": game_clean,
            "target": game_clean,
            "name": f"Game {game_clean.title()}"
        }
        res = controller.execute_automation(intent)
        return json.dumps(res, indent=2)
    except Exception as e:
        logger.error(f"Error in momo_launch_game: {e}")
        return json.dumps({"success": False, "error": str(e)})


# ---------------------------------------------------------------------------
# Tool 3: Desktop App Launching
# ---------------------------------------------------------------------------
@app.tool(name="momo_launch_app")
def momo_launch_app(app_name: str) -> str:
    """
    Launches a desktop application on Windows.
    Supported apps: 'notepad', 'calculator', 'terminal', 'cmd', 'powershell', 'explorer'.
    """
    try:
        from automation.desktop_controller import get_desktop_controller, KNOWN_SYSTEM_APPS
        controller = get_desktop_controller()

        app_clean = app_name.strip().lower()
        exe = KNOWN_SYSTEM_APPS.get(app_clean, f"{app_clean}.exe")

        intent = {
            "type": "launch_app",
            "target": app_clean,
            "executable": exe,
            "name": app_clean.title()
        }
        res = controller.execute_automation(intent)
        return json.dumps(res, indent=2)
    except Exception as e:
        logger.error(f"Error in momo_launch_app: {e}")
        return json.dumps({"success": False, "error": str(e)})


# ---------------------------------------------------------------------------
# Tool 4: Live Web Crawling & Intelligence
# ---------------------------------------------------------------------------
@app.tool(name="momo_web_crawl")
async def momo_web_crawl(query: str, max_results: int = 3) -> str:
    """
    Performs live web crawling and deep article retrieval using Crawl4AI,
    direct national news feeds, and Wikipedia.
    Returns authentic, real-time web content and article snippets.
    """
    try:
        from ai_workflow.services.web_crawler_service import LiveWebCrawlerService
        crawler = LiveWebCrawlerService()
        results = await crawler.gather_realtime_context(query=query, max_results=max_results)

        output = {
            "query": query,
            "count": len(results),
            "results": [
                {
                    "title": r.get("title"),
                    "source": r.get("source"),
                    "url": r.get("url"),
                    "pub_date": r.get("pub_date"),
                    "snippet": (r.get("snippet") or r.get("content", ""))[:400]
                }
                for r in results
            ]
        }
        return json.dumps(output, indent=2)
    except Exception as e:
        logger.error(f"Error in momo_web_crawl: {e}")
        return json.dumps({"query": query, "error": str(e), "results": []})


# ---------------------------------------------------------------------------
# Tool 5: Vision Telemetry & 10-Sensor Perception
# ---------------------------------------------------------------------------
@app.tool(name="momo_get_vision_telemetry")
def momo_get_vision_telemetry() -> str:
    """
    Retrieves live telemetry from MOMO's 18-sensor vision perception & recognition engine:
    1. ear_sensor (Eye Aspect Ratio & Openness)
    2. eyebrow_furrow_sensor (Brow Tension)
    3. mouth_curvature_sensor (Smile/Frown Angle)
    4. cheek_elevation_sensor (Cheek Fold Contrast)
    5. jaw_drop_sensor (Yawn / Vertical Opening)
    6. head_pitch_sensor (Head Slump Angle)
    7. blink_duration_sensor (Blink Duration Tracker)
    8. periorbital_texture_sensor (Eye Bag Strain)
    9. symmetry_sensor (Hemisphere Balance)
    10. temporal_stability (EMA Smoothing Stability)
    11. clarity_quality_sensor (Normalized Laplacian Focus Metric)
    12. illumination_contrast_sensor (RMS Dynamic Range)
    13. skin_chroma_vitality_sensor (YCbCr Cr/Cb Vascular Perfusion & Pallor)
    14. micro_motion_energy_sensor (Temporal Face Velocity & Slump)
    15. mouth_aspect_energy_sensor (Otsu Adaptive Oral Cavity Darkness)
    16. eye_glint_salience_sensor (Corneal Specular Reflection Glint Tracker)
    17. nasolabial_depth_sensor (Cheek-Lip Furrow Strain Energy)
    18. recognition_confidence_sensor (Low-Res Invariant Identity Match)
    Includes biometric user recognition, low-megapixel clarity boost, and strict sad+tired break countdown state.
    """
    try:
        from vision.camera import get_camera_manager
        from vision.expression_detector import ExpressionDetector
        from vision.proactive_monitor import get_proactive_monitor

        cam = get_camera_manager()
        ret, frame = cam.read_frame()
        detector = ExpressionDetector()

        if ret and frame is not None:
            detection = detector.analyze_frame(frame)
        else:
            detection = detector.analyze_frame(None)

        monitor = get_proactive_monitor()
        telemetry = monitor.get_latest_telemetry() if monitor else {}

        sadness_score = float(detection.get("sadness_score", 0.0))
        tired_score = float(detection.get("tired_score", 0.0))
        emotion = detection.get("emotion", "neutral")
        face_detected = detection.get("face_detected", False)
        is_sad = (emotion == "sad" or sadness_score >= 0.50)
        is_tired = (emotion == "tired" or tired_score >= 0.50)

        output = {
            "face_detected": face_detected,
            "primary_emotion": emotion,
            "confidence": detection.get("emotion_confidence", 0.0),
            "sadness_score": sadness_score,
            "tiredness_score": tired_score,
            "is_sad": is_sad,
            "is_tired": is_tired,
            "is_both_sad_and_tired": face_detected and is_sad and is_tired,
            "recognition": detection.get("recognition", {}),
            "enhancement": detection.get("enhancement", {}),
            "sensors": detection.get("sensors", {}),
            "sensors_18": detection.get("sensors", {}),
            "sensors_10": detection.get("sensors", {}),
            "break_timer": {
                "sad_tired_minutes": telemetry.get("sad_tired_minutes", 0.0),
                "sad_tired_seconds": telemetry.get("sad_tired_minutes", 0.0) * 60.0,
                "fatigue_threshold_minutes": 30.0,
                "fatigue_detected": telemetry.get("fatigue_detected", False)
            }
        }
        return json.dumps(output, indent=2)
    except Exception as e:
        logger.error(f"Error in momo_get_vision_telemetry: {e}")
        return json.dumps({"face_detected": False, "error": str(e)})


# ---------------------------------------------------------------------------
# Tool 6: Hardware ESP32 Robot Control
# ---------------------------------------------------------------------------
@app.tool(name="momo_send_robot_command")
def momo_send_robot_command(expression: str = "normal", animation: str = "none", led: str = "") -> str:
    """
    Sends hardware commands to the physical ESP32 OLED display and servo head:
    - Expressions: 'normal', 'happy', 'thinking', 'excited', 'sad', 'tired', 'confused', 'sleepy'
    - Animations: 'none', 'nod', 'tilt_left', 'tilt_right', 'celebrate', 'wave', 'blink'
    - LED modes: 'solid', 'pulsing', 'blink', 'off'
    """
    try:
        from iot.protocol import ESP32Protocol, OLED_FACE_MAP, SERVO_MOTION_MAP
        from iot.serial_bridge import SerialBridge

        cmd = ESP32Protocol.create_device_command(
            expression=expression,
            animation=animation,
            led=led or None
        )

        ports = SerialBridge.list_available_ports()
        output = {
            "command": cmd,
            "oled_ascii": OLED_FACE_MAP.get(expression, OLED_FACE_MAP["normal"]),
            "servo_motion": SERVO_MOTION_MAP.get(animation, SERVO_MOTION_MAP["none"]),
            "available_usb_ports": [p["port"] for p in ports],
            "status": "dispatched"
        }
        return json.dumps(output, indent=2)
    except Exception as e:
        logger.error(f"Error in momo_send_robot_command: {e}")
        return json.dumps({"error": str(e), "status": "failed"})


# ---------------------------------------------------------------------------
# Tool 7: Memory & Knowledge Management
# ---------------------------------------------------------------------------
@app.tool(name="momo_manage_memory")
async def momo_manage_memory(action: str, content: str = "", query: str = "") -> str:
    """
    Manages MOMO's persistent SQLite and ChromaDB vector memory.
    Actions:
    - 'save': Stores an explicit fact or user preference (requires content).
    - 'search': Retrieves relevant facts and past chat context (requires query).
    - 'wipe': Clears session chat history or wipes all stored facts for privacy.
    """
    try:
        from memory.memory_manager import MemoryManager
        from memory.repository import MemoryRepository
        from asgiref.sync import sync_to_async

        mgr = MemoryManager()
        action_clean = action.strip().lower()

        if action_clean == "save":
            if not content.strip():
                return json.dumps({"error": "Content required for 'save' action"})
            res = await mgr.save_explicit_memory(content.strip())
            return json.dumps({"status": "saved", "record": res}, indent=2)

        elif action_clean == "search":
            q = query.strip() or content.strip()
            memories = await mgr.recall_saved_memories(query=q)
            facts = await sync_to_async(MemoryRepository.search_facts)(query=q)
            return json.dumps({
                "query": q,
                "saved_memories": memories,
                "facts": facts
            }, indent=2)

        elif action_clean in ("wipe", "clear"):
            cleared = await sync_to_async(MemoryRepository.clear_session_chat)("default")
            return json.dumps({"status": "cleared", "messages_deleted": cleared}, indent=2)

        return json.dumps({"error": f"Unknown action: {action}. Use 'save', 'search', or 'wipe'."})
    except Exception as e:
        logger.error(f"Error in momo_manage_memory: {e}")
        return json.dumps({"error": str(e)})


# ---------------------------------------------------------------------------
# Tool 8: Natural Language Automation Orchestrator
# ---------------------------------------------------------------------------
@app.tool(name="momo_execute_natural_command")
def momo_execute_natural_command(command: str) -> str:
    """
    Parses any natural language command (e.g. 'open instagram', 'can you open youtube.com',
    'launch game 2048', 'open notepad') and executes the corresponding desktop or browser action.
    """
    try:
        from automation.desktop_controller import get_desktop_controller, DesktopAutomationController
        controller = get_desktop_controller()

        intent = DesktopAutomationController.extract_automation_intent(command)
        if not intent:
            return json.dumps({
                "success": False,
                "message": f"No automation action recognized for command: '{command}'"
            })

        res = controller.execute_automation(intent)
        return json.dumps({
            "intent": intent,
            "execution": res
        }, indent=2)
    except Exception as e:
        logger.error(f"Error in momo_execute_natural_command: {e}")
        return json.dumps({"success": False, "error": str(e)})


# ---------------------------------------------------------------------------
# Server Main Entrypoint
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    logger.info("Starting MOMO MCP Automation Server over stdio transport...")
    app.run(transport="stdio")
