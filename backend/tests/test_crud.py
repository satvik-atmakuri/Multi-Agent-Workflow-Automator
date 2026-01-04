import pytest
from uuid import uuid4
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.models import Workflow
from app.schemas import WorkflowRequest, UserFeedbackRequest
from app import crud

# Setup Postgres database for testing
SQLALCHEMY_DATABASE_URL = "postgresql://workflow_user:workflow_pass@postgres:5432/test_workflow_db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="function")
def db_session():
    """Create a fresh database session for each test."""
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)

def test_create_workflow(db_session):
    request = WorkflowRequest(text="Test workflow request")
    workflow = crud.create_workflow(db_session, request)
    
    assert workflow.id is not None
    assert workflow.user_request == "Test workflow request"
    assert workflow.status == "planning"
    assert workflow.state["workflow_id"] == str(workflow.id)

def test_get_workflow(db_session):
    request = WorkflowRequest(text="Test workflow request")
    created = crud.create_workflow(db_session, request)
    
    fetched = crud.get_workflow(db_session, created.id)
    assert fetched.id == created.id
    assert fetched.user_request == created.user_request

def test_update_workflow_status(db_session):
    request = WorkflowRequest(text="Test workflow request")
    created = crud.create_workflow(db_session, request)
    
    updated = crud.update_workflow_status(db_session, created.id, "researching")
    assert updated.status == "researching"
    assert updated.updated_at > created.created_at

def test_update_workflow_status_completed(db_session):
    request = WorkflowRequest(text="Test workflow request")
    created = crud.create_workflow(db_session, request)
    assert created.completed_at is None
    
    updated = crud.update_workflow_status(db_session, created.id, "completed")
    assert updated.status == "completed"
    assert updated.completed_at is not None

def test_workflow_not_found(db_session):
    random_id = uuid4()
    assert crud.get_workflow(db_session, random_id) is None
    assert crud.update_workflow_status(db_session, random_id, "failed") is None
