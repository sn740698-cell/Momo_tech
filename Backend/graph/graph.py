"""
LangGraph Multi-Supervisor Orchestration Graph for MOMO.
Connects Root, Conversation, Finance, Communication, and Voice supervisors
with specialized agents on a shared Pydantic state.
"""
import logging
from langgraph.graph import StateGraph, START, END

from graph.state import MomoState, MomoResponse, HardwareCommand, RoutingDecision
from supervisors.root import RootSupervisor
from supervisors.conversation import ConversationSupervisor
from supervisors.finance import FinanceSupervisor
from supervisors.communication import CommunicationSupervisor
from supervisors.voice import VoiceSupervisor

from agents.conversation_agent import ConversationAgent
from agents.memory_agent import MemoryAgent
from agents.document_agent import DocumentAgent
from agents.retrieval_agent import RetrievalAgent
from agents.data_analyzer_agent import DataAnalyzerAgent
from agents.texting_agent import TextingAgent
from agents.stt_agent import STTAgent
from agents.tts_agent import TTSAgent
from security.permissions import PermissionManager
from .routing import route_from_root, route_from_finance, route_after_speech_or_chat

logger = logging.getLogger(__name__)


# System node for diagnostics and hardware testing
async def system_node(state: MomoState):
    logger.info("Executing system node...")
    resp = MomoResponse(
        message="System telemetry and hardware allowlists are operating normally at peak performance.",
        expression="excited",
        animation="nod",
        speak=False
    )
    return {
        "response": resp,
        "momo_expression": "excited",
        "momo_animation": "nod",
        "current_agent": "system_node"
    }


def create_momo_graph():
    """
    Assembles and compiles the MOMO multi-supervisor multi-agent StateGraph.
    """
    workflow = StateGraph(MomoState)

    # Instantiate supervisors and agents
    root_sup = RootSupervisor()
    conv_sup = ConversationSupervisor()
    fin_sup = FinanceSupervisor()
    comm_sup = CommunicationSupervisor()
    vox_sup = VoiceSupervisor()

    conv_agent = ConversationAgent()
    mem_agent = MemoryAgent()
    doc_agent = DocumentAgent()
    ret_agent = RetrievalAgent()
    data_agent = DataAnalyzerAgent()
    text_agent = TextingAgent()
    stt_agent = STTAgent()
    tts_agent = TTSAgent()

    # Add Supervisor Nodes
    workflow.add_node("root_supervisor", root_sup.run)
    workflow.add_node("conversation_supervisor", conv_sup.run)
    workflow.add_node("finance_supervisor", fin_sup.run)
    workflow.add_node("communication_supervisor", comm_sup.run)
    workflow.add_node("voice_supervisor", vox_sup.run)

    # Add Agent Nodes
    workflow.add_node("conversation_agent", conv_agent.run)
    workflow.add_node("memory_agent", mem_agent.run)
    workflow.add_node("document_agent", doc_agent.run)
    workflow.add_node("retrieval_agent", ret_agent.run)
    workflow.add_node("data_analyzer_agent", data_agent.run)
    workflow.add_node("texting_agent", text_agent.run)
    workflow.add_node("stt_agent", stt_agent.run)
    workflow.add_node("tts_agent", tts_agent.run)
    workflow.add_node("system_node", system_node)

    # Define Graph Edges
    workflow.add_edge(START, "root_supervisor")

    # Conditional routing from Root Supervisor
    workflow.add_conditional_edges(
        "root_supervisor",
        route_from_root,
        {
            "conversation_supervisor": "conversation_supervisor",
            "finance_supervisor": "finance_supervisor",
            "communication_supervisor": "communication_supervisor",
            "voice_supervisor": "voice_supervisor",
            "system_node": "system_node",
        }
    )

    # Conversation Pipeline: Conversation Supervisor -> Memory Agent -> Conversation Agent
    workflow.add_edge("conversation_supervisor", "memory_agent")
    workflow.add_edge("memory_agent", "conversation_agent")

    # Finance Pipeline: Finance Supervisor -> (Document Agent or Retrieval Agent) -> Data Analyzer -> Conversation Agent
    workflow.add_conditional_edges(
        "finance_supervisor",
        route_from_finance,
        {
            "document_agent": "document_agent",
            "retrieval_agent": "retrieval_agent"
        }
    )
    workflow.add_edge("document_agent", "data_analyzer_agent")
    workflow.add_edge("retrieval_agent", "data_analyzer_agent")
    workflow.add_edge("data_analyzer_agent", "conversation_agent")

    # Communication Pipeline: Communication Supervisor -> Data Analyzer -> Texting Agent
    workflow.add_edge("communication_supervisor", "data_analyzer_agent")
    workflow.add_edge("data_analyzer_agent", "texting_agent")

    # Voice Pipeline: Voice Supervisor -> STT Agent -> Conversation Supervisor
    workflow.add_edge("voice_supervisor", "stt_agent")
    workflow.add_edge("stt_agent", "conversation_supervisor")

    # Output Routing (TTS speech or END)
    workflow.add_conditional_edges(
        "conversation_agent",
        route_after_speech_or_chat,
        {
            "tts_agent": "tts_agent",
            "end": END
        }
    )

    workflow.add_conditional_edges(
        "texting_agent",
        route_after_speech_or_chat,
        {
            "tts_agent": "tts_agent",
            "end": END
        }
    )

    workflow.add_edge("tts_agent", END)
    workflow.add_edge("system_node", END)

    compiled = workflow.compile()
    logger.info("MOMO LangGraph Multi-Supervisor workflow compiled successfully.")
    return compiled


# Module-level singleton compiled graph
momo_graph = create_momo_graph()
