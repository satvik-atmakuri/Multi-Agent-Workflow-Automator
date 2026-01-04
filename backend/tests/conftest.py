import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock
from app.main import app

@pytest.fixture
def client():
    """
    Test client for FastAPI app.
    """
    return TestClient(app)

@pytest.fixture
def mock_workflow_app():
    """
    Mock the LangGraph workflow app stored in app.state.
    """
    mock_app = MagicMock()
    app.state.workflow = mock_app
    return mock_app
