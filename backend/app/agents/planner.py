"""
Planner Agent: Break down the user's request into a structured plan.
"""
from typing import Dict, Any, List
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.exceptions import OutputParserException
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from app.agents.base import BaseAgent
from app.schemas import WorkflowState

class PlanStep(BaseModel):
    step_id: int
    description: str
    agent: str = Field(description="The agent best suited for this step (Researcher, Synthesizer, etc.)")
    required_info: str = Field(description="What information is needed to execute this step")

class Plan(BaseModel):
    goal: str
    steps: List[PlanStep]
    clarification_needed: bool = Field(description="True if the request is ambiguous and needs user input first")
    clarification_questions: List[str] = Field(default_factory=list, description="List of questions if clarification is needed")
    
    # Freshness Detection
    freshness_required: bool = Field(description="True if the user requests current/latest info (news, prices, '2025') vs general knowledge")
    freshness_reasoning: str = Field(description="Why is freshness required or not? e.g. 'User asked for 2025 specs'")

class PlannerAgent(BaseAgent):
    """
    The Planner Agent analyzes the user request and generates a high-level plan.
    It decides if the request is clear enough to proceed or if clarification is needed.
    """
    
    def __init__(self):
        super().__init__(temperature=0.2)  # Lower temperature for more deterministic planning
        
        # Define the output parser
        self.parser = JsonOutputParser(pydantic_object=Plan)
        
        # Define the prompt template
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert Planner Agent in a multi-agent system.
Your goal is to analyze the user's request and create a detailed, step-by-step execution plan.

The available agents to assign tasks to are:
1. **Researcher**: effective for searching the web, gathering information, and fact-checking.
2. **Synthesizer**: effective for compiling information, writing summaries, coding, or creating final content.

CRITICAL INSTRUCTION ON CLARIFICATION:
You must be extremely strict about ambiguity. Do NOT make assumptions about:
- Locations (e.g., if user says "trip", ask "Where?")
- Budgets (e.g., if user asks for a plan, ask "What is the budget?")
- Dates/Timeframes (e.g., if user says "next week", ask for specific dates)
- Preferences (e.g., style, constraints).

If ANY of these core details are missing, you MUST set `clarification_needed` to True and provide a list of specific questions. Better to ask than to assume.

HOWEVER, CRITICAL OVERRIDE - ONCE FEEDBACK IS GIVEN:
If `User Feedback` is provided below, you MUST PROCEED.
1. DO NOT ask for "specific sources" (assume Google Search).
2. DO NOT ask for "format" (assume Markdown report).
3. DO NOT ask for "specific details" if the user gave a general category (e.g., if "IT News", just find top IT news).
4. You are FORBIDDEN from setting `clarification_needed` to True if `User Feedback` is present, unless the feedback is "I don't know" or "Cancel".
5. Your goal is to PRODUCE A PLAN, not to interview the user.
6. If you have ANY partial idea of what to do, EXECUTE IT.

If the request is truly clear and detailed, set `clarification_needed` to False and provide the steps.
    
FRESHNESS DETECTION RULES:
- Set `freshness_required` = **True** ONLY if the answer would be materially wrong without recent data.
  - "Best tablets 2025" -> True
  - "Best tablet in current market" -> True
  - "News about X" -> True
  - "Current price of Bitcoin" -> True
  - "Events/Openings/Availability" -> True
- Set `freshness_required` = **False** for everything else:
  - "Popular tablets for students" -> False (General recommendations are fine)
  - "Explain how LLMs work" -> False
  - "As of 2025, explain X (timeless topic)" -> False
  - "History of Rome" -> False


Format your output as a JSON object matching this structure:
{format_instructions}

User Context/Preferences:
{user_preferences}

User Feedback (Previous Clarifications):
{user_feedback}
"""),
            ("user", "{request}")
        ])

    def invoke(self, state: WorkflowState) -> dict:
        """
        Execute the planning logic.
        """
        print(f"[{self.name}] Planning for request: {state['user_request']}")
        
        # Format preferences
        prefs_str = "None"
        if state.get("user_preferences"):
            prefs_str = "\n".join([f"- {k}: {v}" for k, v in state["user_preferences"].items()])
            
        # Format feedback
        feedback_str = "None"
        if state.get("user_feedback"):
            fb = state["user_feedback"]
            # Format nicely: "Question ID: Response"
            if "responses" in fb:
                 feedback_str = "\n".join([f"- Q: {k}, A: {v}" for k, v in fb["responses"].items()])
            else:
                 feedback_str = str(fb)
        
        # Format the prompt
        chain = self.prompt | self.llm | self.parser
        
        try:
            # Invoke the LLM
            result = chain.invoke({
                "request": state['user_request'],
                "user_preferences": prefs_str,
                "user_feedback": feedback_str,
                "format_instructions": self.parser.get_format_instructions()
            })
            
            print(f"[{self.name}] Feedback String: {feedback_str}")
            print(f"[{self.name}] LLM Result: {result}")
            
            # --- DETERMINISTIC OVERRIDE ---
            # If we received specific feedback, we FORCE the system to proceed, 
            # effectively ignoring the LLM if it tries to ask for clarification again on the same topic.
            # This prevents infinite loops where the LLM is never satisfied.
            if feedback_str != "None" and result.get("clarification_needed") == True:
                print(f"[{self.name}] ⚠️ FORCE OVERRIDE: Feedback detected. Overruling LLM's request for more clarification.")
                result["clarification_needed"] = False
                # If steps are missing because it wanted to clarify, we might need to fallback or ask it to generate steps?
                # The LLM usually outputs steps even when asking for clarification, or we can assume a default plan.
                # A safer bet is to re-prompt or just accept the steps it likely generated.
                if not result.get("steps"):
                     # Emergency Plan if LLM refused to make one
                     result["steps"] = [
                         {"step_id": 1, "description": f"Research the user's request: {state['user_request']}", "agent": "Researcher", "required_info": "Search results"},
                         {"step_id": 2, "description": "Synthesize findings", "agent": "Synthesizer", "required_info": "Summary"}
                     ]
            
            # Update state based on result
            updates = {}
            
            if result.get("clarification_needed"):
                updates["status"] = "awaiting_clarification"
                
                # PERSIST QUESTIONS TO CHAT HISTORY
                # This ensures the question doesn't disappear after the user answers.
                current_history = state.get("chat_history", [])
                
                # Format questions nicely
                questions = result.get("clarification_questions", [])
                q_text = "**I need a few more details to create the best plan for you:**\n\n" + \
                         "\n".join([f"- {q}" for q in questions])
                
                # Avoid duplicates if we re-run planner
                # Check if ANY message in history already has the specific header.
                # The LLM output varies (nondeterministic), so we check the static header "I need a few more details".
                header_text = "**I need a few more details to create the best plan for you:**"
                
                already_asked = False
                if current_history:
                     for msg in current_history:
                         if msg.get("role") == "assistant" and header_text in msg.get("content", ""):
                             already_asked = True
                             break
                
                if not already_asked:
                    current_history.append({"role": "assistant", "content": q_text})
                    updates["chat_history"] = current_history
                else:
                    print(f"[{self.name}] Skipping duplicate clarification persistence.")
                
                updates["planner_output"] = result
                updates["freshness_requirements"] = {
                    "required": result.get("freshness_required", False),
                    "reasoning": result.get("freshness_reasoning", "Default")
                }
            else:
                updates["status"] = "researching" # Or whatever the first step implies
                updates["planner_output"] = result
                updates["freshness_requirements"] = {
                    "required": result.get("freshness_required", False),
                    "reasoning": result.get("freshness_reasoning", "Default")
                }
                
            return updates
            
            return updates
            
        except OutputParserException:
            print(f"[{self.name}] ⚠️ JSON Parsing failed. Falling back to default plan.")
            # Fallback plan
            default_plan = {
                "goal": state['user_request'],
                "steps": [
                    {"step_id": 1, "description": f"Research: {state['user_request']}", "agent": "Researcher", "required_info": "Search results"},
                    {"step_id": 2, "description": "Synthesize answer", "agent": "Synthesizer", "required_info": "Summary"}
                ],
                "clarification_needed": False,
                "clarification_questions": [],
                "freshness_required": True, # Assume true for safety
                "freshness_reasoning": "Parsing failed, defaulting to fresh search"
            }
            return {
                "status": "researching",
                "planner_output": default_plan,
                "freshness_requirements": {
                    "required": True,
                    "reasoning": "Fallback"
                }
            }
        except Exception as e:
            print(f"[{self.name}] Error during planning: {e}")
            return {"status": "failed", "validation_errors": [{"agent": self.name, "error": str(e)}]}
