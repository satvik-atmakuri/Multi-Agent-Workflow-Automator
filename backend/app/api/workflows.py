from fastapi import APIRouter, BackgroundTasks, HTTPException, Request, status, Depends
from typing import Dict, Any, List
import uuid
import logging
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete

from app.schemas import (
    WorkflowRequest,
    WorkflowResponse,
    WorkflowStatusResponse,
    UserFeedbackRequest,
    UserFeedbackResponse,
    ChatRequest,
    ChatResponse,
)
from app.database import get_db
from app.models import Workflow, UserPreference
from app.services.caching import SemanticCache

router = APIRouter()
logger = logging.getLogger(__name__)


def _to_uuid(workflow_id: str) -> uuid.UUID:
    """Parse workflow_id safely and raise HTTP 400 if invalid."""
    try:
        return uuid.UUID(workflow_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid workflow ID format")


async def run_workflow_background(
    app,
    workflow_id: str,
    input_data: Dict[str, Any],
    config: Dict[str, Any],
    db: AsyncSession,
):
    """
    Helper to run the workflow in the background.
    """
    logger.info(f"▶️ Starting background workflow execution for {workflow_id}")

    try:
        if not hasattr(app.state, "workflow") or app.state.workflow is None:
            logger.error("❌ Workflow graph not initialized")
            return

        # Fetch user preferences
        stmt = select(UserPreference)
        result = await db.execute(stmt)
        prefs = {row.key: row.value for row in result.scalars().all()}

        if prefs:
            input_data["user_preferences"] = prefs
            logger.info(f"🧠 Injected {len(prefs)} user preferences")

        # ✅ Invoke ONCE (LangGraph returns final state)
        final_state = await app.state.workflow.ainvoke(input_data, config=config)

        # Keep timestamps consistent in the persisted state
        final_state["updated_at"] = datetime.utcnow().isoformat()

        # Append assistant response to chat_history if completed
        if final_state.get("status") == "completed" and final_state.get("final_output"):
            current_history = final_state.get("chat_history", [])

            content = final_state.get("final_output")
            if isinstance(content, dict):
                if "response" in content:
                    content = content["response"]
                elif "summary" in content:
                    content = content["summary"]
                else:
                    content = str(content)

            # Avoid duplicate final output in history
            is_duplicate = False
            if current_history:
                last_msg = current_history[-1]
                if last_msg.get("role") == "assistant" and last_msg.get("content") == str(content):
                    is_duplicate = True

            if not is_duplicate:
                current_history.append({"role": "assistant", "content": str(content)})
                final_state["chat_history"] = current_history

        # Update DB
        wf_uuid = _to_uuid(workflow_id)
        await db.execute(
            update(Workflow)
            .where(Workflow.id == wf_uuid)
            .values(
                status=final_state.get("status", "completed"),
                updated_at=datetime.utcnow(),
                completed_at=datetime.utcnow() if final_state.get("status") == "completed" else None,
                final_output=final_state.get("final_output"),
                state=final_state,
            )
        )
        await db.commit()

        logger.info(f"✅ Background workflow execution finished for {workflow_id}")

    except Exception as e:
        logger.error(f"❌ Error in background workflow {workflow_id}: {e}")

        # Mark as failed in DB + store error in state for UI visibility
        try:
            wf_uuid = _to_uuid(workflow_id)

            stmt = select(Workflow).where(Workflow.id == wf_uuid)
            res = await db.execute(stmt)
            wf = res.scalar_one_or_none()

            state = (wf.state if wf else {}) or {}
            state["status"] = "failed"
            state["error"] = str(e)
            state["updated_at"] = datetime.utcnow().isoformat()

            await db.execute(
                update(Workflow)
                .where(Workflow.id == wf_uuid)
                .values(status="failed", updated_at=datetime.utcnow(), state=state)
            )
            await db.commit()
        except Exception:
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
            final_output=w.final_output,
        )
        for w in workflows
    ]


@router.post("/", response_model=WorkflowResponse, status_code=status.HTTP_201_CREATED)
async def create_workflow(
    request: WorkflowRequest,
    background_tasks: BackgroundTasks,
    req: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Start a new workflow with the given user request. Checks cache first.
    """
    cache_service = SemanticCache(db)

    # 1) Check cache
    if not request.skip_cache:
        cached_workflow = await cache_service.find_similar_workflow(request.text, threshold=0.95)
        if cached_workflow:
            logger.info(f"✨ Validation Hit! Reusing result from {cached_workflow.id}")
            return WorkflowResponse(
                workflow_id=str(cached_workflow.id),
                status="completed",
                message="Result retrieved from cache (High Similarity Found)",
            )
    else:
        logger.info("⏩ Cache skipped by request")

    # 2) Create workflow
    workflow_id = str(uuid.uuid4())
    logger.info(f"Create workflow request: {workflow_id}")

    embedding = await cache_service.get_embedding(request.text)

    # Keep chat history from the start (helps frontend chat UI)
    now_iso = datetime.utcnow().isoformat()
    initial_state: Dict[str, Any] = {
        "workflow_id": workflow_id,
        "user_request": request.text,
        "status": "planning",
        "created_at": now_iso,
        "updated_at": now_iso,
        "chat_history": [{"role": "user", "content": request.text}],
    }

    new_workflow = Workflow(
        id=uuid.UUID(workflow_id),
        user_request=request.text,
        request_embedding=embedding,
        status="planning",
        state=initial_state,
    )
    db.add(new_workflow)
    await db.commit()

    config = {"configurable": {"thread_id": workflow_id, "db": db}}

    background_tasks.add_task(
        run_workflow_background_wrapper,
        req.app,
        workflow_id,
        initial_state,
        config,
    )

    return WorkflowResponse(
        workflow_id=workflow_id,
        status="started",
        message="Workflow initialized and running in background",
    )


async def run_workflow_background_wrapper(app, workflow_id, input_data, config):
    """Wrapper to handle DB session for background task."""
    from app.database import AsyncSessionLocal

    async with AsyncSessionLocal() as session:
        config["configurable"]["db"] = session
        await run_workflow_background(app, workflow_id, input_data, config, session)


@router.get("/{workflow_id}", response_model=WorkflowStatusResponse)
async def get_workflow_status(workflow_id: str, req: Request, db: AsyncSession = Depends(get_db)):
    """
    Get status. Tries DB first (faster), falls back to LangGraph state.
    """
    wf_uuid = _to_uuid(workflow_id)

    # DB first
    stmt = select(Workflow).where(Workflow.id == wf_uuid)
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
            final_output=workflow.final_output,
        )

    # Fallback to LangGraph state
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

        def _dt_from_state(key: str) -> datetime:
            try:
                return datetime.fromisoformat(state.get(key))
            except Exception:
                return datetime.utcnow()

        return WorkflowStatusResponse(
            workflow_id=state.get("workflow_id", workflow_id),
            status=state.get("status", "failed"),
            state=state,
            created_at=_dt_from_state("created_at"),
            updated_at=_dt_from_state("updated_at"),
            completed_at=None,
            final_output=state.get("final_output"),
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
    db: AsyncSession = Depends(get_db),
):
    """
    Submit feedback/answers to clarification questions.
    """
    logger.info(f"POST /feedback called for {workflow_id}")
    print(f"DEBUG: Feedback Payload: {feedback}")

    wf_uuid = _to_uuid(workflow_id)
    config = {"configurable": {"thread_id": workflow_id, "db": db}}

    input_update: Dict[str, Any] = {
        "user_feedback": feedback.model_dump(),
        "status": "planning",
        "planner_output": None,
    }

    stmt = select(Workflow).where(Workflow.id == wf_uuid)
    result = await db.execute(stmt)
    workflow = result.scalar_one_or_none()

    if workflow:
        current_history = (workflow.state or {}).get("chat_history", [])
        response_text = feedback.responses.get("clarification", str(feedback.responses))
        current_history.append({"role": "user", "content": response_text})

        # ✅ Merge clarification into user_request so downstream agents see it
        clarified_request = f"{workflow.user_request}\nUser clarification: {response_text}"
        input_update["user_request"] = clarified_request

        # ✅ Update DB state immediately (for UI polling)
        state = workflow.state or {}
        state["chat_history"] = current_history
        state["user_request"] = clarified_request
        state["status"] = "planning"
        state["updated_at"] = datetime.utcnow().isoformat()

        await db.execute(
            update(Workflow)
            .where(Workflow.id == wf_uuid)
            .values(status="planning", updated_at=datetime.utcnow(), state=state)
        )
        await db.commit()

        # ✅ IMPORTANT: keep LangGraph checkpoint state in sync
        input_update["chat_history"] = current_history

    background_tasks.add_task(
        run_workflow_background_wrapper,
        req.app,
        workflow_id,
        input_update,
        config,
    )

    return UserFeedbackResponse(
        workflow_id=workflow_id,
        status="resumed",
        message="Feedback received, workflow resuming",
    )


@router.post("/{workflow_id}/chat", response_model=ChatResponse)
async def chat_with_workflow(
    workflow_id: str,
    chat_req: ChatRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Chat with the completed (or running) workflow.
    Uses the current state as context.
    """
    wf_uuid = _to_uuid(workflow_id)

    stmt = select(Workflow).where(Workflow.id == wf_uuid)
    result = await db.execute(stmt)
    workflow = result.scalar_one_or_none()

    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")

    state = workflow.state or {}

    # Prepare context from state
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

    chat_history = state.get("chat_history", [])

    from langchain_openai import ChatOpenAI
    from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.7)

    messages = [
        SystemMessage(
            content=(
                "You are a helpful assistant discussing a specific workflow execution.\n"
                "Use the following context to answer the user's questions.\n"
                "If the answer is in the context, be precise. If not, you can use your general knowledge "
                "but mention that it wasn't part of the specific workflow results.\n\n"
                f"CONTEXT:\n{context_str}\n"
            )
        )
    ]

    for msg in chat_history:
        if msg.get("role") == "user":
            messages.append(HumanMessage(content=msg.get("content", "")))
        else:
            messages.append(AIMessage(content=msg.get("content", "")))

    messages.append(HumanMessage(content=chat_req.message))

    response = await llm.ainvoke(messages)
    reply = response.content

    # Update history & persist
    chat_history.append({"role": "user", "content": chat_req.message})
    chat_history.append({"role": "assistant", "content": reply})

    state["chat_history"] = chat_history
    state["updated_at"] = datetime.utcnow().isoformat()

    await db.execute(
        update(Workflow)
        .where(Workflow.id == wf_uuid)
        .values(updated_at=datetime.utcnow(), state=state)
    )
    await db.commit()

    return ChatResponse(response=reply, history=chat_history)


@router.delete("/{workflow_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_workflow(workflow_id: str, db: AsyncSession = Depends(get_db)):
    """
    Delete a workflow by ID.
    """
    wf_uuid = _to_uuid(workflow_id)

    try:
        stmt = delete(Workflow).where(Workflow.id == wf_uuid)
        result = await db.execute(stmt)
        await db.commit()

        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Workflow not found")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting workflow: {e}")
        raise HTTPException(status_code=500, detail=str(e))
