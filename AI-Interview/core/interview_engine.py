import json
import subprocess
import os
import random
import time
from typing import List, Dict, Any, Generator
from core.logger import get_logger
from prompts.templates import (
    TECH_INTERVIEWER_PROMPT, 
    HR_INTERVIEWER_PROMPT, 
    EXEC_INTERVIEWER_PROMPT, 
    ANALYST_PROMPT,
    INITIAL_QUESTION_POOL_PROMPT,
    RESUME_PARSER_PROMPT
)
from agents.interview_agents import TechAgent, HRAgent, ExecAgent, AnalystAgent
from agents.base_agent import BaseAgent

logger = get_logger("InterviewEngine")

class InterviewEngine:
    def __init__(self, model_name=None, session_id=None):
        self.model_name = model_name
        self.session_id = session_id or f"interview_{int(time.time())}"
        self.analyst_session_id = f"analyst_{self.session_id}"
        
        # Initialize specialized agents
        self.tech_agent = TechAgent(self.session_id)
        self.hr_agent = HRAgent(self.session_id)
        self.exec_agent = ExecAgent(self.session_id)
        self.analyst_agent = AnalystAgent(self.analyst_session_id)
        
        self.agent_map = {
            "Agent_Tech": self.tech_agent,
            "Agent_HR": self.hr_agent,
            "Agent_Exec": self.exec_agent
        }

        self.interviewers = {
            "Agent_Tech": TECH_INTERVIEWER_PROMPT,
            "Agent_HR": HR_INTERVIEWER_PROMPT,
            "Agent_Exec": EXEC_INTERVIEWER_PROMPT
        }

    def parse_resume(self, resume_text: str) -> str:
        """지원자 서류를 JSON 형태의 마스터 프로필로 구조화합니다."""
        logger.info("Parsing and structuring resume using Agent_Parser...")

        # RESUME_PARSER_PROMPT를 사용하여 명확한 JSON 포맷을 지시합니다.
        prompt = RESUME_PARSER_PROMPT.format(resume_text=resume_text[:5000])

        # 서류 파싱을 위한 전용 에이전트 사용 (session_id 누락 방지)
        parser_agent = BaseAgent(
            agent_name="Agent_Parser", 
            session_id=f"parser_{int(time.time())}", 
            intent="Extracting and structuring resume data into pure JSON format."
        )
        output = parser_agent.ask(prompt)

        # JSON 형식만 추출
        try:
            parsed_data = self.parse_json_response(output)
            if "error" not in parsed_data:
                return json.dumps(parsed_data, ensure_ascii=False, indent=2)
            return output
        except:
            return output

    def generate_initial_pool(self, resume_text: str, company_info: str) -> str:
        """지원자 서류와 기업 정보를 분석하여 사전 리포트와 예상 질문을 생성합니다."""
        logger.info("Generating pre-analysis report using specialized Analysis Agent...")
        
        # 사전 분석을 위한 전용 에이전트 생성
        temp_session = f"pre_analysis_{int(time.time())}"
        analysis_agent = BaseAgent(
            agent_name="Agent_Tech", 
            session_id=temp_session, 
            intent="Initial Interview Preparation & Question Pooling"
        )

        prompt = f"""
        당신은 채용 전문가로서 다음 데이터를 분석하여 사전 리포트를 작성하세요.

        [지원자 서류]
        {resume_text[:2500]} 

        [지원 기업 정보]
        {company_info[:2500]}

        [수행 작업]
        1. **지원자 강점 분석**: 기업 정보와 대조하여 지원자의 핵심 강점 3가지를 도출하세요.
        2. **면접 검증 포인트**: 서류에서 기술적/논리적으로 검증이 필요한 핵심 포인트를 짚어주세요.
        3. **예상 질문 리스트**: 각 면접관(Tech, HR, Exec) 관점의 날카로운 질문 10개를 생성하세요.
        """
        
        output = analysis_agent.ask(prompt)
        return output

    def get_next_question(self, 
                          history: List[Dict[str, str]], 
                          resume_text: str, 
                          company_info: str, 
                          current_interviewer: str = None) -> Dict[str, str]:
        """전용 에이전트를 통해 다음 면접관의 질문을 생성합니다."""
        next_interviewer_key = self.select_next_interviewer(current_interviewer)
        agent = self.agent_map[next_interviewer_key]
        
        handoff_context = ""
        if current_interviewer and current_interviewer != next_interviewer_key:
            handoff_context = f"\n[Context Bridge] 이전에는 {current_interviewer}가 질문했습니다. 이제 당신({next_interviewer_key})이 바톤을 이어받아 질문할 차례입니다. 자연스럽게 화제를 전환하거나 심화 질문을 던지세요."

        context_history = ""
        # 최근 4턴의 대화 내역 전달
        for msg in history[-4:]:
            role = "면접관" if msg["role"] == "assistant" else "지원자"
            context_history += f"{role}: {msg['content']}\n"

        prompt = f"""
        [상황] 실무 모의 면접 진행 중 {handoff_context}
        [지원자 서류] {resume_text[:1500]}
        [기업 정보] {company_info[:1500]}
        [이전 대화 내역]
        {context_history}
        
        위 문맥을 바탕으로 당신의 페르소나에 맞춰 다음 질문을 하나만 하세요. 
        사용자의 이전 답변이 있다면 그에 대한 꼬리 질문을 우선적으로 고려하세요.
        """
        
        question = agent.ask(prompt)
        
        return {"interviewer": next_interviewer_key, "question": question.strip()}

    def get_feedback_stream(self, last_question: str, user_answer: str, resume_text: str, company_info: str) -> Generator[str, None, None]:
        """AnalystAgent를 통해 실시간 피드백 스트림을 생성합니다."""
        prompt = f"""
        질문: {last_question}
        답변: {user_answer}
        지원자 서류: {resume_text[:1000]}
        기업 정보: {company_info[:1000]}
        
        위 답변을 분석하여 지정된 JSON 형식으로 피드백을 제공하세요.
        """
        return self.analyst_agent.ask_stream(prompt)

    def select_next_interviewer(self, current: str = None) -> str:
        """다음 면접관을 선택합니다 (Tech -> HR -> Exec 순환)."""
        keys = list(self.agent_map.keys())
        if current not in keys:
            return keys[0]
        
        current_idx = keys.index(current)
        next_idx = (current_idx + 1) % len(keys)
        return keys[next_idx]

    def parse_json_response(self, text: str) -> Dict[str, Any]:
        """텍스트에서 JSON 블록을 추출하여 파싱합니다."""
        import re
        import ast

        def _safe_parse(t: str) -> Dict[str, Any]:
            try:
                return json.loads(t)
            except json.JSONDecodeError as e:
                # JSON 규격 위반(작은따옴표 사용 등) 시 파이썬 ast를 이용해 딕셔너리로 안전하게 파싱 시도
                try:
                    return ast.literal_eval(t)
                except Exception:
                    raise e

        try:
            # ```json ... ``` 형태 우선 추출
            json_block_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
            if json_block_match:
                return _safe_parse(json_block_match.group(1))
            # 그냥 { ... } 형태 추출
            json_match = re.search(r"(\{.*\})", text, re.DOTALL)
            if json_match:
                return _safe_parse(json_match.group(1))
            return _safe_parse(text.strip())
        except Exception as e:
            logger.error(f"JSON Parsing Error: {e}")
            return {"error": f"JSON 파싱 실패: {str(e)}", "raw": text}
