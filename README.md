# Multi-Agent Workflow Automator

An autonomous multi-agent system that executes complex user requests through specialized AI agents with human-in-the-loop clarification.

## 🏗️ Architecture

- **Orchestrator**: LangGraph-based workflow engine managing the state and transitions.
- **Agents**:
    - **Planner**: Decomposes user requests into actionable steps and detects ambiguity.
    - **Researcher**: Performs web searches using **Brave Search API** to gather real-time data (with DuckDuckGo/Mock Fallback for resilience).
    - **Synthesizer**: Aggregates plan and research data into a polished, Markdown-formatted report.
- **State Management**: PostgreSQL with PgVector for semantic memory and embeddings.
- **Backend**: FastAPI with async support for high-throughput agent handling.
- **Frontend**: React (Vite + Tailwind) for an intuitive chat-like interface.

## 🚀 Key Features

- **Intelligent Planning**: Break down complex queries (e.g., "Plan a trip to Tokyo") into sub-tasks.
- **Real-Time Research (Brave Search)**: Fetch fresh, high-quality data from the web using the Brave Search API.
- **Manage History**: Delete old workflows directly from the sidebar UI.
- **Human-in-the-loop**: Validates ambiguity. If a request is vague ("Plan a trip"), the system pauses and asks clarifying questions before proceeding.
- **Semantic Caching**: Reuses previous successful workflows to save time and API costs.
- **Mock Fallback**: Robust error handling ensures the system works even if external search APIs are rate-limited.

## 🛠️ Quick Start

### Prerequisites

- Docker and Docker Compose
- OpenAI API key (required)
- Brave Search API key (required for best results)
- Anthropic API key (optional)

### Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/satvik-atmakuri/Multi-Agent-Workflow-Automator.git
   cd Multi-Agent-Workflow-Automator
   ```

2. **Create environment file:**
   ```bash
   cp .env.example .env
   ```

3. **Edit `.env` and add your API keys:**
   ```bash
   # Required for Agents
   OPENAI_API_KEY=sk-your-key-here
   
   # Required for Research
   BRAVE_SEARCH_API_KEY=your-brave-key-here
   
   # Database (Defaults work with Docker)
   DATABASE_URL=postgresql://workflow_user:workflow_pass@postgres:5432/workflow_db
   ```

4. **Start the services:**
   ```bash
   docker-compose up --build
   ```

5. **Access the Application:**
   - **Frontend UI**: http://localhost:5173
   - **FastAPI Backend**: http://localhost:8000
   - **API Docs**: http://localhost:8000/docs

## 🎯 Usage

1. **Open the Frontend**: Go to `http://localhost:5173`.
2. **Start a Workflow**: Type a request like *"What is the current stock price of Apple?"* or *"Plan a 3-day trip to Paris"*.
3. **Interact**:
   - If the request is clear, watch the agents Plan -> Research -> Synthesize.
   - If the request is ambiguous (e.g., *"Plan a trip"*), the system will ask for clarification. Reply in the chat (e.g., *"Tokyo, $3000 budget"*).
4. **View Results**: The final output will be displayed as a formatted Markdown report.
5. **Manage**: Click the trash icon in the sidebar to delete any old chat sessions.

## 📁 Project Structure

```
.
├── backend/
│   ├── app/
│   │   ├── agents/          # Planner, Researcher (Brave), Synthesizer logic
│   │   ├── orchestrator/    # LangGraph workflow definition (graph.py)
│   │   ├── api/             # FastAPI endpoints (workflows.py)
│   │   ├── services/        # Brave Search & Caching utilities
│   │   └── models.py        # Database schema
│   ├── evaluate_qa_suite.py # Automated verification tests
│   └── Dockerfile
├── frontend/                # React Application
│   ├── src/
│   │   ├── components/      # UI Components (ChatInterface, Sidebar, etc.)
│   │   └── App.tsx          # Main entry point
│   └── Dockerfile
├── docker-compose.yml       # Service orchestration
└── init.sql                 # Database initialization
```


