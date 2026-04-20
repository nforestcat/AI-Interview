from typing import Generator
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
    def __init__(self, session_id: str):
        super().__init__(
            agent_name="Agent_Tech", 
            session_id=session_id, 
            intent="Technical Interview & Skill Verification"
        )

    def ask(self, prompt: str) -> str:
        """Sends a technical interview prompt to the OmG agent."""
        return super().ask(prompt)

    def ask_stream(self, prompt: str) -> Generator[str, None, None]:
        """Streams a technical interview response from the OmG agent."""
        return super().ask_stream(prompt)


class HRAgent(BaseAgent):
    """
    Agent_HR: Focuses on organizational fit, personality, and communication.
    """
    def __init__(self, session_id: str):
        super().__init__(
            agent_name="Agent_HR", 
            session_id=session_id, 
            intent="HR Interview & Cultural Fit"
        )

    def ask(self, prompt: str) -> str:
        return super().ask(prompt)

    def ask_stream(self, prompt: str) -> Generator[str, None, None]:
        return super().ask_stream(prompt)


class ExecAgent(BaseAgent):
    """
    Agent_Exec: Focuses on long-term vision, loyalty, and pressure handling.
    """
    def __init__(self, session_id: str):
        super().__init__(
            agent_name="Agent_Exec", 
            session_id=session_id, 
            intent="Executive Interview & Strategic Thinking"
        )

    def ask(self, prompt: str) -> str:
        return super().ask(prompt)

    def ask_stream(self, prompt: str) -> Generator[str, None, None]:
        return super().ask_stream(prompt)


class AnalystAgent(BaseAgent):
    """
    Agent_Analyst: Provides real-time feedback and evaluation in JSON format.
    """
    def __init__(self, session_id: str):
        super().__init__(
            agent_name="Agent_Analyst", 
            session_id=session_id, 
            intent="Real-time Answer Analysis & Feedback"
        )

    def ask(self, prompt: str) -> str:
        """Analyze the user's answer and return JSON feedback."""
        return super().ask(prompt)

    def ask_stream(self, prompt: str) -> Generator[str, None, None]:
        """Stream the JSON analysis feedback."""
        return super().ask_stream(prompt)
