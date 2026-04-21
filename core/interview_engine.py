import json
import os
import time
from typing import List, Dict, Any, Generator
from google import genai
from core.logger import get_logger
from core.interview_graph import create_interview_graph, InterviewState
from prompts.templates import (
    RESUME_PARSER_PROMPT,
    FINAL_REPORT_PROMPT
)
from core.cache_manager import CacheManager
from agents.base_agent import BaseAgent

logger = get_logger("InterviewEngine")

class InterviewEngine:
    def __init__(self, model_name="gemma-4-31b-it", session_id=None, api_key=None):
        self.model_name = model_name or "gemma-4-31b-it"
        self.session_id = session_id or f"interview_{int(time.time())}"
        
        # Initialize GenAI Client
        self.api_key = api_key or os.environ.get("GOOGLE_API_KEY")
        self.client = genai.Client(api_key=self.api_key)
        
        # Initialize LangGraph
        self.graph = create_interview_graph()
        self.cache_manager = CacheManager()
        
        # Initial State
        self.state = {
            "messages": [],
            "current_agent": "Agent_Tech",
            "context": {
                "model_name": self.model_name,
                "parsed_resume": "",
                "company_info": "",
                "client": self.client  # Client 인스턴스 공유
            },
            "interviewer_counts": {},
            "total_count": 0,
            "is_finished": False
        }

    def clear(self):
        """엔진 상태를 초기화합니다."""
        self.state = {
            "messages": [],
            "current_agent": "Agent_Tech",
            "context": {
                "model_name": self.model_name,
                "parsed_resume": "",
                "company_info": ""
            },
            "interviewer_counts": {},
            "total_count": 0,
            "is_finished": False
        }

    def set_context(self, parsed_resume: str, company_info: str):
        self.state["context"]["parsed_resume"] = parsed_resume
        self.state["context"]["company_info"] = company_info

    def parse_resume(self, resume_text: str) -> str:
        """지원자 서류를 JSON 형태의 마스터 프로필로 구조화합니다."""
        logger.info("Parsing and structuring resume using Agent_Parser...")
        prompt = RESUME_PARSER_PROMPT.format(resume_text=resume_text[:5000])
        parser_agent = BaseAgent(
            agent_name="Agent_Parser", 
            session_id=f"parser_{int(time.time())}", 
            intent="Extracting and structuring resume data into pure JSON format.",
            model=self.model_name,
            client=self.client
        )
        output = parser_agent.ask(prompt)
        try:
            parsed_data = self.parse_json_response(output)
            if "error" not in parsed_data:
                return json.dumps(parsed_data, ensure_ascii=False, indent=2)
            return output
        except:
            return output

    def generate_initial_pool(self, resume_text: str, company_info: str, company_name: str = "Unknown", role_name: str = "Unknown") -> str:
        """지원자 서류와 기업 정보를 분석하여 사전 리포트와 예상 질문을 생성합니다."""
        logger.info(f"Generating pre-analysis report for {company_name}...")
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
        result = analysis_agent.ask(prompt)
        
        # 초안 자동 저장 기능 추가
        try:
            self.cache_manager.save_draft(
                company=company_name,
                role=role_name,
                q_num="00",
                keyword="PreAnalysis",
                content=result
            )
            logger.info(f"Pre-analysis report saved to draft for {company_name}")
        except Exception as e:
            logger.error(f"Failed to save draft: {e}")
            
        return result

    def step(self, user_input: str = None) -> Dict[str, Any]:
        """LangGraph 한 단계를 실행합니다."""
        if user_input:
            self.state["messages"].append({"role": "user", "content": user_input})
        
        # 그래프 실행 (마지막 노드까지 진행)
        # Streamlit에서는 상태 유지가 중요하므로 update를 사용
        output = self.graph.invoke(self.state)
        self.state.update(output)
        
        # 마지막 메시지 (면접관의 질문) 추출
        last_msg = self.state["messages"][-1]
        
        return {
            "interviewer": self.state["current_agent"],
            "question": last_msg["content"],
            "count": self.state["interviewer_counts"].get(self.state["current_agent"], 0),
            "is_final": self.state["total_count"] >= 6
        }

    def get_feedback(self) -> Dict[str, Any]:
        """마지막 분석 노드에서 생성된 피드백을 가져옵니다."""
        raw_feedback = self.state["context"].get("last_feedback_raw", "")
        return self.parse_json_response(raw_feedback)

    def parse_json_response(self, text: str) -> Dict[str, Any]:
        """텍스트에서 가장 큰 유효한 JSON 블록을 추출하여 파싱합니다."""
        import re
        import ast
        def _safe_parse(t: str) -> Dict[str, Any]:
            t = t.strip()
            try: return json.loads(t)
            except json.JSONDecodeError:
                try: return ast.literal_eval(t)
                except: return None
        json_blocks = re.findall(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
        for block in json_blocks:
            res = _safe_parse(block)
            if res: return res
        potential_starts = [i for i, char in enumerate(text) if char == '{']
        potential_ends = [i for i, char in enumerate(text) if char == '}']
        potential_blocks = []
        for s in potential_starts:
            for e in potential_ends:
                if e > s: potential_blocks.append(text[s:e+1])
        potential_blocks.sort(key=len, reverse=True)
        for block in potential_blocks:
            res = _safe_parse(block)
            if res: return res
        return {"error": "유효한 JSON 데이터를 찾을 수 없습니다.", "raw": text}

    def generate_final_report(self, history: List[Dict[str, str]], parsed_resume: str, company_info: str) -> str:
        """전체 대화 내역을 바탕으로 최종 종합 평가 리포트를 생성합니다."""
        logger.info("Generating final report...")
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
        final_agent = BaseAgent(
            agent_name="Head_of_Recruiting",
            session_id=f"final_{int(time.time())}",
            intent="Final Interview Evaluation & Report Generation",
            model=self.model_name,
            client=self.client
        )
        return final_agent.ask(prompt)
