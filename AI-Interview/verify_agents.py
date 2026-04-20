import sys
import os
import json
import time
from core.interview_engine import InterviewEngine
from agents.interview_agents import TechAgent, HRAgent, AnalystAgent

def test_multi_agent():
    session_id = f"test_session_{int(time.time())}"
    print(f"--- Starting Multi-Agent Verification (Session: {session_id}) ---")
    
    engine = InterviewEngine(session_id=session_id)
    
    # 1. Tech Agent Test
    print("\n[Step 1] TechAgent: Asking a technical question...")
    tech_q = engine.tech_agent.ask("이력서에 Python Fast API 경험이 있다고 되어 있는데, 비동기 처리를 어떻게 구현했는지 설명해 주세요.")
    print(f"TechAgent Question: {tech_q[:100]}...")
    
    # 2. HR Agent Test (Session continuity)
    print("\n[Step 2] HRAgent: Switching to HR context but maintaining session...")
    hr_q = engine.hr_agent.ask("방금 기술적인 부분에 대해 답변하셨는데, 그 프로젝트에서 팀원들과 협업할 때 어떤 어려움이 있었나요?")
    print(f"HRAgent Question: {hr_q[:100]}...")
    
    # 3. Analyst Agent Test (Separate session and JSON)
    print("\n[Step 3] AnalystAgent: Requesting JSON feedback...")
    feedback_raw = engine.analyst_agent.ask("질문: 위 프로젝트의 기술적 해결책은? / 답변: asyncio를 사용하여 I/O 바운드 작업을 최적화했습니다.")
    print(f"AnalystAgent Raw Output: {feedback_raw[:100]}...")
    
    try:
        feedback_json = engine.parse_json_response(feedback_raw)
        if "evaluation" in feedback_json:
            print("✅ AnalystAgent returned valid JSON feedback!")
        else:
            print("❌ AnalystAgent JSON schema mismatch.")
    except Exception as e:
        print(f"❌ AnalystAgent JSON parsing failed: {e}")

    print("\n--- Verification Complete ---")

if __name__ == '__main__':
    test_multi_agent()
