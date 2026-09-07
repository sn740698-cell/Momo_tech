"""
Base Workflow Agent Interface for MOMO.
Enforces modular design, clear input/state contracts, and partial state returns.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any
import logging

from ai_workflow.state import WorkflowState

logger = logging.getLogger(__name__)


class BaseWorkflowAgent(ABC):
    """
    Standard interface for all workflow agents.
    Each agent inspects state and returns a dictionary with partial state updates.
    """

    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    async def execute(self, state: WorkflowState) -> Dict[str, Any]:
        """
        Executes the agent's specific responsibility.
        Must return a dict of partial state updates to merge into WorkflowState.
        """
        pass

    async def run(self, state: WorkflowState) -> Dict[str, Any]:
        """
        Wrapper that logs execution start and finish with exception handling.
        """
        logger.info(f"[{self.name}] Beginning execution for execution_id='{state.execution_id}'...")
        try:
            updates = await self.execute(state)
            logger.info(f"[{self.name}] Completed successfully.")
            return updates
        except Exception as e:
            logger.error(f"[{self.name}] Error during execution: {e}", exc_info=True)
            return {
                "errors": [f"Agent '{self.name}' failed: {str(e)}"]
            }
