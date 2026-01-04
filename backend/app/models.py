from sqlalchemy import Column, String, Integer, DateTime, Text, DECIMAL
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from pgvector.sqlalchemy import Vector
from app.database import Base
import uuid


class Workflow(Base):
    __tablename__ = "workflows"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_request = Column(Text, nullable=False)
    request_embedding = Column(Vector(1536))
    status = Column(String(50), nullable=False, default="planning")

    state = Column(
        JSONB,
        nullable=False,
        default=dict,               # ✅ Python-side
        server_default="{}"          # ✅ DB-side
    )

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now()    # ✅ FIX
    )

    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),   # ✅ FIX
        onupdate=func.now()
    )

    completed_at = Column(DateTime(timezone=True), nullable=True)
    final_output = Column(JSONB, nullable=True)


class WorkflowStep(Base):
    __tablename__ = "workflow_steps"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    workflow_id = Column(UUID(as_uuid=True), nullable=False)
    agent_name = Column(String(100), nullable=False)

    input_state = Column(JSONB, default=dict, server_default="{}")
    output_state = Column(JSONB, default=dict, server_default="{}")

    executed_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now()    # ✅ FIX
    )

    duration_ms = Column(Integer)
    tokens_used = Column(Integer)
    cost_usd = Column(DECIMAL(10, 6))


class UserFeedback(Base):
    __tablename__ = "user_feedback"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    workflow_id = Column(UUID(as_uuid=True), nullable=False)

    questions = Column(JSONB, nullable=False)
    responses = Column(JSONB, nullable=False)
    question_ratings = Column(JSONB)

    approval_status = Column(String(20), nullable=False)

    submitted_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now()    # ✅ FIX
    )


class QuestionAnalytics(Base):
    __tablename__ = "question_analytics"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    question_text = Column(Text, nullable=False)
    question_category = Column(String(50))
    question_embedding = Column(Vector(1536))
    request_type = Column(String(100))

    avg_rating = Column(DECIMAL(3, 2))
    times_asked = Column(Integer, default=1)
    times_helpful = Column(Integer, default=0)

    last_used = Column(DateTime(timezone=True), nullable=True)


class UserPreference(Base):
    __tablename__ = "user_preferences"

    id = Column(Integer, primary_key=True, autoincrement=True)
    key = Column(String(50), unique=True, nullable=False)
    value = Column(Text, nullable=False)
    
    updated_at = Column(
        DateTime(timezone=True), 
        server_default=func.now(), 
        onupdate=func.now()
    )
