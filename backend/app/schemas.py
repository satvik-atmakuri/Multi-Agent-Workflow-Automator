"""
Pydantic models for request/response validation.
"""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Dict, List, Literal, Any
from datetime import datetime

# ============================================================================
# Pydantic Models (API Request/Response)
# ============================================================================

class WorkflowRequest(BaseModel):
    """Request model for creating a new workflow"""
    text: str = Field(..., description="The user's request to process", min_length=10)
    skip_cache: bool = Field(default=False, description="Set to true to bypass semantic caching")
    
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [{
                "text": "Plan a 3-day trip to Paris for $1,500"
            }]
        }
    )


class WorkflowResponse(BaseModel):
    """Response model for workflow creation"""
    workflow_id: str
    status: str
    message: str = "Workflow created successfully"


class WorkflowStatusResponse(BaseModel):
    """Response model for workflow status queries"""
    workflow_id: str
    status: Literal["planning", "awaiting_clarification", "researching", 
                    "synthesizing", "validating", "completed", "failed"]
    state: Dict[str, Any]
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None
    final_output: Optional[Dict[str, Any]] = None


class ClarificationQuestion(BaseModel):
    """Model for a single clarification question"""
    id: str
    text: str
    category: str
    importance: Literal["high", "medium", "low"]
    default_assumption: str


class UserFeedbackRequest(BaseModel):
    """Request model for submitting user feedback"""
    responses: Dict[str, str] = Field(..., description="Question ID to answer mapping")
    ratings: Optional[Dict[str, int]] = Field(default_factory=dict, description="Question ID to rating (1-5) mapping")
    approval: Optional[Literal["approved", "needs_changes", "rejected"]] = "approved"
    additional_context: Optional[str] = None
    
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [{
                "responses": {
                    "q1": "I prefer direct flights",
                    "q2": "Mid-range hotel in city center"
                },
                "ratings": {
                    "q1": 5,
                    "q2": 4
                },
                "approval": "approved"
            }]
        }
    )


class UserFeedbackResponse(BaseModel):
    """Response model for feedback submission"""
    status: str
    message: str
    workflow_id: str


class ChatRequest(BaseModel):
    """Request model for chatting with a workflow"""
    message: str


class ChatResponse(BaseModel):
    """Response model for chat"""
    response: str
    history: List[Dict[str, str]]


# ============================================================================
# Workflow State Schema (for LangGraph)
# ============================================================================

from typing import TypedDict, NotRequired

class WorkflowState(TypedDict):
    """
    The state object that flows through all agents in the LangGraph workflow.
    This is the 'memory' of the workflow.
    """
    # Core identifiers
    workflow_id: str
    user_request: str
    status: Literal["planning", "awaiting_clarification", "researching", 
                    "synthesizing", "validating", "completed", "failed"]
    
    # Agent outputs
    planner_output: NotRequired[Optional[Dict[str, Any]]]
    clarification_questions: NotRequired[Optional[List[ClarificationQuestion]]]
    user_feedback: NotRequired[Optional[Dict[str, Any]]]
    user_approval: NotRequired[Optional[Literal["approved", "needs_changes", "rejected"]]]
    researcher_output: NotRequired[Optional[Dict[str, Any]]]
    synthesizer_output: NotRequired[Optional[Dict[str, Any]]]
    final_output: NotRequired[Optional[Dict[str, Any]]]
    validation_errors: NotRequired[List[Dict[str, Any]]]
    
    # Control flow
    retry_count: NotRequired[int]
    current_agent: NotRequired[Optional[str]]
    
    # Metadata
    user_preferences: NotRequired[Optional[Dict[str, str]]]
    created_at: str
    created_at: str
    updated_at: str
    chat_history: NotRequired[List[Dict[str, str]]]
    freshness_requirements: NotRequired[Optional[Dict[str, Any]]] # e.g. {"required": bool, "confidence": str}
