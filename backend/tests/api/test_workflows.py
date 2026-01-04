import pytest
from unittest.mock import AsyncMock
from datetime import datetime

class MockState:
    def __init__(self, values):
        self.values = values

@pytest.mark.asyncio
async def test_create_workflow(client, mock_workflow_app):
    # Mock ainvoke to do nothing (it's called in background)
    mock_workflow_app.ainvoke = AsyncMock()
    
    payload = {"text": "Plan a trip to London"}
    response = client.post("/api/workflows/", json=payload)
    
    assert response.status_code == 201
    data = response.json()
    assert "workflow_id" in data
    assert data["status"] == "started"
    
    # Verify background task was called (we can't easily verify background tasks with TestClient 
    # without using a context manager or checking side effects, but we can check if ainvoke was NOT called synchronously)
    # Actually, TestClient runs background tasks synchronously after the response.
    # So ainvoke SHOULD have been called.
    mock_workflow_app.ainvoke.assert_called_once()

@pytest.mark.asyncio
async def test_get_workflow_status(client, mock_workflow_app):
    workflow_id = "test-id-123"
    
    # Mock aget_state
    mock_state_values = {
        "workflow_id": workflow_id,
        "status": "researching",
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
        "user_request": "Plan a trip"
    }
    
    # Mock the snapshot object returned by aget_state
    mock_snapshot = MockState(mock_state_values)
    mock_workflow_app.aget_state = AsyncMock(return_value=mock_snapshot)
    
    response = client.get(f"/api/workflows/{workflow_id}")
    
    assert response.status_code == 200
    data = response.json()
    assert data["workflow_id"] == workflow_id
    assert data["status"] == "researching"
    assert data["state"]["status"] == "researching"

@pytest.mark.asyncio
async def test_submit_feedback(client, mock_workflow_app):
    workflow_id = "test-id-123"
    mock_workflow_app.ainvoke = AsyncMock()
    
    payload = {
        "responses": {"q1": "Answer 1"},
        "ratings": {"q1": 5},
        "approval": "approved"
    }
    
    response = client.post(f"/api/workflows/{workflow_id}/feedback", json=payload)
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "resumed"
    
    mock_workflow_app.ainvoke.assert_called_once()
