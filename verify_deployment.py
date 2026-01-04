import requests
import time
import sys

BASE_URL = "http://localhost:8000"

def log(msg, status="INFO"):
    colors = {
        "INFO": "\033[94m",
        "SUCCESS": "\033[92m",
        "ERROR": "\033[91m",
        "RESET": "\033[0m"
    }
    print(f"{colors.get(status, '')}[{status}] {msg}{colors['RESET']}")

def verify_system():
    log("Starting System Verification...", "INFO")

    # 1. Health Check
    try:
        r = requests.get(f"{BASE_URL}/health")
        if r.status_code == 200:
            log("Backend is Healthy", "SUCCESS")
            log(f"Details: {r.json()}", "INFO")
        else:
            log(f"Backend Health Check Failed: {r.status_code}", "ERROR")
            sys.exit(1)
    except Exception as e:
        log(f"Could not connect to backend: {e}", "ERROR")
        sys.exit(1)

    # 2. Configure a test workflow
    # We use "skip_cache" to ensure a new one is created
    payload = {
        "text": "Test verification workflow",
        "skip_cache": True
    }
    
    workflow_id = None
    try:
        log("Creating Test Workflow...", "INFO")
        r = requests.post(f"{BASE_URL}/api/workflows/", json=payload)
        if r.status_code == 201:
            data = r.json()
            workflow_id = data["workflow_id"]
            log(f"Created Workflow: {workflow_id}", "SUCCESS")
        else:
            log(f"Failed to create workflow: {r.text}", "ERROR")
            sys.exit(1)
    except Exception as e:
        log(f"Error creating workflow: {e}", "ERROR")
        sys.exit(1)

    # 3. Verify it exists in list
    try:
        r = requests.get(f"{BASE_URL}/api/workflows/")
        ids = [w["workflow_id"] for w in r.json()]
        if workflow_id in ids:
            log("Verified workflow appears in history list", "SUCCESS")
        else:
            log("Workflow not found in history list!", "ERROR")
    except Exception as e:
        log(f"Error listing workflows: {e}", "ERROR")

    # 4. Test Deletion (The New Feature)
    if workflow_id:
        try:
            log(f"Testing Deletion for {workflow_id}...", "INFO")
            r = requests.delete(f"{BASE_URL}/api/workflows/{workflow_id}")
            
            if r.status_code == 204:
                log("Delete request successful (204 No Content)", "SUCCESS")
                
                # Verify it's gone
                r_check = requests.get(f"{BASE_URL}/api/workflows/{workflow_id}")
                # The API returns 200 with workflow status or 404? 
                # Our get_workflow_status might return 404 or 500 if DB record is gone.
                # Let's check the list again.
                r_list = requests.get(f"{BASE_URL}/api/workflows/")
                current_ids = [w["workflow_id"] for w in r_list.json()]
                
                if workflow_id not in current_ids:
                    log("Confirmed: Workflow is gone from history.", "SUCCESS")
                else:
                    log("❌ Failed: Workflow still exists in list after delete!", "ERROR")
            else:
                log(f"Delete failed with status {r.status_code}: {r.text}", "ERROR")
        except Exception as e:
            log(f"Error during deletion test: {e}", "ERROR")

    log("System Verification Complete", "INFO")

if __name__ == "__main__":
    verify_system()
