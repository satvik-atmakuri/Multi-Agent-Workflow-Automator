"""
Base abstract class for all agents in the system.
Enforces a standard interface for invoking agents via LangGraph.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from app.config import settings
from app.schemas import WorkflowState

class BaseAgent(ABC):
    """
    Abstract base class for all agents.
    """
    
    def __init__(self, model_name: str = settings.DEFAULT_MODEL, temperature: float = 0):
        """
        Initialize the agent with an LLM client.
        """
        self.llm = ChatOpenAI(
            model=model_name,
            temperature=temperature,
            api_key=settings.OPENAI_API_KEY,
            max_tokens=settings.MAX_TOKENS
        )
        self.name = self.__class__.__name__

    @abstractmethod
    def invoke(self, state: WorkflowState) -> dict:
        """
        Main entry point for the agent.
        
        Args:
            state: The current state of the workflow.
            
        Returns:
            A dictionary of updates into the state.
            e.g. {"planner_output": {...}, "status": "researching"}
        """
        pass

    def get_llm(self):
        """Return the configured LLM instance."""
        return self.llm
