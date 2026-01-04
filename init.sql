-- Enable PgVector extension for embeddings (RAG functionality)
CREATE EXTENSION IF NOT EXISTS vector;

-- Enable UUID generation
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Workflows table: Stores the main workflow state
CREATE TABLE IF NOT EXISTS workflows (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_request TEXT NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'planning',
    state JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,
    final_output JSONB
);

-- Index for faster status queries
CREATE INDEX IF NOT EXISTS idx_workflows_status ON workflows(status);
CREATE INDEX IF NOT EXISTS idx_workflows_created ON workflows(created_at DESC);

-- Workflow steps table: Audit trail of each agent execution
CREATE TABLE IF NOT EXISTS workflow_steps (
    id SERIAL PRIMARY KEY,
    workflow_id UUID REFERENCES workflows(id) ON DELETE CASCADE,
    agent_name VARCHAR(100) NOT NULL,
    input_state JSONB,
    output_state JSONB,
    executed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    duration_ms INTEGER,
    tokens_used INTEGER,
    cost_usd DECIMAL(10, 6)
);

CREATE INDEX IF NOT EXISTS idx_steps_workflow ON workflow_steps(workflow_id);
CREATE INDEX IF NOT EXISTS idx_steps_agent ON workflow_steps(agent_name);

-- User feedback table: Stores clarification responses
CREATE TABLE IF NOT EXISTS user_feedback (
    id SERIAL PRIMARY KEY,
    workflow_id UUID REFERENCES workflows(id) ON DELETE CASCADE,
    questions JSONB NOT NULL,
    responses JSONB NOT NULL,
    question_ratings JSONB,
    approval_status VARCHAR(20) NOT NULL,
    submitted_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_feedback_workflow ON user_feedback(workflow_id);

-- Question analytics table: Learning system for question quality
CREATE TABLE IF NOT EXISTS question_analytics (
    id SERIAL PRIMARY KEY,
    question_text TEXT NOT NULL,
    question_category VARCHAR(50),
    request_type VARCHAR(100),
    avg_rating DECIMAL(3, 2),
    times_asked INTEGER DEFAULT 1,
    times_helpful INTEGER DEFAULT 0,
    last_used TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_question_category ON question_analytics(question_category);
CREATE INDEX IF NOT EXISTS idx_question_type ON question_analytics(request_type);

-- Function to automatically update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to auto-update updated_at on workflows table
CREATE TRIGGER update_workflows_updated_at
    BEFORE UPDATE ON workflows
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- LangGraph checkpointer tables (created automatically by langgraph-checkpoint-postgres)
-- These tables store workflow checkpoints for resumability
-- They will be created when the application first runs
