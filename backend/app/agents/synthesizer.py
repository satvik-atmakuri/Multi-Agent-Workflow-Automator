"""
Synthesizer Agent: Combines all gathered information into a final response.
Uses planner goal (effective request) + structured researcher output (summary + sources).
"""
from typing import Dict, Any, List
from datetime import datetime

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.exceptions import OutputParserException
from pydantic import BaseModel, Field

from app.agents.base import BaseAgent
from app.schemas import WorkflowState

class SynthesizerOutput(BaseModel):
    response: str = Field(description="The final helpful answer in Markdown format")
    confidence: str = Field(description="Confidence level (High/Medium/Low)")
    citations: List[str] = Field(description="List of URLs explicitly cited in the response")

class SynthesizerAgent(BaseAgent):
    """
    The Synthesizer Agent takes the plan, research inputs, and user request
    to create a coherent, final response.
    """

    def __init__(self):
        super().__init__(temperature=0.5)
        self.parser = JsonOutputParser(pydantic_object=SynthesizerOutput)

        self.prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert Synthesizer.

Your job:
- Produce a final, helpful answer to the user's request in Markdown.
- You MUST strictly rely on the Research Findings provided. Do NOT invent facts, prices, availability, dates, or events.
- If Research Findings indicate missing data ("I could not find..." or empty), say so plainly and provide safe alternatives (what user can do next).

Output rules:
- Valid Markdown
- Use headers + bullet lists where appropriate
- If sources are provided, include a Sources section with clickable links

Current Date: {date}
"""),
            ("user", """Effective User Request:
{request}

Plan:
{plan}

Research Summary:
{research_summary}

Sources:
{sources_md}

Generate the final response as a detailed JSON object strictly matching:
{format_instructions}""")
        ])

    @staticmethod
    def _effective_request(state: WorkflowState) -> str:
        planner = state.get("planner_output") or {}
        if isinstance(planner, dict):
            goal = planner.get("goal")
            if isinstance(goal, str) and goal.strip():
                return goal.strip()
        return (state.get("user_request") or "").strip()

    @staticmethod
    def _format_sources_md(sources: List[str]) -> str:
        if not sources:
            return "None"
        lines = []
        for i, url in enumerate(sources, start=1):
            lines.append(f"{i}. {url}")
        return "\n".join(lines)

    def invoke(self, state: WorkflowState) -> dict:
        print(f"[{self.name}] Synthesizing final response...")

        current_date_str = datetime.now().strftime("%B %d, %Y")

        # Plan
        plan_obj = state.get("planner_output")
        plan_str = str(plan_obj) if plan_obj else "No plan available."

        # Research (structured)
        research_obj = state.get("researcher_output") or {}
        if isinstance(research_obj, dict):
            research_summary = (research_obj.get("summary") or "").strip()
            sources = research_obj.get("sources") or []
            if not isinstance(sources, list):
                sources = []
        else:
            research_summary = str(research_obj)
            sources = []

        sources_md = self._format_sources_md([s for s in sources if isinstance(s, str) and s.strip()])

        effective_req = self._effective_request(state)

        chain = self.prompt | self.llm | self.parser

        try:
            result = chain.invoke({
                "request": effective_req,
                "plan": plan_str,
                "research_summary": research_summary if research_summary else "No research findings.",
                "sources_md": sources_md,
                "date": current_date_str,
                "format_instructions": self.parser.get_format_instructions()
            })
            
            # Helper to extract just the response text
            # result is a dict {response, confidence, citations}
            
            return {
                "synthesizer_output": result,
                "status": "completed",
                "final_output": result
            }

        except OutputParserException:
             # Fallback if strict JSON fails (rare with gpt-4o, but possible)
             # We might not have the raw text easily if parser blocked it.
             # Actually, without 'include_raw=True' or catching earlier, we might lose it.
             # But for now, we returning a generic error or retry logic would be better.
             # Let's return a basic success with error note.
             return {
                 "synthesizer_output": {"response": "Error parsing agent response.", "confidence": "Low", "citations": []},
                 "status": "completed",
                 "final_output": {"response": "I encountered an error formatting the final response."}
             }

        except Exception as e:
            print(f"[{self.name}] Error during synthesis: {e}")
            return {"validation_errors": [{"agent": self.name, "error": str(e)}]}
