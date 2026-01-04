import requests
import time
import json
import sys

# Configuration
API_URL = "http://localhost:8000/api/workflows"
POLL_INTERVAL = 2
MAX_RETRIES = 30  # 60 seconds max wait

# Test Cases
test_cases = [
    # {
    #     "id": "T1",
    #     "category": "General Knowledge",
    #     "query": "What are the three laws of thermodynamics?",
    #     "expected_keywords": ["energy", "entropy", "absolute zero", "first law", "second law"],
    #     "must_not_contain": ["I cannot fulfill", "verifiable sources"],
    #     "description": "Should answer from general knowledge without needing external research."
    # },
    {
        "id": "T2",
        "category": "Research (Freshness)",
        "query": "What is the current stock price of Apple (AAPL) right now?",
        "expected_keywords": ["AAPL", "$", "price", "Apple"],
        "must_not_contain": ["I cannot fulfill"],
        "description": "Should retrieve live data or at least attempt to search/answer with recent info."
    },
    {
        "id": "T4",
        "category": "Ambiguous/Clarification",
        "query": "Plan a trip.",
        "expected_keywords": ["where", "budget"], # Expecting clarification questions matching prompt logic
        "expect_status": "awaiting_clarification",
        "description": "Should trigger clarification mode due to vague request."
    },
    {
        "id": "T5",
        "category": "Human-in-the-loop (Feedback)",
        "query": "Plan a trip.",
        "feedback_payload": {
            "responses": {"q1": "Tokyo, Japan. Budget is $5000. 1 week duration."}
        },
        "expected_keywords": ["Tokyo", "$5000", "Japan"],
        "expect_status": "completed",
        "description": "Should stop for clarification, accept feedback, and complete."
    }
]

def run_test(case):
    print(f"\n[Running {case['id']}] {case['category']}: {case['query']}")
    
    try:
        # Create Workflow - Use skip_cache
        # import uuid in case we still want unique text
        unique_query = f"{case['query']}"
        resp = requests.post(API_URL, json={"text": unique_query, "skip_cache": True})
        resp.raise_for_status()
        data = resp.json()
        workflow_id = data["workflow_id"]
        print(f"  -> Workflow ID: {workflow_id}")
        
        # Poll for completion OR clarification
        final_state = None
        for _ in range(MAX_RETRIES):
            time.sleep(POLL_INTERVAL)
            status_resp = requests.get(f"{API_URL}/{workflow_id}")
            status_resp.raise_for_status()
            state = status_resp.json()
            status = state["status"]
            
            if status == "awaiting_clarification" and "feedback_payload" in case:
                print("  -> Status: awaiting_clarification. Sending Feedback...")
                # Send Feedback
                fb_resp = requests.post(f"{API_URL}/{workflow_id}/feedback", json=case["feedback_payload"])
                fb_resp.raise_for_status()
                print("  -> Feedback Submitted. Resuming polling...")
                # Reset retries effectively or just continue loop? 
                # We continue the loop, expecting it to go to 'completed' now.
                # To be safe, maybe extend retries? For now, we assume standard timeout covers it.
                continue

            if status in ["completed", "failed"]:
                final_state = state
                break
        else:
            print("  -> TIMED OUT")
            return False

        # Verify
        print(f"  -> Final Status: {status}")
        
        if status == "failed":
            print(f"  -> FAILED: Workflow failed.")
            return False
            
        # Check specific status expectation
        if "expect_status" in case:
            if status != case["expect_status"]:
                print(f"  -> FAILED: Expected status '{case['expect_status']}', got '{status}'")
                return False

        # Check Output Content
        final_output = final_state.get("final_output", {}) if final_state else {}
        response_text = final_output.get("response", "") if final_output else ""
        
        # Fallback: if synthesizer put it in final_output as string
        if not response_text and isinstance(final_output, str):
            response_text = final_output
        elif not response_text and "synthesizer_output" in final_state.get("state", {}):
             # Try grabbing from state directly if final_output is missing
             response_text = str(final_state["state"]["synthesizer_output"])

        print(f"  -> Response Length: {len(response_text)}")
        
        # Check Keywords
        missing_keywords = [k for k in case.get("expected_keywords", []) if k.lower() not in response_text.lower()]
        
        if missing_keywords:
            print(f"  -> FAILED: Missing keywords: {missing_keywords}")
            print(f"     Preview: {response_text[:100]}...")
            return False
            
        # Check Negative constraints
        forbidden_present = [k for k in case.get("must_not_contain", []) if k.lower() in response_text.lower()]
        if forbidden_present:
            print(f"  -> FAILED: Found forbidden content: {forbidden_present}")
            return False

        print("  -> SUCCESS: Output meets criteria.")
        return True

    except Exception as e:
        print(f"  -> ERROR: System error during test: {e}")
        return False

def main():
    print("=== Starting QA Evaluation Suite ===")
    print(f"Target: {API_URL}")
    
    results = []
    for case in test_cases:
        success = run_test(case)
        results.append({
            "id": case["id"],
            "success": success,
            "query": case["query"]
        })
    
    print("\n\n=== Final Report ===")
    passed = sum(1 for r in results if r["success"])
    total = len(results)
    
    for r in results:
        status_icon = "✅" if r["success"] else "❌"
        print(f"{status_icon} {r['id']}: {r['query']}")
        
    print(f"\nSummary: {passed}/{total} Passed")
    
    if passed != total:
        sys.exit(1)

if __name__ == "__main__":
    main()
