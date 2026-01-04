import pytest
import requests
import time
import uuid

# Configuration
BASE_URL = "http://localhost:8000/api/workflows"

@pytest.fixture
def workflow_request():
    return {
        "text": "Plan a romantic dinner for two in Paris with a budget of 300 euros."
    }

def test_full_workflow_lifecycle(workflow_request):
    """
    Simulates a full user journey:
    1. Start Workflow
    2. Poll Status (Researching -> Clarification?)
    3. Provide Feedback (if needed)
    4. Verify Completion
    """
    print(f"\n🚀 Starting E2E Workflow Test...")
    
    response = requests.post(f"{BASE_URL}/", json=workflow_request)
    if response.status_code != 201:
        print(f"❌ Failed to create workflow: {response.status_code}")
        print(f"Response: {response.text}")
    assert response.status_code == 201
    workflow_id = response.json()["workflow_id"]
    print(f"✅ Workflow Created: {workflow_id}")
    
    # 2. Poll Status
    status = "started"
    max_retries = 30 # 60 seconds max
    
    for i in range(max_retries):
        time.sleep(2) 
        r = requests.get(f"{BASE_URL}/{workflow_id}")
        assert r.status_code == 200
        data = r.json()
        status = data["status"]
        state = data["state"]
        
        print(f"🔄 Polling ({i+1}/{max_retries}): {status}")
        
        if status == "completed":
            print("🎉 Workflow Completed!")
            assert data["final_output"] is not None
            print("Final Output:", data["final_output"])
            break
            
        elif status == "failed":
            pytest.fail(f"❌ Workflow failed: {state}")
            
        elif status == "awaiting_clarification":
            print("❓ Clarification requested by agent. Sending feedback...")
            
            # Extract questions if any (though our current mock might just be status change)
            questions = state.get("clarification_questions", [])
            
            # 3. Submit Feedback
            feedback_payload = {
                "responses": {q["id"]: "This is a test answer" for q in questions},
                "ratings": {q["id"]: 5 for q in questions},
                "approval": "approved"
            }
            # If no questions found in state but status is awaiting_clarification, we still approve
            if not questions:
                # Fallback for simple testing if logic doesn't populate questions list in visible state
                feedback_payload["responses"] = {"dummy": "value"}

            f_resp = requests.post(f"{BASE_URL}/{workflow_id}/feedback", json=feedback_payload)
            assert f_resp.status_code == 200
            print("✅ Feedback submitted, workflow resumed.")
            
    else:
        pytest.fail("❌ Timeout waiting for workflow completion")

if __name__ == "__main__":
    # Allow running directly script
    test_full_workflow_lifecycle({"text": "Plan a 3-day trip to London for $2000 starting next Monday."})
