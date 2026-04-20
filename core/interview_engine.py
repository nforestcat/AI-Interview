import json
import subprocess
import os
import random
import time
from typing import List, Dict, Any, Generator
from google import genai
from core.logger import get_logger
from prompts.templates import (
    TECH_INTERVIEWER_PROMPT, 
    HR_INTERVIEWER_PROMPT, 
    EXEC_INTERVIEWER_PROMPT, 
    ANALYST_PROMPT,
    INITIAL_QUESTION_POOL_PROMPT,
    RESUME_PARSER_PROMPT,
    FINAL_REPORT_PROMPT
)
from agents.interview_agents import TechAgent, HRAgent, ExecAgent, AnalystAgent
from agents.base_agent import BaseAgent

logger = get_logger("InterviewEngine")

class InterviewEngine:
    def __init__(self, model_name="gemma-4-31b-it", session_id=None, api_key=None):
        self.model_name = model_name or "gemma-4-31b-it"
        self.session_id = session_id or f"interview_{int(time.time())}"
        self.analyst_session_id = f"analyst_{self.session_id}"
        
        # Initialize GenAI Client
        self.api_key = api_key or os.environ.get("GOOGLE_API_KEY")
        self.client = genai.Client(api_key=self.api_key)
        
        # Initialize specialized agents with shared client
        self.tech_agent = TechAgent(self.session_id, model=self.model_name, client=self.client)
        self.hr_agent = HRAgent(self.session_id, model=self.model_name, client=self.client)
        self.exec_agent = ExecAgent(self.session_id, model=self.model_name, client=self.client)
        self.analyst_agent = AnalystAgent(self.analyst_session_id, model=self.model_name, client=self.client)
        
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
            intent="Extracting and structuring resume data into pure JSON format.",
            model=self.model_name,
            client=self.client
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
            intent="Initial Interview Preparation & Question Pooling",
            model=self.model_name,
            client=self.client
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
                          current_interviewer: str = None,
                          current_count: int = 0,
                          total_count: int = 0) -> Dict[str, Any]:
        """세트 로테이션 로직에 따라 다음 질문을 생성하거나 면접을 종료합니다."""
        
        # 0. 종료 조건 체크 (총 6회 질문 완료 시)
        if total_count >= 6:
            agent = self.agent_map["Agent_Exec"] # 마무리는 임원 면접관이 담당
            prompt = f"""
            [상황] 모든 공식적인 면접 질문 세트가 끝났습니다.
            [지원 기업] {company_info[:100]}
            
            [미션] 아래 예시와 같은 톤으로 지원자를 격려하며 면접을 마무리하는 멘트를 하세요.
            예시: "네, 지원자님. 곤란하고 극단적인 상황을 가정한 압박 질문이 계속 이어졌음에도 불구하고, 끝까지 평정심을 잃지 않고 본인의 철학을 진정성 있게 답변해 주셔서 정말 감사합니다. 저희가 이렇게 강하게 질문드린 이유는, 실제 [기업명]의 서비스 규모에서는 상상 이상의 압박감과 책임감이 따르기 때문입니다. 오늘 지원자님의 기술적 깊이부터 비즈니스 마인드, 그리고 위기 앞에서의 멘탈까지 폭넓게 확인할 수 있는 뜻깊은 시간이었습니다. 고생 많으셨습니다. 혹시 마지막으로 저희에게 궁금한 점 있으신가요?"
            
            반드시 기업명을 언급하고, 지원자의 노력을 치하하며 마지막 '역질문'을 유도하세요.
            """
            question = agent.ask(prompt)
            return {
                "interviewer": "Agent_Exec",
                "question": question.strip(),
                "count": 0,
                "is_final": True
            }

        # 1. 면접관 및 질문 성격 결정
        if current_count == 1 and current_interviewer:
            # 동일한 면접관이 꼬리 질문을 던질 차례 (Set 2/2)
            next_interviewer_key = current_interviewer
            is_follow_up = True
            new_count = 2
        else:
            # 면접관 교체 및 새로운 메인 질문 (Set 1/2)
            next_interviewer_key = self.select_next_interviewer(current_interviewer)
            is_follow_up = False
            new_count = 1

        agent = self.agent_map[next_interviewer_key]
        
        # 2. 문맥 구성을 위한 히스토리 정리 (최근 대화 위주)
        context_history = ""
        for msg in history[-4:]:
            role = "면접관" if msg["role"] == "assistant" else "지원자"
            context_history += f"{role}: {msg['content']}\n"

        # 3. 상황별 프롬프트 구성
        if is_follow_up:
            # 꼬리 질문 프롬프트 (T자형 깊이 추구)
            prompt = f"""
            [상황] 당신({next_interviewer_key})은 방금 질문을 던졌고 지원자의 답변을 들었습니다. 
            [미션] 지원자 답변의 논리적 허점을 파고들거나, 장애 상황/예외 케이스를 가정한 '날카로운 꼬리 질문'을 하나만 하세요.
            [이전 대화]
            {context_history}
            """
        else:
            # 브릿지 메인 질문 프롬프트 (맥락 유지 + 관점 전환)
            bridge_context = ""
            if current_interviewer:
                bridge_context = f"이전에는 {current_interviewer}와 대화했습니다."
            
            prompt = f"""
            [상황] 면접관이 당신({next_interviewer_key})으로 교체되었습니다. {bridge_context}
            [미션] 이전 대화의 맥락(주제)을 자연스럽게 이어받되, 당신의 페르소나 관점에서 검증이 필요한 새로운 메인 질문을 던지세요.
            [지원자 요약] {resume_text[:1000]}
            [이전 대화 내역]
            {context_history}
            """
        
        question = agent.ask(prompt)
        
        return {
            "interviewer": next_interviewer_key, 
            "question": question.strip(),
            "count": new_count
        }

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
        """텍스트에서 가장 큰 유효한 JSON 블록을 추출하여 파싱합니다."""
        import re
        import ast

        def _safe_parse(t: str) -> Dict[str, Any]:
            t = t.strip()
            try:
                return json.loads(t)
            except json.JSONDecodeError:
                try:
                    # 작은따옴표 대응을 위한 literal_eval
                    return ast.literal_eval(t)
                except:
                    return None

        # 1. ```json ... ``` 블록 찾기
        json_blocks = re.findall(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
        for block in json_blocks:
            res = _safe_parse(block)
            if res: return res

        # 2. 가장 바깥쪽 { } 찾기 (Greedy match from first { to last })
        # 텍스트에 여러 개의 {}가 섞여있을 경우를 대비해 루프를 돌며 유효성 검사
        potential_starts = [i for i, char in enumerate(text) if char == '{']
        potential_ends = [i for i, char in enumerate(text) if char == '}']
        
        # 가장 긴 블록부터 시도
        potential_blocks = []
        for s in potential_starts:
            for e in potential_ends:
                if e > s:
                    potential_blocks.append(text[s:e+1])
        
        # 길이 순으로 정렬하여 가장 긴 것부터 파싱 시도
        potential_blocks.sort(key=len, reverse=True)
        
        for block in potential_blocks:
            res = _safe_parse(block)
            if res: return res

        logger.error(f"Failed to find valid JSON in text: {text[:200]}...")
        return {"error": "유효한 JSON 데이터를 찾을 수 없습니다.", "raw": text}

    def generate_final_report(self, history: List[Dict[str, str]], parsed_resume: str, company_info: str) -> str:
        """전체 대화 내역을 바탕으로 최종 종합 평가 리포트를 생성합니다."""
        logger.info("Generating final comprehensive interview report...")
        
        # 대화 내역 포맷팅
        transcript = ""
        for msg in history:
            role = "면접관" if msg["role"] == "assistant" else "지원자"
            name = msg.get("name", role)
            transcript += f"[{name}] {msg['content']}\n"

        prompt = FINAL_REPORT_PROMPT.format(
            parsed_resume=parsed_resume,
            company_info=company_info,
            chat_history=transcript
        )
        
        # 임원 면접관/채용 위원장 에이전트 생성
        final_agent = BaseAgent(
            agent_name="Head_of_Recruiting",
            session_id=f"final_{int(time.time())}",
            intent="Final Interview Evaluation & Report Generation",
            model=self.model_name,
            client=self.client
        )
        
        return final_agent.ask(prompt)
