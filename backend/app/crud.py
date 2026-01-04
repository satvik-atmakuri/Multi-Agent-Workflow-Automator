"""
data access layer (CRUD) for database interactions.
"""
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import List, Optional, Dict, Any, Union
from uuid import UUID
from datetime import datetime

from app.models import Workflow, WorkflowStep, UserFeedback, QuestionAnalytics
from app.schemas import WorkflowRequest, WorkflowState

# ============================================================================
# Workflows
# ============================================================================

def create_workflow(db: Session, request: WorkflowRequest) -> Workflow:
    """Create a new workflow entry from a user request."""
    # Initialize empty state properly
    initial_state = {
        "workflow_id": "",  # Will update after ID generation if needed, or rely on return
        "user_request": request.text,
        "status": "planning",
        "retry_count": 0,
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat()
    }
    
    db_workflow = Workflow(
        user_request=request.text,
        status="planning",
        state=initial_state,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db.add(db_workflow)
    db.commit()
    db.refresh(db_workflow)
    
    # Update state with the generated ID
    # Note: We do this because WorkflowState model needs the ID
    updated_state = db_workflow.state.copy()
    updated_state["workflow_id"] = str(db_workflow.id)
    db_workflow.state = updated_state
    db.commit()
    
    return db_workflow

def get_workflow(db: Session, workflow_id: UUID) -> Optional[Workflow]:
    """Get a workflow by ID."""
    return db.query(Workflow).filter(Workflow.id == workflow_id).first()

def update_workflow_status(db: Session, workflow_id: UUID, status: str) -> Optional[Workflow]:
    """Update just the status of a workflow."""
    workflow = get_workflow(db, workflow_id)
    if workflow:
        workflow.status = status
        workflow.updated_at = datetime.utcnow()
        if status in ["completed", "failed"]:
            workflow.completed_at = datetime.utcnow()
        db.commit()
        db.refresh(workflow)
    return workflow

def update_workflow_state(db: Session, workflow_id: UUID, state: Dict[str, Any]) -> Optional[Workflow]:
    """Update the LangGraph state of a workflow."""
    workflow = get_workflow(db, workflow_id)
    if workflow:
        workflow.state = state
        workflow.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(workflow)
    return workflow

# ============================================================================
# Workflow Steps
# ============================================================================

def log_workflow_step(db: Session, step_data: Dict[str, Any]) -> WorkflowStep:
    """Log a completed step in the workflow."""
    step = WorkflowStep(**step_data)
    db.add(step)
    db.commit()
    db.refresh(step)
    return step

def get_workflow_steps(db: Session, workflow_id: UUID) -> List[WorkflowStep]:
    """Get all steps for a specific workflow, ordered by execution time."""
    return db.query(WorkflowStep)\
        .filter(WorkflowStep.workflow_id == workflow_id)\
        .order_by(WorkflowStep.executed_at.asc())\
        .all()

# ============================================================================
# User Feedback
# ============================================================================

def create_feedback(db: Session, 
                   workflow_id: UUID, 
                   request_data: Any, # UserFeedbackRequest
                   questions: Dict[str, Any]) -> UserFeedback:
    """Record user feedback."""
    feedback = UserFeedback(
        workflow_id=workflow_id,
        questions=questions,
        responses=request_data.responses,
        question_ratings=request_data.ratings,
        approval_status=request_data.approval,
        submitted_at=datetime.utcnow()
    )
    db.add(feedback)
    db.commit()
    db.refresh(feedback)
    return feedback

# ============================================================================
# Analytics
# ============================================================================

def log_question_analytics(db: Session, 
                         question_text: str, 
                         category: str,
                         helpful_rating: int = None) -> None:
    """Update analytics for a clarification question."""
    # Try to find existing question
    # This is a simple implementation; in production could check fuzzy matches
    q_stats = db.query(QuestionAnalytics)\
        .filter(QuestionAnalytics.question_text == question_text)\
        .first()
        
    if not q_stats:
        q_stats = QuestionAnalytics(
            question_text=question_text,
            question_category=category,
            times_asked=0,
            times_helpful=0
        )
        db.add(q_stats)
    
    q_stats.times_asked += 1
    q_stats.last_used = datetime.utcnow()
    
    if helpful_rating and helpful_rating >= 4:
        q_stats.times_helpful += 1
        
    db.commit()
