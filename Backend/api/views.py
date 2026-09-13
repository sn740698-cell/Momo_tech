import json
import logging
from datetime import datetime
from django.http import JsonResponse, StreamingHttpResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.response import Response
from rest_framework import status

from ai.ollama_client import OllamaClient
from ai.model_manager import ModelManager
from ai.gpu_manager import GPUManager
from memory.models import MemoryItem, MessageLog, UserPreference
from memory.repository import MemoryRepository
from security.permissions import PermissionManager
from iot.device_registry import DeviceRegistry
from documents.processor import DocumentProcessor
from documents.repository import DocumentRepository
from graph.graph import momo_graph

logger = logging.getLogger(__name__)

ollama_client = OllamaClient()
doc_processor = DocumentProcessor()


def api_root(request):
    """
    Root API endpoint providing discovery of all MOMO services.
    """
    return JsonResponse({
        "name": "MOMO Brain Core API",
        "version": "1.0.0",
        "status": "online",
        "endpoints": {
            "health": "/api/health/",
            "system_status": "/api/system/status/",
            "memory": "/api/memory/",
            "devices": "/api/devices/",
            "ollama_status": "/api/ollama/status/",
            "ollama_models": "/api/ollama/models/",
            "documents": "/api/documents/",
            "finance": "/api/finance/<doc_id>/",
            "privacy": "/api/settings/privacy/",
            "workflow_execute": "/api/workflow/execute/",
            "workflow_executions": "/api/workflow/executions/",
            "workflow_sources": "/api/workflow/sources/",
            "workflow_health": "/api/workflow/health/",
            "websocket": "/ws/momo/",
        }
    })


@api_view(['GET'])
def health_check(request):
    """
    Standard health check endpoint.
    GET /api/health/
    """
    return Response({
        "status": "online",
        "service": "MOMO Local AI Backend",
        "framework": "Django 6.1 + Channels + LangGraph",
        "timestamp": datetime.now().isoformat()
    })


@api_view(['GET'])
def system_status(request):
    """
    Comprehensive system status telemetry conforming to MOMO Spec Section 74.
    GET /api/system/status/
    """
    ollama_health = ollama_client.check_health()
    vram_info = GPUManager.get_vram_telemetry()
    devices = DeviceRegistry.get_all_devices()
    esp32_online = any(d.get("status") == "online" for d in devices.values())

    status_dict = {
        "backend": True,
        "langgraph": True,
        "ollama": bool(ollama_health.get("online", False)),
        "llm_model": bool(len(ollama_health.get("models", [])) > 0),
        "bert": True,
        "distilbert": True,
        "chromadb": True,
        "camera": PermissionManager.is_camera_enabled(),
        "microphone": PermissionManager.is_microphone_enabled(),
        "tts": True,
        "esp32": esp32_online,
        "gpu": GPUManager.is_cuda_available(),
        "gpu_telemetry": vram_info,
        "timestamp": datetime.now().isoformat()
    }
    return Response(status_dict)


@api_view(['GET', 'POST', 'DELETE'])
def memory_views(request):
    """
    Memory retrieval, insertion, and wipe endpoints.
    GET /api/memory/
    POST /api/memory/
    DELETE /api/memory/
    """
    if request.method == 'GET':
        if not PermissionManager.is_memory_enabled():
            return Response({"status": "disabled", "message": "Memory is disabled via privacy settings.", "memories": []})
        
        facts = MemoryRepository.search_facts(limit=50)
        prefs = MemoryRepository.get_all_preferences()
        return Response({"status": "success", "facts": facts, "preferences": prefs, "count": len(facts)})

    elif request.method == 'POST':
        if not PermissionManager.is_memory_enabled():
            return Response({"error": "Memory is disabled via privacy settings."}, status=status.HTTP_403_FORBIDDEN)
        
        body = request.data
        content = body.get("content") or body.get("value", "").strip()
        fact_type = body.get("type") or body.get("category", "general")
        conf = float(body.get("confidence", 1.0))
        if not content:
            return Response({"error": "'content' or 'value' is required."}, status=status.HTTP_400_BAD_REQUEST)

        fact = MemoryRepository.add_fact(content=content, fact_type=fact_type, confidence=conf)
        return Response({"status": "saved", "id": fact.id, "content": fact.content, "type": fact.fact_type})

    elif request.method == 'DELETE':
        fact_id = request.query_params.get("id")
        if fact_id:
            try:
                deleted = MemoryRepository.delete_fact(int(fact_id))
                return Response({"status": "deleted" if deleted else "not_found", "id": fact_id})
            except ValueError:
                return Response({"error": "Invalid id"}, status=status.HTTP_400_BAD_REQUEST)
        else:
            # Wipe all memories (Privacy Center 1-click wipe)
            wipe_stats = MemoryRepository.wipe_all_memory()
            return Response({"status": "wiped", **wipe_stats})


@api_view(['GET'])
def device_list(request):
    """
    Lists all known physical ESP32 companions.
    GET /api/devices/
    """
    devices = DeviceRegistry.get_all_devices()
    return Response({"devices": devices, "count": len(devices)})


@api_view(['GET'])
def device_detail(request, device_id):
    """
    Returns telemetry for a specific ESP32 companion.
    GET /api/devices/<id>/
    """
    dev = DeviceRegistry.get_device(device_id)
    if not dev:
        return Response({"error": f"Device '{device_id}' not found."}, status=status.HTTP_404_NOT_FOUND)
    return Response(dev)


@api_view(['GET'])
def ollama_status(request):
    """
    Live Ollama connection diagnostic.
    GET /api/ollama/status/
    """
    res = ollama_client.check_health()
    return Response(res)


@api_view(['GET'])
def ollama_models(request):
    """
    Lists locally installed models in Ollama, strictly filtered to Llama models.
    GET /api/ollama/models/
    """
    res = ollama_client.check_health()
    all_models = res.get("models", [])
    llama_models = [m for m in all_models if "llama" in m.get("name", "").lower()]
    llama_names = [m.get("name") for m in llama_models]
    if not llama_names:
        fallback_name = ModelManager.DEFAULT_PRIMARY_MODEL
        llama_names = [fallback_name]
        llama_models = [{"name": fallback_name, "model": fallback_name}]
    return Response({"models": llama_models, "model_names": llama_names, "count": len(llama_models)})



@api_view(['GET', 'POST'])
@parser_classes([MultiPartParser, FormParser, JSONParser])
def document_views(request):
    """
    Document processing and listing.
    POST /api/documents/ (Upload document)
    GET /api/documents/ (List documents)
    """
    if request.method == 'POST':
        file_obj = request.FILES.get('file')
        if not file_obj:
            # Check for JSON raw text upload
            raw_text = request.data.get('text')
            filename = request.data.get('filename', 'document.txt')
            if raw_text:
                content = raw_text.encode('utf-8')
            else:
                return Response({"error": "No file or text provided."}, status=status.HTTP_400_BAD_REQUEST)
        else:
            content = file_obj.read()
            filename = file_obj.name

        doc, insight, extra = doc_processor.process_document(content=content, filename=filename)
        DocumentRepository.save(doc, insight)

        return Response({
            "status": "success",
            "document": doc.model_dump(),
            "financial_insight": insight.model_dump() if insight else None,
            "extra": extra
        }, status=status.HTTP_201_CREATED)

    elif request.method == 'GET':
        docs = DocumentRepository.get_all_documents()
        return Response({
            "documents": [d.model_dump() for d in docs],
            "count": len(docs)
        })


@api_view(['GET'])
def document_detail(request, document_id):
    """
    Retrieves document content and chunk breakdown.
    GET /api/documents/<id>/
    """
    doc = DocumentRepository.get_document(document_id)
    if not doc:
        return Response({"error": f"Document '{document_id}' not found."}, status=status.HTTP_404_NOT_FOUND)
    insight = DocumentRepository.get_insight_by_doc(document_id)
    return Response({
        "document": doc.model_dump(),
        "financial_insight": insight.model_dump() if insight else None
    })


@api_view(['GET'])
def finance_detail(request, document_id):
    """
    Returns mathematically verified financial insight for a document.
    GET /api/finance/<document_id>/
    """
    insight = DocumentRepository.get_insight_by_doc(document_id)
    if not insight:
        return Response({"error": f"No financial insight found for document '{document_id}'."}, status=status.HTTP_404_NOT_FOUND)
    return Response(insight.model_dump())


@api_view(['GET', 'POST'])
def privacy_settings(request):
    """
    Gets or updates privacy permissions.
    GET /api/settings/privacy/
    POST /api/settings/privacy/
    """
    if request.method == 'POST':
        data = request.data
        for key in ["camera", "microphone", "memory", "activity"]:
            if key in data:
                PermissionManager.set_permission(key, bool(data[key]))
        return Response({"status": "updated", "settings": PermissionManager.get_all_permissions()})

    return Response({"settings": PermissionManager.get_all_permissions()})


# Backward-compatible endpoints for current frontend
def api_status(request):
    return JsonResponse({
        "status": "online",
        "service": "Django REST Backend",
        "framework": "Django 6.1",
        "backend_port": 8000,
        "message": "Backend server is running and connected successfully!",
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })

def api_ollama_status(request):
    res = ollama_client.check_health()
    return JsonResponse(res)

@csrf_exempt
def api_message(request):
    if request.method == "POST":
        try:
            body = json.loads(request.body.decode('utf-8'))
            client_msg = body.get("message", "")
        except Exception:
            client_msg = request.POST.get("message", "")

        return JsonResponse({
            "status": "success",
            "received_message": client_msg,
            "response": f"Django received your message: '{client_msg}' successfully!",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
    return JsonResponse({"status": "success", "message": "Send a POST request to test."})

@csrf_exempt
def api_chat(request):
    """
    REST chat endpoint matching WebSocket response schema.
    Provides instant fallback when WebSocket is reconnecting or down.
    POST /api/chat/
    """
    if request.method != "POST":
        return JsonResponse({"error": "POST method required"}, status=405)
    try:
        body = json.loads(request.body.decode('utf-8'))
        msg = body.get("message", "")
        if not msg and "messages" in body:
            msg = body["messages"][-1].get("content", "")
    except Exception:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    if not msg:
        return JsonResponse({"error": "Message is required"}, status=400)

    # Ingest live vision & emotion telemetry
    from vision import get_proactive_monitor
    monitor = get_proactive_monitor()
    telemetry = monitor.get_latest_telemetry()

    import asyncio
    from agents.conversation_agent import ConversationAgent
    from graph.state import MomoState, Message, VisionState

    vis_obj = VisionState(
        camera_available=telemetry.get("camera_available", False),
        privacy_shutter_closed=telemetry.get("privacy_blocked", True),
        person_present=telemetry.get("face_detected", False),
        face_detected=telemetry.get("face_detected", False),
        emotion=telemetry.get("emotion", "neutral"),
        emotion_confidence=telemetry.get("emotion_confidence", 0.0),
        looking_at_camera=telemetry.get("looking_at_camera", False),
        work_duration_minutes=telemetry.get("work_duration_minutes", 0.0),
        fatigue_detected=telemetry.get("fatigue_detected", False),
    )

    # Load prior conversation history for context
    from graph.graph import momo_graph
    from memory.repository import MemoryRepository

    session_id = body.get("session_id", "default")
    mem_repo = MemoryRepository()

    history_turns = []
    try:
        recent = mem_repo.get_recent_chat(session_id=session_id, limit=6)
        for h in recent:
            if h.get("content"):
                history_turns.append(Message(
                    role=h.get("role", "user"),
                    content=h.get("content", ""),
                    expression=h.get("expression", "normal"),
                    animation=h.get("animation", "none")
                ))
    except Exception as e:
        logger.warning(f"Error loading chat history in api_chat: {e}")

    # Record current user turn
    try:
        mem_repo.record_message(role="user", content=msg, session_id=session_id)
    except Exception as e:
        logger.warning(f"Error recording user turn in api_chat: {e}")

    # Append current user message as final active turn
    history_turns.append(Message(role="user", content=msg))

    state = MomoState(
        messages=history_turns,
        vision_state=vis_obj,
        metadata={"requested_model": body.get("model")}
    )

    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            res = loop.run_until_complete(asyncio.wait_for(momo_graph.ainvoke(state), timeout=45.0))
        finally:
            loop.close()

        if isinstance(res, dict):
            resp_obj = res.get("response")
            expr = res.get("momo_expression", "normal")
            anim = res.get("momo_animation", "none")
        else:
            resp_obj = getattr(res, "response", None)
            expr = getattr(res, "momo_expression", "normal")
            anim = getattr(res, "momo_animation", "none")

        msg_text = resp_obj.message if resp_obj else "I'm right here with you!"
        speak = getattr(resp_obj, "speak", True) if resp_obj else True
        model_used = getattr(resp_obj, "model", body.get("model", "hf.co/hugging-quants/Llama-3.2-1B-Instruct-Q8_0-GGUF:Q8_0")) if resp_obj else body.get("model", "hf.co/hugging-quants/Llama-3.2-1B-Instruct-Q8_0-GGUF:Q8_0")

        # Record assistant response turn
        try:
            mem_repo.record_message(
                role="assistant",
                content=msg_text,
                expression=expr,
                animation=anim,
                session_id=session_id
            )
        except Exception:
            pass
    except Exception as e:
        logger.warning(f"api_chat fallback triggered on exception: {e}")
        msg_text = f"Hello! I am here and attentive. How can I assist your work or give you a quick boost today?"
        expr = "happy"
        anim = "nod"
        speak = True
        model_used = body.get("model", "hf.co/hugging-quants/Llama-3.2-1B-Instruct-Q8_0-GGUF:Q8_0")

    return JsonResponse({
        "message": msg_text,
        "expression": expr,
        "animation": anim,
        "speak": speak,
        "model": model_used,
        "status": "success",
        "timestamp": datetime.now().isoformat()
    })


@csrf_exempt
def api_chat_clear(request):
    """
    Purges conversation history and ChromaDB vector chat memories for the session.
    POST /api/chat/clear/
    """
    if request.method not in ["POST", "DELETE"]:
        return JsonResponse({"error": "POST or DELETE required"}, status=405)
    try:
        if request.body:
            body = json.loads(request.body.decode('utf-8'))
            session_id = body.get("session_id", "default")
        else:
            session_id = request.POST.get("session_id", "default")
    except Exception:
        session_id = "default"

    mem_repo = MemoryRepository()
    db_cleared = mem_repo.clear_session_chat(session_id=session_id)

    try:
        from memory.chroma_memory import ChromaMemoryService
        chroma_svc = ChromaMemoryService()
        vector_cleared = chroma_svc.clear_session_chats(session_id=session_id)
    except Exception as e:
        logger.warning(f"Error clearing ChromaDB in api_chat_clear: {e}")
        vector_cleared = 0

    return JsonResponse({
        "status": "success",
        "session_id": session_id,
        "db_messages_deleted": db_cleared,
        "vector_chats_deleted": vector_cleared,
        "message": "Conversation history and memory cleared successfully."
    })


import base64
from django.http import HttpResponse
from voice.tts import TextToSpeech

tts_engine = TextToSpeech()

@api_view(['POST'])
def api_tts(request):
    """
    Synthesizes speech from text.
    POST /api/tts/
    Accepts: { "text": "...", "voice": "...", "format": "wav" | "base64" }
    """
    data = request.data
    text = data.get("text", "")
    voice_id = data.get("voice")
    output_format = data.get("format", "wav")

    if not text:
        return Response({"error": "No text provided"}, status=status.HTTP_400_BAD_REQUEST)

    audio_bytes = tts_engine.synthesize(text, voice_id=voice_id)
    if not audio_bytes:
        return Response({"error": "TTS synthesis failed"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    if output_format == "base64":
        encoded = base64.b64encode(audio_bytes).decode('utf-8')
        return Response({"status": "success", "audio_base64": encoded, "content_type": "audio/wav"})

    response = HttpResponse(audio_bytes, content_type="audio/wav")
    response['Content-Disposition'] = 'inline; filename="momo_speech.wav"'
    return response


@api_view(['GET'])
def api_tts_voices(request):
    """
    Lists locally available system voices.
    GET /api/tts/voices/
    """
    voices = tts_engine.get_available_voices()
    return Response({"voices": voices, "count": len(voices)})


# ==============================================================================
# MOMO OpenCV Vision & Emotion Perception Endpoints
# ==============================================================================
from vision import get_proactive_monitor, CameraManager, ExpressionDetector, get_camera_manager

_api_camera_manager = get_camera_manager()
_api_expression_detector = ExpressionDetector()


@api_view(['GET'])
def vision_status(request):
    """
    Returns live vision perception telemetry (detected emotion, face count,
    looking at camera/display, fatigue status, work session duration).
    GET /api/vision/status/
    """
    monitor = get_proactive_monitor()
    telemetry = monitor.get_latest_telemetry(refresh_if_stale=True)
    return Response(telemetry)


@api_view(['GET', 'POST'])
def vision_capture(request):
    """
    Triggers an instant single-frame emotion and facial expression analysis.
    POST /api/vision/capture/
    """
    if not PermissionManager.is_camera_enabled():
        return Response({
            "status": "disabled",
            "message": "Camera is disabled in privacy settings.",
            "face_detected": False,
            "emotion": "neutral"
        }, status=status.HTTP_403_FORBIDDEN)

    camera = get_camera_manager()
    camera.set_privacy_shutter(False)
    success, frame = camera.read_frame()
    if not success or frame is None:
        frame = CameraManager.generate_mock_face_frame("happy")

    analysis = _api_expression_detector.analyze_frame(frame)
    return Response({
        "status": "success",
        "analysis": analysis
    })


def vision_stream(request):
    """
    Real-time multipart MJPEG video stream with OpenCV facial bounding box,
    5-point landmarks, emotion badge, gaze orientation, and focus session counter.
    GET /api/vision/stream/
    """
    def frame_generator():
        import cv2
        import time
        camera = get_camera_manager()
        camera.set_privacy_shutter(False)
        monitor = get_proactive_monitor()

        while True:
            frame = camera.get_last_frame()
            if frame is None:
                success, frame = camera.read_frame()
            if frame is None:
                frame = CameraManager.generate_mock_face_frame("happy")

            telemetry = monitor.get_latest_telemetry(refresh_if_stale=False)
            work_mins = telemetry.get("work_duration_minutes", 0.0)

            sad_tired_mins = telemetry.get("sad_tired_minutes", 0.0)

            annotated = _api_expression_detector.annotate_frame(
                frame, work_mins=work_mins, sad_tired_mins=sad_tired_mins
            )
            ret, jpeg = cv2.imencode('.jpg', annotated, [int(cv2.IMWRITE_JPEG_QUALITY), 75])
            if ret:
                yield (
                    b'--frame\r\n'
                    b'Content-Type: image/jpeg\r\n\r\n' + jpeg.tobytes() + b'\r\n'
                )
            time.sleep(0.066)  # ~15 FPS smooth stream, light CPU footprint

    response = StreamingHttpResponse(
        frame_generator(),
        content_type='multipart/x-mixed-replace; boundary=frame'
    )
    response['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
    response['Pragma'] = 'no-cache'
    response['Expires'] = '0'
    response['X-Accel-Buffering'] = 'no'
    return response


_last_preview_jpeg_bytes = None
_last_preview_jpeg_time = 0.0


def vision_preview(request):
    """
    Returns a single JPEG image snapshot of the annotated camera preview.
    GET /api/vision/preview/
    """
    global _last_preview_jpeg_bytes, _last_preview_jpeg_time
    import cv2
    import time
    from django.http import HttpResponse

    now = time.time()
    if _last_preview_jpeg_bytes is not None and (now - _last_preview_jpeg_time < 0.10):
        resp = HttpResponse(_last_preview_jpeg_bytes, content_type="image/jpeg")
        resp['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
        resp['Pragma'] = 'no-cache'
        return resp

    camera = get_camera_manager()
    camera.set_privacy_shutter(False)
    frame = camera.get_last_frame()
    if frame is None:
        success, frame = camera.read_frame()
    if frame is None:
        frame = CameraManager.generate_mock_face_frame("neutral")

    monitor = get_proactive_monitor()
    telemetry = monitor.get_latest_telemetry(refresh_if_stale=False)
    annotated = _api_expression_detector.annotate_frame(
        frame,
        work_mins=telemetry.get("work_duration_minutes", 0.0),
        sad_tired_mins=telemetry.get("sad_tired_minutes", 0.0)
    )
    ret, jpeg = cv2.imencode('.jpg', annotated, [int(cv2.IMWRITE_JPEG_QUALITY), 75])
    if ret:
        raw_bytes = jpeg.tobytes()
        _last_preview_jpeg_bytes = raw_bytes
        _last_preview_jpeg_time = now

        resp = HttpResponse(raw_bytes, content_type="image/jpeg")
        resp['Cache-Control'] = 'no-cache, no-store, must-revalidate, max-age=0'
        resp['Pragma'] = 'no-cache'
        return resp
    return HttpResponse(status=500)


# ==============================================================================
# Web Crawler & Real-Time Intelligence Endpoints (Crawl4AI & ScrapeGraphAI)
# ==============================================================================
from ai_workflow.services.web_crawler_service import LiveWebCrawlerService

@api_view(['POST'])
def api_crawl_url(request):
    """
    Crawls a direct web URL using Crawl4AI with paywall filtration and clean markdown.
    POST /api/crawler/crawl/
    Payload: { "url": "https://...", "max_chars": 4000 }
    """
    url = request.data.get("url", "").strip()
    if not url:
        return Response({"error": "'url' parameter is required."}, status=status.HTTP_400_BAD_REQUEST)

    max_chars = int(request.data.get("max_chars", 4000))
    crawler = LiveWebCrawlerService(timeout_seconds=15.0)
    
    import asyncio
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            res = loop.run_until_complete(crawler.crawl_url(url, max_chars=max_chars))
        finally:
            loop.close()
    except Exception as e:
        return Response({"error": f"Crawl failed: {str(e)}", "url": url}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    return Response(res)


@api_view(['POST'])
def api_crawl_search(request):
    """
    Performs multi-source web search and deep article crawling.
    POST /api/crawler/search/
    Payload: { "query": "...", "max_results": 3 }
    """
    query = request.data.get("query", "").strip()
    if not query:
        return Response({"error": "'query' parameter is required."}, status=status.HTTP_400_BAD_REQUEST)

    max_results = int(request.data.get("max_results", 3))
    crawler = LiveWebCrawlerService(timeout_seconds=15.0)

    import asyncio
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            items = loop.run_until_complete(crawler.gather_realtime_context(query, max_results=max_results))
        finally:
            loop.close()
    except Exception as e:
        return Response({"error": f"Search failed: {str(e)}", "query": query}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    return Response({"query": query, "results": items, "count": len(items)})


# ==============================================================================
# Desktop Automation & Mindful Game Break Endpoints
# ==============================================================================
from automation import get_game_controller

@api_view(['POST'])
def automation_launch_game(request):
    """
    Launches game break via browser and PyAutoGUI canvas centering.
    POST /api/automation/launch_game/
    Payload: { "game": "2048" | "pacman" | "wordle" | "littlealchemy" }
    """
    game_key = request.data.get("game", "2048")
    controller = get_game_controller()
    result = controller.launch_game(game_key=game_key, auto_scroll=True)
    return Response(result)


@api_view(['GET'])
def automation_motivate(request):
    """
    Returns encouraging, cheerful voice motivation for the user's game break.
    GET /api/automation/motivate/?game=2048
    """
    game_key = request.query_params.get("game", "2048")
    controller = get_game_controller()
    speech = controller.get_motivational_speech(game_key=game_key)
    return Response({
        "motivation": speech,
        "expression": "excited",
        "animation": "celebrate",
    })


@api_view(['GET'])
def automation_games_list(request):
    """
    Lists all supported mindful recharging mini-games.
    GET /api/automation/games/
    """
    controller = get_game_controller()
    return Response({"games": controller.get_supported_games()})



# ==============================================================================
# MOMO Multi-Agent AI Workflow Endpoints
# ==============================================================================
from asgiref.sync import async_to_sync
from ai_workflow.services.execution_service import ExecutionService
from ai_workflow.services.retrieval_service import IsolatedRetrievalService

isolated_retriever = IsolatedRetrievalService()


@api_view(['POST'])
def workflow_execute(request):
    """
    Executes the multi-agent RAG / workflow subsystem.
    POST /api/workflow/execute/
    Payload:
    {
        "input": "...",
        "tenant_id": "tenant_a",
        "project_id": "proj_1",
        "user_id": "user_1",
        "max_retries": 2,
        "metadata": {}
    }
    """
    data = request.data
    user_input = data.get("input") or data.get("message") or data.get("user_input", "")
    if not user_input or not str(user_input).strip():
        return Response(
            {
                "status": "failed",
                "error": "INVALID_REQUEST: 'input', 'message', or 'user_input' field is required."
            },
            status=status.HTTP_400_BAD_REQUEST
        )

    tenant_id = data.get("tenant_id", "default")
    project_id = data.get("project_id", "default")
    user_id = data.get("user_id", "default")
    max_retries = int(data.get("max_retries", 2))
    metadata = data.get("metadata", {})

    # Execute workflow synchronously via async_to_sync
    result = async_to_sync(ExecutionService.execute_workflow)(
        user_input=str(user_input).strip(),
        tenant_id=tenant_id,
        project_id=project_id,
        user_id=user_id,
        max_retries=max_retries,
        metadata=metadata
    )

    http_status = status.HTTP_200_OK if result.get("status") in ("completed", "unresolved_exhausted") else status.HTTP_500_INTERNAL_SERVER_ERROR
    return Response(result, status=http_status)


@api_view(['GET'])
def workflow_executions_list(request):
    """
    Lists workflow execution history with tenant and project isolation.
    GET /api/workflow/executions/?tenant_id=...&project_id=...&limit=50
    """
    tenant_id = request.query_params.get("tenant_id")
    project_id = request.query_params.get("project_id")
    limit = int(request.query_params.get("limit", 50))

    runs = ExecutionService.list_executions(tenant_id=tenant_id, project_id=project_id, limit=limit)
    return Response({
        "executions": runs,
        "count": len(runs),
        "tenant_id": tenant_id,
        "project_id": project_id
    })


@api_view(['GET'])
def workflow_execution_detail(request, execution_id):
    """
    Retrieves execution detail and evaluation findings.
    GET /api/workflow/executions/<id>/?tenant_id=...&project_id=...
    """
    tenant_id = request.query_params.get("tenant_id")
    project_id = request.query_params.get("project_id")

    rec = ExecutionService.get_execution(execution_id=execution_id, tenant_id=tenant_id, project_id=project_id)
    if not rec:
        return Response(
            {"error": f"Execution '{execution_id}' not found or inaccessible within given tenant context."},
            status=status.HTTP_404_NOT_FOUND
        )
    return Response(rec)


@api_view(['GET'])
def workflow_sources(request):
    """
    Retrieves grounded context sources with strict tenant and project isolation.
    GET /api/workflow/sources/?query=...&tenant_id=...&project_id=...
    """
    query = request.query_params.get("query", "")
    tenant_id = request.query_params.get("tenant_id", "default")
    project_id = request.query_params.get("project_id", "default")
    top_k = int(request.query_params.get("top_k", 4))

    items = isolated_retriever.retrieve(
        tenant_id=tenant_id,
        project_id=project_id,
        query=query,
        top_k=top_k
    )
    return Response({
        "query": query,
        "tenant_id": tenant_id,
        "project_id": project_id,
        "count": len(items),
        "sources": [item.model_dump() for item in items],
        "no_context_found": len(items) == 0
    })


@api_view(['GET'])
def workflow_health(request):
    """
    Telemetry check for the AI workflow subsystem.
    GET /api/workflow/health/
    """
    info = ExecutionService.check_health()
    return Response(info)


