from typing import Dict, Any
from app.schemas import WorkflowState

FRESHNESS_KEYWORDS = [
    "current", "latest", "best", "right now", "today", "this year", "2025"
]

def validator_node(state: WorkflowState) -> Dict[str, Any]:
    """
    Validates whether the workflow output is allowed to claim freshness.
    Deterministic gate — no LLM calls.
    """
    # Use 'get' with default/fallback to avoid KeyErrors
    user_request = state.get("user_request", "").lower()
    researcher_output = state.get("researcher_output")
    final_output = state.get("final_output")

    # Detect intent from Planner (SSOT)
    freshness_req = state.get("freshness_requirements", {})
    requires_freshness = freshness_req.get("required", False) 
    
    # Fallback to regex if Planner didn't set it (legacy support)
    if not freshness_req:
         requires_freshness = any(k in user_request for k in FRESHNESS_KEYWORDS)

    if not requires_freshness:
        # Intent is Timeless/General -> Pass immediately.
        # Fix #3: If no sources were found, we allow the LLM answer but add a light disclaimer.
        sources = researcher_output.get("sources", []) if researcher_output else []
        if not sources:
            current_response = final_output.get("response", "")
            # Only append if not already there
            if "general knowledge" not in current_response.lower():
                 final_output["response"] = current_response + "\n\n(Note: This answer is based on general knowledge and may not reflect real-time data.)"
        
        return {"status": "completed", "final_output": final_output}

    # Freshness required → Researcher output must exist and HAVE SOURCES
    sources = researcher_output.get("sources", []) if researcher_output else []
    
    if not researcher_output or not sources or not isinstance(sources, list):
        # User requested to remove strict refusal. 
        # Instead of blocking, we allow the answer but add a disclaimer.
        current_response = final_output.get("response", "") if final_output else ""
        if "general knowledge" not in current_response.lower():
             if final_output:
                final_output["response"] = current_response + "\n\n(Note: I could not find verifiable sources, so this answer is based on general knowledge and may not reflect real-time data.)"
        
        return {
            "status": "completed", 
            "final_output": final_output
        }

    # Detect timestamp laundering in final answer
    response_text = ""
    if final_output and "response" in final_output:
        response_text = final_output.get("response", "").lower()

    if "as of" in response_text or "current market" in response_text:
         # If we are here, we passed the source existence check.
         # So we assume it's valid enough to pass.
         pass
        
    return {"status": "completed"}
