import pytest
from unittest.mock import MagicMock, patch
from app.agents.clarification import ClarificationAgent
from app.schemas import WorkflowState, ClarificationQuestion

def test_clarification_instantiation():
    with patch("app.agents.base.ChatOpenAI"):
        agent = ClarificationAgent()
        assert agent.name == "ClarificationAgent"
        assert agent.parser is not None

# NOTE: Similar to Planner, functional testing requires mocking the chain.
# We trust the structure for now and verify imports.
