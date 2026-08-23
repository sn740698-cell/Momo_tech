import json
import logging
from datetime import datetime
import requests
from django.http import JsonResponse, StreamingHttpResponse
from django.views.decorators.csrf import csrf_exempt

logger = logging.getLogger(__name__)

OLLAMA_BASE_URL = "http://127.0.0.1:11434"

def api_root(request):
    """
    Root API endpoint providing metadata and available endpoints.
    """
    return JsonResponse({
        "status": "online",
        "message": "Welcome to MOMO API Server",
        "timestamp": datetime.now().isoformat(),
        "endpoints": {
            "status": "/api/status/",
            "message": "/api/message/",
            "ollama_status": "/api/ollama/status/",
            "chat": "/api/chat/"
        }
    })

def api_status(request):
    """
    Health check and server status endpoint.
    """
    return JsonResponse({
        "status": "online",
        "service": "Django REST Backend",
        "framework": "Django 6.1",
        "backend_port": 8000,
        "message": "Backend server is running and connected successfully!",
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })

@csrf_exempt
def api_message(request):
    """
    Handles GET and POST requests for testing message exchange with frontend.
    """
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

    return JsonResponse({
        "status": "success",
        "message": "Send a POST request with {'message': 'your text'} to test interaction.",
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })

def api_ollama_status(request):
    """
    Checks if the local Ollama service is reachable and fetches list of available models.
    """
    try:
        resp = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=3)
        if resp.status_code == 200:
            data = resp.json()
            models_raw = data.get("models", [])
            models_list = [
                {
                    "name": m.get("name"),
                    "size": m.get("size"),
                    "modified_at": m.get("modified_at"),
                    "details": m.get("details", {})
                }
                for m in models_raw
            ]
            
            version_str = "unknown"
            try:
                ver_resp = requests.get(f"{OLLAMA_BASE_URL}/api/version", timeout=2)
                if ver_resp.status_code == 200:
                    version_str = ver_resp.json().get("version", "unknown")
            except Exception:
                pass

            return JsonResponse({
                "status": "online",
                "ollama_host": OLLAMA_BASE_URL,
                "version": version_str,
                "models": models_list,
                "model_names": [m.get("name") for m in models_raw],
                "default_model": "qwen3:4b",
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })
        else:
            return JsonResponse({
                "status": "error",
                "ollama_host": OLLAMA_BASE_URL,
                "error": f"Ollama returned HTTP status {resp.status_code}",
                "models": [],
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }, status=502)
    except requests.exceptions.RequestException as e:
        return JsonResponse({
            "status": "offline",
            "ollama_host": OLLAMA_BASE_URL,
            "error": "Ollama is not reachable on localhost:11434. Make sure Ollama desktop/daemon is running.",
            "models": [],
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }, status=503)

@csrf_exempt
def api_chat(request):
    """
    Chat endpoint communicating with Ollama local LLM.
    Accepts:
    - model (str): e.g. "qwen3:4b"
    - messages (list of dict): [{"role": "user"|"assistant"|"system", "content": "..."}]
    - stream (bool, optional): whether to stream response tokens
    - system_prompt (str, optional): system prompt override
    - temperature (float, optional): generation temperature
    """
    if request.method != "POST":
        return JsonResponse({
            "status": "error",
            "message": "Only POST method is allowed on /api/chat/."
        }, status=405)

    try:
        body = json.loads(request.body.decode('utf-8'))
    except Exception:
        return JsonResponse({
            "status": "error",
            "message": "Invalid JSON body provided."
        }, status=400)

    model = body.get("model", "qwen3:4b")
    messages = body.get("messages", [])
    system_prompt = body.get("system_prompt", "You are MOMO AI, a helpful, precise, and friendly assistant.")
    stream_requested = bool(body.get("stream", False))
    temperature = body.get("temperature", 0.7)

    if not messages and "message" in body:
        messages = [{"role": "user", "content": body.get("message", "")}]

    if not messages:
        return JsonResponse({
            "status": "error",
            "message": "No messages provided in request payload."
        }, status=400)

    formatted_messages = []
    has_system = any(m.get("role") == "system" for m in messages)
    if not has_system and system_prompt:
        formatted_messages.append({"role": "system", "content": system_prompt})
    formatted_messages.extend(messages)

    payload = {
        "model": model,
        "messages": formatted_messages,
        "stream": stream_requested,
        "options": {
            "temperature": float(temperature)
        }
    }

    if stream_requested:
        def stream_generator():
            try:
                with requests.post(
                    f"{OLLAMA_BASE_URL}/api/chat",
                    json=payload,
                    stream=True,
                    timeout=180
                ) as r:
                    if r.status_code != 200:
                        err_text = r.text
                        yield f"data: {json.dumps({'error': f'Ollama error ({r.status_code}): {err_text}', 'done': True})}\n\n"
                        return

                    for line in r.iter_lines():
                        if line:
                            decoded = line.decode('utf-8')
                            try:
                                chunk_json = json.loads(decoded)
                                msg_dict = chunk_json.get("message", {})
                                delta_content = msg_dict.get("content", "")
                                delta_thinking = msg_dict.get("thinking", "")
                                is_done = chunk_json.get("done", False)
                                yield f"data: {json.dumps({'content': delta_content, 'thinking': delta_thinking, 'done': is_done, 'model': model})}\n\n"
                            except Exception:
                                yield f"data: {decoded}\n\n"
            except requests.exceptions.RequestException as e:
                yield f"data: {json.dumps({'error': f'Connection error: {str(e)}', 'done': True})}\n\n"

        response = StreamingHttpResponse(stream_generator(), content_type="text/event-stream")
        response['Cache-Control'] = 'no-cache'
        response['X-Accel-Buffering'] = 'no'
        return response

    # Non-streaming response
    try:
        ollama_resp = requests.post(
            f"{OLLAMA_BASE_URL}/api/chat",
            json=payload,
            timeout=180
        )
        if ollama_resp.status_code == 200:
            data = ollama_resp.json()
            message_obj = data.get("message", {})
            return JsonResponse({
                "status": "success",
                "model": model,
                "message": message_obj,
                "content": message_obj.get("content", ""),
                "thinking": message_obj.get("thinking", ""),
                "done": data.get("done", True),
                "total_duration": data.get("total_duration"),
                "eval_count": data.get("eval_count"),
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })
        elif ollama_resp.status_code == 404:
            return JsonResponse({
                "status": "model_not_found",
                "error": f"Model '{model}' was not found in your Ollama library.",
                "hint": f"Run `ollama pull {model}` in your terminal or install a local model, then refresh.",
                "model": model
            }, status=404)
        else:
            return JsonResponse({
                "status": "error",
                "error": f"Ollama returned HTTP {ollama_resp.status_code}: {ollama_resp.text}",
                "model": model
            }, status=ollama_resp.status_code)
    except requests.exceptions.RequestException as e:
        return JsonResponse({
            "status": "offline",
            "error": f"Could not connect to Ollama at {OLLAMA_BASE_URL}. Ensure Ollama is running.",
            "details": str(e)
        }, status=503)
