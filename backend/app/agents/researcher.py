"""
Researcher Agent: Executes search queries to gather information.
Uses Brave Search API (preferred) and returns deterministic sources (URLs) from tool results.
Falls back gracefully if sources are unavailable or the LLM returns non-JSON.

IMPORTANT:
- Uses Planner output (goal/required_info) as the effective task so clarifications flow downstream.
"""
from __future__ import annotations

from typing import List, Dict, Any
from datetime import datetime
import re

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.exceptions import OutputParserException
from pydantic import BaseModel, Field

from app.agents.base import BaseAgent
from app.schemas import WorkflowState

# Optional fallback (keeps repo runnable even without Brave key)
try:
    from langchain_community.tools import DuckDuckGoSearchRun  # type: ignore
except Exception:  # pragma: no cover
    DuckDuckGoSearchRun = None  # type: ignore

from app.services.brave_search import brave_web_search, brave_news_search, BraveSearchError


class ResearchLLMOutput(BaseModel):
    summary: str = Field(description="Concise summary of the gathered information")


class ResearcherAgent(BaseAgent):
    """
    The Researcher Agent performs web searches to answer the user's request.
    """

    def __init__(self):
        super().__init__(temperature=0)
        self.parser = JsonOutputParser(pydantic_object=ResearchLLMOutput)

        self.ddg_fallback = DuckDuckGoSearchRun() if DuckDuckGoSearchRun else None

        self.prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    """You are an expert Researcher.

You will be given a task and a list of Search Results (titles/snippets/urls).
Your job is to write a concise, factual summary grounded ONLY in those search results.

Rules:
1) If Search Results are empty, you MUST output JSON with summary: "I could not find the requested information."
2) Do NOT invent sources/URLs. You will NOT output sources — only a summary.
3) Do NOT make up dynamic facts (prices, exact counts, dates) unless explicitly present in the results.
4) Prefer to paraphrase and mention key claims with light attribution like "According to the sources..."

Return STRICT JSON exactly matching:
{format_instructions}
""",
                ),
                ("user", """Task: {task}

Search Results:
{search_results}
"""),
            ]
        )

    @staticmethod
    def _needs_news_search(state: WorkflowState) -> bool:
        req = (state.get("user_request") or "").lower()
        planner = state.get("planner_output") or {}
        plan_text = str(planner).lower()

        news_markers = ["news", "headline", "headlines", "breaking", "latest updates", "today's news", "this week"]
        return any(m in req for m in news_markers) or any(m in plan_text for m in news_markers)

    @staticmethod
    def _format_results_for_llm(results: List[Dict[str, Any]]) -> str:
        if not results:
            return "NO RESULTS"
        lines = []
        for i, r in enumerate(results, start=1):
            title = r.get("title", "")
            url = r.get("url", "")
            snippet = r.get("snippet", "")
            source = r.get("source", "")
            published = r.get("published", None)

            meta = []
            if source:
                meta.append(source)
            if published:
                meta.append(str(published))
            meta_str = f" ({' | '.join(meta)})" if meta else ""

            lines.append(f"{i}. {title}{meta_str}\n   {snippet}\n   URL: {url if url else '[no url]'}")
        return "\n".join(lines)

    @staticmethod
    def _contains_year(text: str) -> bool:
        return bool(re.search(r"\b(19|20)\d{2}\b", text))

    @staticmethod
    def _build_effective_task(state: WorkflowState) -> str:
        """
        Use planner_output.goal and first step.required_info if available.
        This ensures clarified intent is used downstream.
        """
        user_request = state.get("user_request") or ""
        planner_output = state.get("planner_output") or {}

        effective = user_request.strip()

        if isinstance(planner_output, dict):
            goal = planner_output.get("goal")
            steps = planner_output.get("steps") or []

            if goal and isinstance(goal, str) and goal.strip():
                effective = goal.strip()

            if steps and isinstance(steps, list) and isinstance(steps[0], dict):
                req_info = steps[0].get("required_info")
                if req_info and isinstance(req_info, str) and req_info.strip():
                    effective = f"{effective}\nRequired info: {req_info.strip()}"

        return effective.strip()

    def invoke(self, state: WorkflowState) -> dict:
        # ✅ Use effective task (includes clarifications)
        effective_task = self._build_effective_task(state)

        # --- Step 1: Generate search query ---
        query_gen_prompt = ChatPromptTemplate.from_template(
            "Generate a simple, keyword-based web search query for the request below. "
            "Strip filler words. Keep location/date constraints. Do not add extra years unless missing.\n"
            "Request: {request}\nQuery:"
        )
        chain_gen = query_gen_prompt | self.llm
        search_query = chain_gen.invoke({"request": effective_task}).content.strip().replace('"', "")

        # ✅ Fix: Only append current year if request/query has no year already
        if any(w in effective_task.lower() for w in ["current", "latest", "today", "this year", "now"]):
            if not self._contains_year(effective_task) and not self._contains_year(search_query):
                search_query = f"{search_query} {datetime.now().year}"

        print(f"[{self.name}] Effective Task: {effective_task}")
        print(f"[{self.name}] Generated Query: {search_query}")

        # --- Step 2: Search (Brave preferred) ---
        results: List[Dict[str, Any]] = []
        used_tool: str = "brave_web"

        try:
            if self._needs_news_search(state):
                used_tool = "brave_news"
                results = brave_news_search(search_query, count=5)
            else:
                used_tool = "brave_web"
                results = brave_web_search(search_query, count=5)
        except BraveSearchError as e:
            print(f"[{self.name}] Brave not configured: {e}")
        except Exception as e:
            print(f"[{self.name}] Brave search error: {e}")

        # Optional fallback
        if not results and self.ddg_fallback is not None:
            try:
                print(f"[{self.name}] Falling back to DuckDuckGoSearchRun...")
                ddg_text = self.ddg_fallback.invoke(search_query)

                if ddg_text and isinstance(ddg_text, str):
                    used_tool = "duckduckgo_fallback"
                    results = [{
                        "title": "DuckDuckGo fallback (unstructured)",
                        "url": "",
                        "snippet": ddg_text[:2000],
                        "source": "DuckDuckGo"
                    }]
            except Exception as e:
                print(f"[{self.name}] DuckDuckGo fallback failed: {e}")

        # Deterministic sources
        sources: List[str] = [r.get("url", "") for r in results if r.get("url")]
        seen = set()
        sources = [s for s in sources if not (s in seen or seen.add(s))]

        # --- Step 3: If no results, deterministic output ---
        if not results or self._format_results_for_llm(results) == "NO RESULTS":
            return {
                "researcher_output": {
                    "summary": "I could not find the requested information.",
                    "sources": sources,
                    "tool": used_tool,
                    "query": search_query,
                }
            }

        # --- Step 4: Summarize grounded to results ---
        search_results_text = self._format_results_for_llm(results)
        chain = self.prompt | self.llm

        try:
            raw = chain.invoke(
                {
                    "task": effective_task,  # ✅ use effective task here too
                    "search_results": search_results_text,
                    "format_instructions": self.parser.get_format_instructions(),
                }
            )
            parsed = self.parser.parse(raw.content)
            summary = (parsed.get("summary") or "").strip() or "I could not find the requested information."

        except OutputParserException:
            content = (raw.content if "raw" in locals() else "").strip()
            summary = content if content else "I could not find the requested information."
        except Exception as e:
            print(f"[{self.name}] Summarization error: {e}")
            summary = "I could not find the requested information."

        result = {
            "summary": summary,
            "sources": sources,
            "tool": used_tool,
            "query": search_query,
        }

        return {"researcher_output": result}
