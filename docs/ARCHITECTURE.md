# Architecture

This document details the internal design of the Multi-Agent Workflow Automator, focusing on the state management, agent orchestration, and validation logic.

## 🧠 State Schema

The core of the system is the `WorkflowState` maintained in `backend/app/orchestrator/graph.py`. This TypedDict moves through the LangGraph nodes.

```python
class WorkflowState(TypedDict):
    user_request: str           # The original (or clarified) user query
    planner_output: dict        # Structured plan (Goal, Steps, Requirements)
    researcher_output: dict     # Aggregated search results (Web/News)
    final_output: str           # The synthesized Markdown response
    clarification_needed: bool  # Flag to trigger the feedback loop
    clarification_question: str # The question asking the user for details
    user_feedback: dict         # User's response to clarification
    chat_history: list          # Chronological conversation log
```

## 🔄 Clarification Loop

The system is designed to never guess intent. It uses a **Human-in-the-Loop** pattern:

1.  **Planner Node**: Analyzes `user_request`. If ambiguous (missing dates, budget, location), it sets `clarification_needed=True`.
2.  **Router**: Conditional edge in `graph.py` detects this flag.
    -   If `True` -> Transitions to **End** (Wait for Feedback).
    -   State is persisted in Postgres with `thread_id` = `workflow_id`.
3.  **User Action**: User sees the question and replies via `POST /api/workflows/{id}/feedback`.
4.  **Resumption**: The backend updates `user_request` with the new context and re-invokes the graph. The Planner runs again with the full context.

## ⚡ Freshness & Validation

The **Validator Node** acts as the quality gatekeeper before delivering results.

-   **Logic**: Located in `backend/app/orchestrator/validator.py`.
-   **Freshness Check**:
    -   If the query implies "news", "current", or "price", the validator checks for at least **2 unique, reachable HTTP sources**.
    -   Tests URLs using `HEAD` requests to ensure they aren't 404s.
-   **Outcome**:
    -   **Pass**: Returns final output.
    -   **Fail**: Appends a rigorous disclaimer: _"Note: I could not reliably retrieve enough live sources..."_

## 🛡️ Tool Boundaries

Agents are strictly scoped to prevent hallucination and side effects:

-   **Planner**: Pure LLM (OpenAI/Anthropic). **No external tools**.
-   **Researcher**: **Exclusive access** to `Brave Search API`.
    -   It is the *only* agent allowed to fetch external data.
    -   It normalizes data into a standard List[Dict] structure.
-   **Synthesizer**: Pure LLM. Consumes Researcher output. **No external tools**.

## 💾 Caching & Persistence

-   **Short-term System State**: Managed by **LangGraph AsyncPostgresSaver**. This allows pausing/resuming workflows at any node.
-   **Long-term Semantic Cache**:
    -   Before starting a workflow, specific embeddings of the `user_request` are checked against `pgvector`.
    -   If a highly similar request (>95% cosine similarity) exists and was successful, the cached `final_output` is returned immediately.
