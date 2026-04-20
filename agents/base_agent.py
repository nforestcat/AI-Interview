from google import genai
from google.genai import types
import os
from typing import Generator, Optional

class BaseAgent:
    """
    Base class for GenAI API-based agents.
    """
    def __init__(self, 
                 agent_name: str, 
                 session_id: str, 
                 intent: str, 
                 model: str = "gemma-4-31b-it", 
                 client: Optional[genai.Client] = None):
        """
        Initialize the agent with a name, a session_id, and a specific intent (persona).
        """
        self.agent_name = agent_name
        self.session_id = session_id
        self.intent = intent
        self.model = model
        
        # Initialize client if not provided
        if client:
            self.client = client
        else:
            api_key = os.environ.get("GOOGLE_API_KEY")
            self.client = genai.Client(api_key=api_key)

    def ask(self, prompt: str) -> str:
        """
        Send a synchronous request to the Gemini API.
        """
        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=self.intent,
                    temperature=0.7,
                )
            )
            return response.text
        except Exception as e:
            return f"Error during Gemini API call: {str(e)}"

    def ask_stream(self, prompt: str) -> Generator[str, None, None]:
        """
        Send a streaming request to the Gemini API.
        """
        try:
            response = self.client.models.generate_content_stream(
                model=self.model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=self.intent,
                    temperature=0.7,
                )
            )
            for chunk in response:
                if chunk.text:
                    yield chunk.text
        except Exception as e:
            yield f"\n[Error]: {str(e)}"
