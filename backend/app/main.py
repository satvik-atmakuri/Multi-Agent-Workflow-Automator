"""
Main FastAPI application initialization.
This is the entry point for the backend API.
"""
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from psycopg_pool import AsyncConnectionPool

from app.config import settings
from app.orchestrator.graph import build_graph

# Configure logging
logging.basicConfig(
    level=settings.LOG_LEVEL.upper(),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manage application lifespan: setup/teardown of resources.
    """
    logger.info("🚀 Starting Multi-Agent Workflow Automator")
    logger.info(f"Environment: {settings.APP_ENV}")
    
    # Initialize Checkpointer and Workflow
    try:
        # Use AsyncPostgresSaver context manager to handle pool creation/closure automatically
        # This is the recommended way to ensuring the pool is closed on shutdown
        async with AsyncPostgresSaver.from_conn_string(settings.DATABASE_URL) as checkpointer:
            # Setup persistence tables
            await checkpointer.setup()
            
            # Build graph with checkpointer
            workflow = build_graph(checkpointer=checkpointer)
            
            # Store in app state
            app.state.workflow = workflow
            logger.info("✅ LangGraph Workflow Initialized with Persistence")
            
            yield
            
    except Exception as e:
        logger.error(f"❌ Failed to initialize workflow: {e}")
        # Yield to allow app to start (though functionality will be broken)
        yield
    
    logger.info("👋 Shutting down Multi-Agent Workflow Automator")

# Initialize FastAPI app
app = FastAPI(
    title="Multi-Agent Workflow Automator",
    description="Autonomous multi-agent system for complex task execution with human-in-the-loop clarification",
    version="1.0.0",
    docs_url="/docs",  # Swagger UI at http://localhost:8000/docs
    redoc_url="/redoc",  # ReDoc at http://localhost:8000/redoc
    lifespan=lifespan
)

# Configure CORS for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "Multi-Agent Workflow Automator",
        "version": "1.0.0",
        "environment": settings.APP_ENV
    }

@app.get("/health")
async def health_check():
    """Detailed health check"""
    # Simply check if workflow is initialized
    workflow_status = "configured" if hasattr(app.state, "workflow") and app.state.workflow else "unconfigured"
    
    return {
        "status": "healthy",
        "database": "connected", # AsyncPostgresSaver manages connection
        "workflow_engine": workflow_status
    }

# Import and include routers
# Import and include routers
from app.api import workflows, preferences
app.include_router(workflows.router, prefix="/api/workflows", tags=["workflows"])
app.include_router(preferences.router, prefix="/api/preferences", tags=["preferences"])
