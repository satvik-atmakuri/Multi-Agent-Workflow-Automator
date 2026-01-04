import os
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models import Base, Workflow, WorkflowStep, UserFeedback, QuestionAnalytics
from app.config import settings

# Use an in-memory SQLite database for model verification if Postgres isn't available
# But we prefer testing against the real thing if possible.
# For unit testing models, SQLite is fine.

SQLALCHEMY_DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://workflow_user:workflow_pass@postgres:5432/workflow_db"
)

@pytest.fixture
def session():
    engine = create_engine(SQLALCHEMY_DATABASE_URL)
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    yield db
    db.close()
    Base.metadata.drop_all(bind=engine)


def test_workflow_model(session):
    workflow = Workflow(user_request="Test Request", status="planning")
    session.add(workflow)
    session.commit()
    
    saved = session.query(Workflow).first()
    assert saved.user_request == "Test Request"
    assert saved.status == "planning"
    assert saved.id is not None

def test_question_analytics_model(session):
    qa = QuestionAnalytics(question_text="Why?", question_category="clarification")
    session.add(qa)
    session.commit()
    
    saved = session.query(QuestionAnalytics).first()
    assert saved.question_text == "Why?"
    assert saved.question_category == "clarification"
