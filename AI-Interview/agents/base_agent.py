import subprocess
import os
import tempfile
from typing import Generator

class BaseAgent:
    """
    Base class for OmG-style agents using Gemini CLI.
    Handles communication with the 'gemini' command line tool via STDIN.
    """
    def __init__(self, agent_name: str, session_id: str, intent: str, model: str = None, quiet: bool = True):
        """
        Initialize the agent with a name, a session_id (used for logging), and a specific intent.
        
        Args:
            agent_name (str): The name of the agent (e.g., Agent_Tech).
            session_id (str): Identifier for the session (used for tracking, but not passed to -r).
            intent (str): The core objective/focus for the agent.
            model (str): The model name to use.
            quiet (bool): Whether to use quiet mode.
        """
        self.agent_name = agent_name
        self.session_id = session_id
        self.intent = intent
        self.model = model
        self.quiet = quiet

    def _get_strict_prompt(self, user_prompt: str) -> str:
        """Construct the prompt for the formal OmG agent."""
        return (
            f"[SYSTEM DIRECTIVE]\n"
            f"Agent Name: {self.agent_name}\n"
            f"Core Intent: {self.intent}\n\n"
            "You MUST NOT act as an AI developer assistant. You MUST NOT use any tools. "
            "You MUST strictly follow the user's prompt below and output exactly what is requested, "
            "without any conversational filler, greetings, or meta-commentary.\n\n"
            f"[USER PROMPT]\n{user_prompt}"
        )

    def ask(self, prompt: str) -> str:
        """
        Send a synchronous request to the Gemini CLI.
        """
        strict_prompt = self._get_strict_prompt(prompt)
            
        env = os.environ.copy()
        env["NODE_TLS_REJECT_UNAUTHORIZED"] = "0"
            
        # We handle history manually in the engine, so we don't use -r (resume session)
        # to avoid "Invalid session identifier" errors for new sessions.
        cmd = ["gemini.cmd", "-p", " "]
        if self.model:
            cmd.extend(["-m", self.model])
            
        try:
            # Direct execution with STDIN injection to bypass shell escape and encoding issues
            result = subprocess.run(
                cmd,
                input=strict_prompt,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                check=True,
                env=env,
                shell=True
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            error_msg = e.stderr.strip() if e.stderr else str(e)
            return f"Error during Gemini CLI call: {error_msg}"
        except Exception as e:
            return f"Unexpected error: {str(e)}"

    def ask_stream(self, prompt: str) -> Generator[str, None, None]:
        """
        Send a streaming request to the Gemini CLI.
        """
        strict_prompt = self._get_strict_prompt(prompt)
            
        env = os.environ.copy()
        env["NODE_TLS_REJECT_UNAUTHORIZED"] = "0"
            
        cmd = ["gemini.cmd", "-p", " "]
        if self.model:
            cmd.extend(["-m", self.model])
            
        try:
            # Stream via STDIN pipe
            process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8',
                errors='replace',
                bufsize=1,
                env=env,
                shell=True
            )

            # Write prompt and close stdin to signal EOF
            process.stdin.write(strict_prompt)
            process.stdin.close()

            for line in iter(process.stdout.readline, ''):
                if line:
                    yield line

            process.stdout.close()
            process.wait()

            if process.returncode != 0:
                stderr_content = process.stderr.read()
                if stderr_content:
                    yield f"\n[Error]: {stderr_content}"
        except Exception as e:
            yield f"\n[Error]: {str(e)}"
