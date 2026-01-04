from fastapi import APIRouter, BackgroundTasks, HTTPException, Request, status, Depends
from typing import Dict, Any, List, Optional
import uuid
import logging
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from app.schemas import (
    WorkflowRequest, 
    WorkflowResponse, 
    WorkflowStatusResponse,
    UserFeedbackRequest,
    UserFeedbackResponse,
    ChatRequest,
    ChatResponse
)
from app.database import get_db
from app.models import Workflow, UserPreference
from app.services.caching import SemanticCache

router = APIRouter()
logger = logging.getLogger(__name__)

async def run_workflow_background(app, workflow_id: str, input_data: Dict[str, Any], config: Dict[str, Any], db: AsyncSession):
    """
    Helper to run the workflow in the background.
    """
    logger.info(f"▶️ Starting background workflow execution for {workflow_id}")
    try:
        # Check if workflow exists in state
        if not hasattr(app.state, "workflow") or app.state.workflow is None:
            logger.error("❌ Workflow graph not initialized")
            return

        # Fetch User Preferences
        stmt = select(UserPreference)
        result = await db.execute(stmt)
        prefs = {row.key: row.value for row in result.scalars().all()}
        
        # Inject preferences into input
        if prefs:
            input_data["user_preferences"] = prefs
            logger.info(f"🧠 Injected {len(prefs)} user preferences")

        # Invoke the graph
        await app.state.workflow.ainvoke(input_data, config=config)
        
        # Update completion status in DB (Optional, LangGraph persistence handles state, but we want our table updated)
        # We can't easily do this here without a reliable callback or checking state after invoke returns (it returns state)
        # Actually ainvoke returns the final state!
        final_state = await app.state.workflow.ainvoke(input_data, config=config)
        
        # Capture Final Output in Chat History
        # This ensures it appears chronologically after user feedback
        if final_state.get("status") == "completed" and final_state.get("final_output"):
             current_history = final_state.get("chat_history", [])
             
             # Check if we already added it (to avoid duplicates on retries)
             # Simple check: is the last message identical to final_output?
             is_duplicate = False
             if current_history:
                 last_msg = current_history[-1]
                 if last_msg.get("role") == "assistant" and last_msg.get("content") == str(final_state.get("final_output")):
                     is_duplicate = True
                     
             if not is_duplicate:
                 # Format if it's a dict
                 content = final_state.get("final_output")
                 if isinstance(content, dict):
                     # Extract the actual value if possible
                     if "response" in content:
                         content = content["response"]
                     elif "summary" in content:
                         content = content["summary"]
                     else:
                         content = str(content) # Fallback to stringified dict
                     
                 current_history.append({"role": "assistant", "content": content})
                 final_state["chat_history"] = current_history

        # Update Workflow table
        await db.execute(
            update(Workflow)
            .where(Workflow.id == uuid.UUID(workflow_id))
            .values(
                status=final_state.get("status", "completed"),
                completed_at=datetime.utcnow() if final_state.get("status") == "completed" else None,
                final_output=final_state.get("final_output"),
                state=final_state
            )
        )
        await db.commit()
        
        logger.info(f"✅ Background workflow execution finished for {workflow_id}")
        
    except Exception as e:
        logger.error(f"❌ Error in background workflow {workflow_id}: {e}")
        # Mark as failed in DB
        try:
             await db.execute(
                update(Workflow)
                .where(Workflow.id == uuid.UUID(workflow_id))
                .values(status="failed")
            )
             await db.commit()
        except:
            pass

@router.get("/", response_model=List[WorkflowStatusResponse])
async def list_workflows(db: AsyncSession = Depends(get_db)):
    """
    List all past workflows (History).
    """
    stmt = select(Workflow).order_by(Workflow.created_at.desc())
    result = await db.execute(stmt)
    workflows = result.scalars().all()
    
    return [
        WorkflowStatusResponse(
            workflow_id=str(w.id),
            status=w.status,
            state=w.state,
            created_at=w.created_at,
            updated_at=w.updated_at,
            completed_at=w.completed_at,
            final_output=w.final_output
        ) for w in workflows
    ]

@router.post("/", response_model=WorkflowResponse, status_code=status.HTTP_201_CREATED)
async def create_workflow(
    request: WorkflowRequest, 
    background_tasks: BackgroundTasks,
    req: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Start a new workflow with the given user request. Checks cache first.
    """
    cache_service = SemanticCache(db)
    
    # 1. Check Cache
    if not request.skip_cache:
        cached_workflow = await cache_service.find_similar_workflow(request.text, threshold=0.95)
        
        if cached_workflow:
            logger.info(f"✨ Validation Hit! Reusing result from {cached_workflow.id}")
            return WorkflowResponse(
                workflow_id=str(cached_workflow.id),
                status="completed",
                message="Result retrieved from cache (High Similarity Found)"
            )
    else:
        logger.info("⏩ Cache skipped by request")

    # 2. Create new Workflow
    workflow_id = str(uuid.uuid4())
    logger.info(f"Create workflow request: {workflow_id}")
    
    # Generate embedding for the new request
    embedding = await cache_service.get_embedding(request.text)
    
    # Initial state
    initial_state = {
        "workflow_id": workflow_id,
        "user_request": request.text,
        "status": "planning",
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat()
    }
    
    # Persist initial record to DB
    new_workflow = Workflow(
        id=uuid.UUID(workflow_id),
        user_request=request.text,
        request_embedding=embedding,
        status="planning",
        state=initial_state
    )
    db.add(new_workflow)
    await db.commit()
    
    # LangGraph config
    config = {"configurable": {"thread_id": workflow_id}}
    
    # Run in background
    # Note: We need a new session for the background task because the current one closes
    # But BackgroundTasks doesn't easily support async session injection.
    # Pattern: Pass the `run_workflow_background` a way to create a session, or handle session inside.
    # Simplest for now: The helper needs to create its own session or we pass the app and it uses a scoped session factory.
    # Given our setup, let's instantiate the session inside the background function if possible, or pass the session_maker.
    
    # Actually, we can't pass the `db` session as it will be closed.
    # We'll rely on the background task to create its own session.
    # We need to refactor `run_workflow_background` to create a session.
    
    background_tasks.add_task(
        run_workflow_background_wrapper, 
        req.app, 
        workflow_id, 
        initial_state, 
        config
    )
    
    return WorkflowResponse(
        workflow_id=workflow_id,
        status="started",
        message="Workflow initialized and running in background"
    )

async def run_workflow_background_wrapper(app, workflow_id, input_data, config):
    """Wrapper to handle DB session for background task"""
    from app.database import AsyncSessionLocal
    async with AsyncSessionLocal() as session:
        await run_workflow_background(app, workflow_id, input_data, config, session)


@router.get("/{workflow_id}", response_model=WorkflowStatusResponse)
async def get_workflow_status(workflow_id: str, req: Request, db: AsyncSession = Depends(get_db)):
    """
    Get status. Tries DB first (faster), falls back to LangGraph state.
    """
    # Try DB first
    stmt = select(Workflow).where(Workflow.id == uuid.UUID(workflow_id))
    result = await db.execute(stmt)
    workflow = result.scalar_one_or_none()
    
    if workflow:
        return WorkflowStatusResponse(
            workflow_id=str(workflow.id),
            status=workflow.status,
            state=workflow.state,
            created_at=workflow.created_at,
            updated_at=workflow.updated_at,
            completed_at=workflow.completed_at,
            final_output=workflow.final_output
        )

    # Fallback to LangGraph (Original Logic)
    if not hasattr(req.app.state, "workflow"):
        raise HTTPException(status_code=500, detail="Workflow system not initialized")
        
    config = {"configurable": {"thread_id": workflow_id}}
    
    try:
        snapshot = await req.app.state.workflow.aget_state(config)
        
        if not snapshot:
             raise HTTPException(status_code=404, detail="Workflow not found")

        state = snapshot.values
        if not state:
             raise HTTPException(status_code=404, detail="Workflow state not found")

        return WorkflowStatusResponse(
            workflow_id=state.get("workflow_id", workflow_id),
            status=state.get("status", "failed"),
            state=state, 
            created_at=datetime.fromisoformat(state.get("created_at", datetime.utcnow().isoformat())),
            updated_at=datetime.fromisoformat(state.get("updated_at", datetime.utcnow().isoformat())),
            completed_at=None,
            final_output=state.get("final_output")
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{workflow_id}/feedback", response_model=UserFeedbackResponse)
async def submit_feedback(
    workflow_id: str,
    feedback: UserFeedbackRequest,
    background_tasks: BackgroundTasks,
    req: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Submit feedback/answers to clarification questions.
    """
    logger.info(f"POST /feedback called for {workflow_id}")
    print(f"DEBUG: Feedback Payload: {feedback}") # Explicit print for debugging
    config = {"configurable": {"thread_id": workflow_id}}
    
    input_update = {
        "user_feedback": feedback.model_dump(),
        "status": "planning", 
        "planner_output": None 
    }
    
    # Also append to chat history for continuity
    stmt = select(Workflow).where(Workflow.id == uuid.UUID(workflow_id))
    result = await db.execute(stmt)
    workflow = result.scalar_one_or_none()
    
    if workflow:
        current_history = workflow.state.get("chat_history", [])
        # Format the feedback response nicely
        response_text = feedback.responses.get("clarification", str(feedback.responses))
        current_history.append({"role": "user", "content": response_text})
        
        # We need to update the state in the DB immediately so polling sees it, 
        # or rely on the background task to do it? 
        # Background task takes `input_update` and passes it to `ainvoke`.
        # LangGraph usually merges input into state.
        # But `chat_history` might not be a top-level input for the planner?
        # Let's check our Graph state schema. `chat_history` is not explicitly in `WorkflowState` TypedDict!
        # It's treating it as metadata in `api/chat`. 
        
        # We should add `chat_history` to `input_update` so LangGraph persists it?
        # Or just update it via DB here? 
        # Since we are using `run_workflow_background`, we are passing `input_update` to `ainvoke`.
        # If `chat_history` isn't in `WorkflowState`, `ainvoke` might ignore it or treating it access extra?
        
        # Let's just update the DB object's state directly here for the UI to see it immediately.
        state = workflow.state
        state["chat_history"] = current_history
        
        # update the db state for immediate UI feedback
        await db.execute(
            update(Workflow)
            .where(Workflow.id == uuid.UUID(workflow_id))
            .values(state=state)
        )
        await db.commit()

        # CRITICAL: Also pass this updated history to LangGraph input
        # so it gets merged into the persistent checkpoint state.
        # Otherwise, LangGraph will overwrite our manual DB update with its old state.
        input_update["chat_history"] = current_history
    
    
    background_tasks.add_task(
        run_workflow_background_wrapper,
        req.app,
        workflow_id,
        input_update,
        config
    )
    
    return UserFeedbackResponse(
        workflow_id=workflow_id,
        status="resumed",
        message="Feedback received, workflow resuming"
    )

@router.post("/{workflow_id}/chat", response_model=ChatResponse)
async def chat_with_workflow(
    workflow_id: str,
    chat_req: ChatRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Chat with the completed (or running) workflow.
    Uses the current state as context.
    """
    # 1. Fetch Workflow
    stmt = select(Workflow).where(Workflow.id == uuid.UUID(workflow_id))
    result = await db.execute(stmt)
    workflow = result.scalar_one_or_none()
    
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
        
    state = workflow.state
    
    # 2. Prepare Context from State
    context_parts = []
    if state.get("user_request"):
        context_parts.append(f"Original Request: {state['user_request']}")
    
    if state.get("planner_output"):
        context_parts.append(f"Plan: {state['planner_output']}")
        
    if state.get("researcher_output"):
        context_parts.append(f"Research Data: {state['researcher_output']}")
        
    if state.get("final_output"):
        context_parts.append(f"Final Result: {state['final_output']}")
        
    context_str = "\n\n".join(context_parts)
    
    # 3. Handle History
    chat_history = state.get("chat_history", [])
    
    # 4. Call LLM
    from langchain_openai import ChatOpenAI
    from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
    
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.7)
    
    messages = [
        SystemMessage(content=f"""You are a helpful assistant discussing a specific workflow execution. 
Use the following context to answer the user's questions. 
If the answer is in the context, be precise. If not, you can use your general knowledge but mention that it wasn't part of the specific workflow results.

CONTEXT:
{context_str}
""")
    ]
    
    # Add history
    for msg in chat_history:
        if msg["role"] == "user":
            messages.append(HumanMessage(content=msg["content"]))
        else:
            messages.append(AIMessage(content=msg["content"]))
            
    # Add current message
    messages.append(HumanMessage(content=chat_req.message))
    
    response = await llm.ainvoke(messages)
    reply = response.content
    
    # 5. Update History & Persist
    chat_history.append({"role": "user", "content": chat_req.message})
    chat_history.append({"role": "assistant", "content": reply})
    
    # Update local state obj
    state["chat_history"] = chat_history
    workflow.state = state
    
    # Save to DB
    # Note: We are modifying the 'state' JSON column directly.
    # LangGraph checkpointing is separate, but this is fine for metadata/chat.
    await db.execute(
        update(Workflow)
        .where(Workflow.id == uuid.UUID(workflow_id))
        .values(state=state)
    )
    await db.commit()
    
    return ChatResponse(
        response=reply,
        history=chat_history
    )
