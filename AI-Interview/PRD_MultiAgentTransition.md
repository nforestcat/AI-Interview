# PRD: Transition to Robust OmG-Powered Multi-Agent AI Interview System

## 1. Problem Statement
The current AI Interview system simulates a multi-agent environment by prepending system instructions to standard Gemini CLI calls. This "pseudo-multi-agent" approach suffers from several limitations:
- **Context Leakage**: High risk of "persona bleeding" where one interviewer's style or previous system instructions contaminate another's response.
- **Manual State Management**: Session management is handled manually in the application layer, leading to fragile handoffs and complex logic for maintaining conversation continuity.
- **Inconsistent Feedback**: The Analyst agent shares the same execution path as the interviewers, which can lead to mixed output or slower responsiveness.
- **Maintenance Complexity**: Adding or modifying agents requires deep changes to the core engine rather than configuration-based agent definitions.

## 2. Scope and Non-goals
### Scope
- **Formal Agent Definition**: Define and register 4 distinct OmG agents: `Agent_Tech`, `Agent_HR`, `Agent_Exec`, and `Agent_Analyst`.
- **Isolated Session Management**: Implement separate Gemini CLI sessions for each interview instance and a dedicated "sidecar" session for the Analyst.
- **Structured Handoff Mechanism**: Develop a reliable protocol for passing interview context and "handoff summaries" when switching between interviewer agents.
- **Optimized Feedback Loop**: Ensure the Analyst agent operates independently of the main chat flow to provide real-time, non-blocking feedback.

### Non-goals
- Changing the primary UI framework (Streamlit).
- Replacing the core LLM (Gemini 3.1 Pro Preview).
- Implementing video or audio interview features in this phase.
- Modifying the initial enterprise/resume search and parsing logic (already functional).

## 3. Acceptance Criteria

### 3.1 Agent Isolation
- **Separate Personas**: Each agent must strictly adhere to its defined persona (Tech, HR, Exec, Analyst) without "bleeding" traits from others.
- **Session Integrity**:
  - The Interviewer agents must share a common "Interview Session" context but maintain unique "turn-based" instructions.
  - The Analyst agent MUST operate in a completely separate session to avoid evaluating its own evaluation or interfering with the chat history.
- **Command-Line Precision**: Every `gemini ask` or `omg` call must include the `--session` and `--intent` (or equivalent system instruction) flags to ensure context isolation.

### 3.2 Handoff Accuracy
- **Context Continuity**: When transitioning (e.g., Tech -> HR), the new agent must receive a summary of the previous interaction to avoid repetitive questions.
- **Seamless Transition**: The user should not see system-level handoff messages. The "Next Question" should naturally flow from the previous answer or bridge the gap between personas (e.g., "Moving from technical details to your team experience...").
- **State Persistence**: Current active agent, turn count, and handoff metadata must be tracked in the session state to ensure recovery if the app restarts.

### 3.3 Feedback Reliability
- **Strict JSON Enforcement**: The Analyst agent must return valid, parsable JSON 100% of the time.
- **Schema Compliance**: The output must contain:
  - `evaluation`: {`clarity`, `evidence`, `intent_match`}
  - `evaluation_detail`: {`clarity`, `evidence`, `intent_match`}
  - `check_items`: List of strings.
  - `improvement_guide`: Detailed string.
  - `model_answer_direction`: Detailed string.
- **Content Quality**: Feedback must directly reference the user's specific answer and the interviewer's specific question, avoiding generic templates.

### 3.4 UI Responsiveness
- **Streaming Feedback**: The Analyst's JSON output (or its parsed parts) must stream into the "Live Feedback" panel in real-time.
- **Low Latency Transitions**: The switch between interviewers and the generation of the next question must occur within < 5 seconds.
- **Non-blocking Feedback**: User should be able to see the feedback starting to appear even as the next interviewer is preparing their question.

## 4. Constraints and Dependencies
- **OmG Framework**: Relies on the Gemini CLI extension for session and agent management.
- **Environment**: Must function within a PowerShell-based environment (chcp 65001).
- **Rate Limits**: Must handle potential Gemini API rate limits gracefully during concurrent agent calls (Interview vs Analyst).
- **Concurrency**: Streamlit's execution model must be managed to allow background/simultaneous updates of chat and feedback.

## 5. Handoff Checklist
- [ ] Registered 4 agents in `agents/` or via a centralized agent config.
- [ ] Refactored `InterviewEngine` to use `--session` and agent-specific tags.
- [ ] Verified JSON parsing robustness for the Analyst output.
- [ ] Implemented the "Context Bridge" for interviewer handoffs.
- [ ] Tested UI for smooth streaming and concurrent state updates.
