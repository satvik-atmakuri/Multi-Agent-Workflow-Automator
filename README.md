# Multi-Agent Workflow Automator

**An autonomous AI system that plans, researches, and executes complex tasks with human-in-the-loop validation.**

## 🏗️ Architecture

The system orchestrates specialized agents using **LangGraph** and **FastAPI**.

1.  **Planner**: Decomposes requests (e.g., "Plan a trip") into steps.
2.  **Researcher**: Fetches real-time info via **Brave Search API**.
3.  **Synthesizer**: Aggregates data into a final report.
4.  **Validator**: Checks freshness and accuracy before delivery.

_See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the deep dive._

## 🚀 Features

-   **Human-in-the-Loop**: Detects ambiguity and asks for clarification.
-   **Real-Time Research**: Accesses the live internet (unlike frozen LLMs).
-   **Semantic Memory**: Reuses past workflows using `pgvector` embeddings.
-   **Resilience**: Robust error handling with DuckDuckGo fallbacks.
-   **Management**: Delete old chats directly from the UI.

## 🛠️ Quick Start (Docker)

The fastest way to run the system.

1.  **Clone & Setup**:
    ```bash
    git clone https://github.com/satvik-atmakuri/Multi-Agent-Workflow-Automator.git
    cd Multi-Agent-Workflow-Automator
    cp .env.example .env
    ```

2.  **Configure `.env`**:
    
    | Variable | Purpose |
    | :--- | :--- |
    | `OPENAI_API_KEY` | Required. Brain of the system. |
    | `BRAVE_SEARCH_API_KEY` | Required. Real-time search. |
    | `DATABASE_URL` | Leave as default for Docker. |

3.  **Run**:
    ```bash
    docker-compose up --build
    ```

4.  **Access**:
    -   Frontend: http://localhost:5173
    -   Backend: http://localhost:8000

## 🧪 Testing & Evaluation

### Verification Script
Run the automated system check:
```bash
python verify_deployment.py
```

### QA Evaluation Suite
Evaluate agent logic against a test dataset:
```bash
docker exec -it workflow_backend python evaluate_qa_suite.py
```

## 📚 Documentation

-   **[Architecture](docs/ARCHITECTURE.md)**: State schema, caching logic, and tool boundaries.
-   **[Backend Guide](backend/README.md)**: API endpoints, migrations, and local setup.
-   **[Frontend Guide](frontend/README.md)**: Component structure and polling logic.
-   **[Troubleshooting](docs/TROUBLESHOOTING.md)**: Fixes for keys, CORS, and DB issues.


---
*Built with LangGraph, FastAPI, and React 19.*
