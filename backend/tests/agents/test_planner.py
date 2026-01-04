import pytest
from unittest.mock import MagicMock, patch
from app.agents.planner import PlannerAgent
from app.schemas import WorkflowState

def test_planner_instantiation():
    with patch("app.agents.base.ChatOpenAI"):
        agent = PlannerAgent()
        assert agent.name == "PlannerAgent"
        assert agent.parser is not None
        assert agent.prompt is not None

# Functional testing of LangChain chains usually requires `langchain-core` testing utils 
# or Integration Tests. We will stick to instantiation tests for now to verify imports/syntax.


