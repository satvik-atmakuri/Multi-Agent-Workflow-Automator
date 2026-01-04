# Multi-Agent Workflow Automator

An autonomous multi-agent system that executes complex user requests through specialized AI agents with human-in-the-loop clarification.

## 🏗️ Architecture

- **Orchestrator**: LangGraph-based workflow engine with DAG execution
- **Agents**: Planner, Clarification, Researcher, Synthesizer, Critic
- **State Management**: PostgreSQL with PgVector for embeddings
- **Backend**: FastAPI with async support
- **Frontend**: React (to be implemented)

## 🚀 Quick Start

### Prerequisites

- Docker and Docker Compose
- OpenAI API key (required)
- Anthropic API key (optional)

### Setup

1. **Clone and navigate to the project:**
   ```bash
   cd "/Users/spartan/projects/Multi-Agent Workflow Automator"
   ```

2. **Create environment file:**
   ```bash
   cp .env.example .env
   ```

3. **Edit `.env` and add your API keys:**
   ```bash
   # Required
   OPENAI_API_KEY=sk-your-key-here
   
   # Optional
   ANTHROPIC_API_KEY=your-key-here
   ```

4. **Start the services:**
   ```bash
   docker-compose up --build
   ```

5. **Verify the services are running:**
   - FastAPI: http://localhost:8000
   - API Docs: http://localhost:8000/docs
   - PostgreSQL: localhost:5432

### Testing the Setup

```bash
# Check API health
curl http://localhost:8000/health

# Expected response:
# {"status":"healthy","database":"connected","llm_api":"configured"}
```

## 📁 Project Structure

```
.
├── backend/
│   ├── app/
│   │   ├── agents/          # AI agent implementations
│   │   ├── api/             # FastAPI route handlers
│   │   ├── orchestrator/    # LangGraph workflow
│   │   ├── tools/           # External function tools
│   │   ├── config.py        # Configuration management
│   │   ├── database.py      # Database connection
│   │   ├── models.py        # Pydantic & ORM models
│   │   └── main.py          # FastAPI app entry point
│   ├── requirements.txt     # Python dependencies
│   └── Dockerfile           # Container definition
├── frontend/                # React app (to be implemented)
├── docker-compose.yml       # Service orchestration
├── init.sql                 # Database schema
└── .env                     # Environment variables (create from .env.example)
```

## 🔧 Development

### Running in Development Mode

The Docker Compose setup includes hot-reload for both backend and frontend:

```bash
# Start services
docker-compose up

# View logs
docker-compose logs -f backend

# Stop services
docker-compose down

# Rebuild after dependency changes
docker-compose up --build
```

### Database Access

```bash
# Connect to PostgreSQL
docker exec -it workflow_postgres psql -U workflow_user -d workflow_db

# Run migrations (when implemented)
docker exec -it workflow_backend alembic upgrade head
```

### Running Tests

```bash
# Inside the backend container
docker exec -it workflow_backend pytest

# With coverage
docker exec -it workflow_backend pytest --cov=app
```

## 📚 API Documentation

Once the server is running, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## 🎯 Workflow Example

```python
# Example workflow execution
POST /api/workflows
{
  "text": "Plan a 3-day trip to Paris for $1,500"
}

# Response
{
  "workflow_id": "123e4567-e89b-12d3-a456-426614174000",
  "status": "planning"
}

# Check status
GET /api/workflows/{workflow_id}

# When status is "awaiting_clarification", submit feedback
POST /api/workflows/{workflow_id}/feedback
{
  "responses": {"q1": "Direct flights preferred"},
  "ratings": {"q1": 5},
  "approval": "approved"
}
```

## 🧪 Implementation Status

- [x] Phase 1: Foundation Setup (Docker, FastAPI, PostgreSQL)
- [x] Phase 2: Database & State Management
- [/] Phase 3: Core Agent Implementation
- [/] Phase 4: LangGraph Orchestration
- [ ] Phase 5: FastAPI Backend Endpoints
- [/] Phase 6: Tool Integration
- [ ] Phase 7: React Frontend
- [/] Phase 8: Testing & Validation
- [ ] Phase 9: Deployment
- [ ] Phase 10: Advanced Features

## 📝 Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENAI_API_KEY` | Yes | OpenAI API key for LLM access |
| `ANTHROPIC_API_KEY` | No | Anthropic API key for Claude models |
| `DATABASE_URL` | Yes | PostgreSQL connection string |
| `APP_ENV` | No | Environment (development/production) |
| `CORS_ORIGINS` | No | Allowed CORS origins for frontend |

## 🤝 Contributing

This is a learning project. Feel free to experiment and extend!

## 📄 License

MIT License
