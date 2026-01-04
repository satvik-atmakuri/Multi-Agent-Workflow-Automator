from __future__ import annotations

from typing import Dict, Any, List
from urllib.parse import urlparse

from app.schemas import WorkflowState

FRESHNESS_KEYWORDS = [
    "current", "latest", "right now", "today", "this year", "this week", "breaking", "headline", "news"
]


def _is_valid_http_url(u: str) -> bool:
    try:
        p = urlparse(u)
        return p.scheme in {"http", "https"} and bool(p.netloc)
    except Exception:
        return False


def _unique_domains(urls: List[str]) -> int:
    domains = set()
    for u in urls:
        try:
            domains.add(urlparse(u).netloc.lower())
        except Exception:
            continue
    return len(domains)


def _append_disclaimer(final_output: Dict[str, Any] | None, disclaimer: str) -> Dict[str, Any] | None:
    if not final_output:
        return final_output
    resp = final_output.get("response", "") or ""
    if disclaimer.lower() in resp.lower():
        return final_output
    if resp and not resp.endswith(("\n", " ")):
        resp += " "
    final_output["response"] = resp + disclaimer
    return final_output


def validator_node(state: WorkflowState) -> Dict[str, Any]:
    """
    Validates whether the workflow output is allowed to claim freshness.
    Deterministic gate — no LLM calls.

    Policy:
    - If freshness is NOT required: allow completion, but if no sources, add a light disclaimer.
    - If freshness IS required: require >= 2 valid http(s) URLs and preferably >= 2 unique domains.
      If missing, allow completion but force a stronger disclaimer (no hard failure).
    """
    user_request = (state.get("user_request") or "").lower()
    researcher_output = state.get("researcher_output") or {}
    final_output = state.get("final_output")

    freshness_req = state.get("freshness_requirements", {}) or {}
    requires_freshness = bool(freshness_req.get("required", False))

    freshness_req = state.get("freshness_requirements", {}) or {}
    requires_freshness = bool(freshness_req.get("required", False))

    # Fallback if planning stage didn't run or didn't set it (e.g. legacy state)
    if not freshness_req:
        requires_freshness = any(k in user_request for k in FRESHNESS_KEYWORDS)

    # 1. Enforce Structure (Robustness)
    if final_output and isinstance(final_output, dict):
        if "confidence" not in final_output:
            final_output["confidence"] = "Medium" # Default
        if "citations" not in final_output:
            final_output["citations"] = []

    sources = researcher_output.get("sources", []) if isinstance(researcher_output, dict) else []
    if not isinstance(sources, list):
        sources = []

    valid_sources = [s for s in sources if isinstance(s, str) and _is_valid_http_url(s)]
    uniq_domains = _unique_domains(valid_sources)

    if not requires_freshness:
        if not valid_sources:
            final_output = _append_disclaimer(
                final_output,
                "(Note: I did not retrieve external sources for this; the answer may reflect general knowledge and may not include the latest updates.)",
            )
        return {"status": "completed", "final_output": final_output}

    if len(valid_sources) < 2 or uniq_domains < 2:
        final_output = _append_disclaimer(
            final_output,
            "(Note: I could not reliably retrieve enough live sources to guarantee this is fully up to date. Consider rerunning or providing preferred sources.)",
        )
        return {"status": "completed", "final_output": final_output}

    response_text = (final_output.get("response", "") if final_output else "").lower()
    if "as of" in response_text and not valid_sources:
        final_output = _append_disclaimer(
            final_output,
            "(Note: A time-qualified claim was made, but no valid sources were attached.)",
        )
        return {"status": "completed", "final_output": final_output}

    return {"status": "completed", "final_output": final_output}
