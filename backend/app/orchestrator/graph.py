"""
LangGraph workflow definition for the Multi-Agent System.
"""
from typing import Dict, Any,  Literal
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.base import BaseCheckpointSaver

from app.schemas import WorkflowState
from app.agents.planner import PlannerAgent
from app.agents.researcher import ResearcherAgent
from app.agents.synthesizer import SynthesizerAgent
from app.orchestrator.validator import validator_node

# Initialize Agents
planner = PlannerAgent()
researcher = ResearcherAgent()
synthesizer = SynthesizerAgent()

# ============================================================================
# Node Definitions
# ============================================================================

def planner_node(state: WorkflowState) -> Dict[str, Any]:
    """Execute the Planner Agent."""
    return planner.invoke(state)

def researcher_node(state: WorkflowState) -> Dict[str, Any]:
    """Execute the Researcher Agent."""
    return researcher.invoke(state)

def synthesizer_node(state: WorkflowState) -> Dict[str, Any]:
    """Execute the Synthesizer Agent."""
    return synthesizer.invoke(state)

# ============================================================================
# Conditional Logic
# ============================================================================

def route_planner_output(state: WorkflowState) -> Literal["end_clarification", "researcher"]:
    """
    Determine the next node based on the Planner's output.
    """
    output = state.get('planner_output')
    if output and output.get("clarification_needed"):
        return "end_clarification"
    return "researcher"

# ============================================================================
# Graph Construction
# ============================================================================

def build_graph(checkpointer: BaseCheckpointSaver = None):
    """
    Build and compile the StateGraph.
    """
    workflow = StateGraph(WorkflowState)

    # Add validator node

    workflow.add_node("planner", planner_node)
    workflow.add_node("researcher", researcher_node)
    workflow.add_node("synthesizer", synthesizer_node)
    workflow.add_node("validator", validator_node)

    # Add Edges
    workflow.set_entry_point("planner")

    # Conditional Edge from Planner
    workflow.add_conditional_edges(
        "planner",
        route_planner_output,
        {
            "end_clarification": END,
            "researcher": "researcher"
        }
    )

    # Researcher -> Synthesizer -> Validator -> END
    workflow.add_edge("researcher", "synthesizer")
    workflow.add_edge("synthesizer", "validator")
    workflow.add_edge("validator", END)

    # Compile
    app = workflow.compile(checkpointer=checkpointer)
    return app
