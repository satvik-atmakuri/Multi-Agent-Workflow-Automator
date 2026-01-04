import pytest
from unittest.mock import MagicMock, patch
from app.orchestrator.graph import build_graph, route_planner_output
from app.schemas import WorkflowState

# Mock agents to avoid API calls or importing them fully
@patch("app.orchestrator.graph.planner")
@patch("app.orchestrator.graph.researcher")
@patch("app.orchestrator.graph.clarification_agent")
@patch("app.orchestrator.graph.synthesizer")
def test_graph_construction(mock_syn, mock_clar, mock_res, mock_plan):
    graph = build_graph()
    assert graph is not None

def test_route_planner_clarification():
    state = WorkflowState(
        workflow_id="1", user_request="test", status="planning", 
        created_at="now", updated_at="now",
        planner_output={"clarification_needed": True}
    )
    result = route_planner_output(state)
    assert result == "clarification"

def test_route_planner_research():
    state = WorkflowState(
        workflow_id="1", user_request="test", status="planning", 
        created_at="now", updated_at="now",
        planner_output={"clarification_needed": False}
    )
    result = route_planner_output(state)
    assert result == "researcher"
