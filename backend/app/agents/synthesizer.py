"""
Synthesizer Agent: Combines all gathered information into a final response.
"""
from typing import Dict, Any
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from app.agents.base import BaseAgent
from app.schemas import WorkflowState

class SynthesizerAgent(BaseAgent):
    """
    The Synthesizer Agent takes the plan, research inputs, and user request 
    to create a coherent, final response.
    """
    
    def __init__(self):
        super().__init__(temperature=0.5)
        self.parser = StrOutputParser()
        
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert Synthesizer.
Your goal is to compile all the information gathered by other agents and produce a final, comprehensive response to the user's request.

CRITICAL INSTRUCTIONS:
1. **Source of Truth**: You MUST strictly use the 'Research Findings' provided. Do not invent prices, dates, or facts.
2. **Formatting**: Output valid Markdown. Use bolding for key figures, lists for readability, and headers for sections.
3. **Missing Data**: If the research findings say "NO RESULTS" or "I could not find", you must state that clearly in your answer. Do NOT guess.
4. **Citations**: If sources are provided in the research findings, link to them.
5. **Tone**: Professional, concise, and helpful.

Current Date: {date}
"""),
            ("user", """User Request: {request}

Plan: {plan}

Research Findings: {research_output}

Generate the final response.""")
        ])

    def invoke(self, state: WorkflowState) -> dict:
        """
        Synthesize final output.
        """
        print(f"[{self.name}] Synthesizing final response...")
        
        from datetime import datetime
        current_date_str = datetime.now().strftime("%B %d, %Y")
        
        try:
            # Prepare context
            plan_str = str(state.get('planner_output')) if state.get('planner_output') else "No plan available."
            research_str = str(state.get('researcher_output')) if state.get('researcher_output') else "No research findings."
            
            chain = self.prompt | self.llm | self.parser
            
            result = chain.invoke({
                "request": state['user_request'],
                "plan": plan_str,
                "research_output": research_str,
                "date": current_date_str
            })
            
            # Store final output in a structured way if needed, 
            # for now we put it in final_output dict
            return {
                "synthesizer_output": {"response": result},
                "status": "completed",
                "final_output": {"response": result}
            }
            
        except Exception as e:
            print(f"[{self.name}] Error during synthesis: {e}")
            return {"validation_errors": [{"agent": self.name, "error": str(e)}]}
