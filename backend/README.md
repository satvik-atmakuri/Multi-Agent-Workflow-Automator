# Backend - Multi-Agent Workflow Automator

The backend is a high-performance **FastAPI** application that orchestrates AI agents using **LangGraph**. It handles state persistence, semantic caching, and real-time internet research via Brave Search.

## 🏃 Local Run (No Docker)

For developers who want to debug Python logic directly:

1.  **Virtual Env**:
    ```bash
    cd backend
    python -m venv venv
    
    # Windows
    venv\Scripts\activate
    # Mac/Linux
    source venv/bin/activate
    ```

2.  **Install**:
    ```bash
    pip install -r requirements.txt
    ```

3.  **Run**:
    ```bash
    # Ensure DATABASE_URL in .env points to localhost if using local DB
    uvicorn app.main:app --reload --port 8000
    ```

## 🗄️ Migrations (Alembic)

We use Alembic to manage the Postgres schema.

-   **Apply Migrations**: `alembic upgrade head`
-   **Create Migration**: `alembic revision --autogenerate -m "msg"`

## 🔌 API Endpoints

### Workflows

-   `POST /api/workflows`: Start new workflow.
    -   Payload: `{"text": "Research AI", "skip_cache": false}`
-   `GET /api/workflows/{id}`: Get status & state.
-   `DELETE /api/workflows/{id}`: Delete workflow & history.
-   `POST /api/workflows/{id}/feedback`: Submit clarification.
    -   Payload: `{"responses": {"clarification": "Context"}}`
-   `POST /api/workflows/{id}/chat`: Continue conversation (Not fully used in UI yet).

### Preferences

-   `GET /api/preferences`: List user settings.
-   `POST /api/preferences`: Set key-value pair.

## 🧠 State Storage

State is dual-persisted:
1.  **LangGraph**: Uses `AsyncPostgresSaver` in `backend/app/orchestrator/graph.py` to checkpoint state at every node.
2.  **Postgres Table**: The `workflows` table stores high-level status (`completed`, `failed`), timestamps, and the final JSON output for easy querying.

## 🦁 Brave Search Setup

1.  Get Key: https://brave.com/search/api/
2.  Set `BRAVE_SEARCH_API_KEY` in `.env`.
3.  **Fallback**: If key is missing, `Researcher` agent defaults to a mock/DDG fallback (see `researcher.py`).

## ⚠️ Common Errors

-   **Redirect Loops**: Check `main.py` CORS settings.
-   **Async Timeout**: If Brave takes >60s, increase `httpx` timeout in `brave_search.py`.
