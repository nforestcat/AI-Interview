from google import genai
from typing import Optional
from agents.base_agent import BaseAgent
from prompts.templates import (
    TECH_INTERVIEWER_PROMPT,
    HR_INTERVIEWER_PROMPT,
    EXEC_INTERVIEWER_PROMPT,
    ANALYST_PROMPT
)

class TechAgent(BaseAgent):
    """
    Agent_Tech: Focuses on technical skills, projects, and troubleshooting.
    """
    def __init__(self, session_id: str, model: str = "gemma-4-31b-it", client: Optional[genai.Client] = None):
        super().__init__(
            agent_name="Agent_Tech", 
            session_id=session_id, 
            intent=TECH_INTERVIEWER_PROMPT,
            model=model,
            client=client
        )

class HRAgent(BaseAgent):
    """
    Agent_HR: Focuses on organizational fit, personality, and communication.
    """
    def __init__(self, session_id: str, model: str = "gemma-4-31b-it", client: Optional[genai.Client] = None):
        super().__init__(
            agent_name="Agent_HR", 
            session_id=session_id, 
            intent=HR_INTERVIEWER_PROMPT,
            model=model,
            client=client
        )

class ExecAgent(BaseAgent):
    """
    Agent_Exec: Focuses on long-term vision, loyalty, and pressure handling.
    """
    def __init__(self, session_id: str, model: str = "gemma-4-31b-it", client: Optional[genai.Client] = None):
        super().__init__(
            agent_name="Agent_Exec", 
            session_id=session_id, 
            intent=EXEC_INTERVIEWER_PROMPT,
            model=model,
            client=client
        )

class AnalystAgent(BaseAgent):
    """
    Agent_Analyst: Provides real-time feedback and evaluation in JSON format.
    """
    def __init__(self, session_id: str, model: str = "gemma-4-31b-it", client: Optional[genai.Client] = None):
        super().__init__(
            agent_name="Agent_Analyst", 
            session_id=session_id, 
            intent=ANALYST_PROMPT,
            model=model,
            client=client
        )
