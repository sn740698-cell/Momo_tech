"""
Conditional routing functions for the LangGraph MOMO workflow.
"""
from graph.state import MomoState


def route_from_root(state: MomoState) -> str:
    route = state.current_route or "conversation"
    if route == "finance":
        return "finance_supervisor"
    elif route == "communication":
        return "communication_supervisor"
    elif route == "voice":
        return "voice_supervisor"
    elif route == "system":
        return "system_node"
    return "conversation_supervisor"


def route_from_finance(state: MomoState) -> str:
    if state.metadata.get("upload_queue"):
        return "document_agent"
    return "retrieval_agent"


def route_after_speech_or_chat(state: MomoState) -> str:
    if state.response and state.response.speak:
        return "tts_agent"
    return "end"
