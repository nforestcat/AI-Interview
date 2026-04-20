import json
import re
from typing import List
from pydantic import BaseModel, Field, ValidationError
from google.genai import types
from prompts.templates import (
    EXPERIENCE_ANALYSIS_PROMPT, 
    EXPERIENCE_ANALYSIS_INSTRUCTION,
    DRAFT_GEN_PROMPT,
    DRAFT_GEN_INSTRUCTION
)
from core.logger import get_logger

# 로거 설정
logger = get_logger("LLMEngine")

# AI 응답 구조 정의
class ExperienceAnalysis(BaseModel):
    is_sufficient: bool = Field(description="정보가 충분한지 여부")
    fit_analysis: str = Field(description="Step 1: 문항 의도 및 기업 핏(Fit) 연결 분석 결과")
    evaluation_checklists: List[str] = Field(description="Step 2: 수립된 3가지 맞춤형 평가 기준 리스트")
    follow_up_question: str = Field(description="Step 3: 내용 평가에 따른 면접관의 부드러운 꼬리 질문")
    extracted_star: str = Field(description="추출된 STAR 구조 데이터")
    future_roadmap_plan: str = Field(description="입사 후 포부 전략")
    question_keyword: str = Field(description="파일명용 짧은 한국어 키워드")

class LLMEngine:
    def __init__(self, client, model_name='gemma-4-31b-it'):
        self.client = client
        self.model_name = model_name

    def _extract_json(self, text: str) -> str:
        """응답 텍스트에서 순수 JSON 부분만 안전하게 추출합니다."""
        text = text.replace("```json", "").replace("```", "").strip()
        match = re.search(r"(\{.*\})", text, re.DOTALL)
        if match: 
            return match.group(1)
        return text

    def classify_question(self, question: str) -> str:
        """자소서 문항을 7가지 빈출 유형으로 상세 분류합니다."""
        logger.info("🏷️ 7단계 문항 성격 정밀 분류 시작")
        prompt = f"""다음 자소서 문항이 어떤 유형에 속하는지 판단하여 숫자만 출력하세요.
        문항: {question}
        
        1: 지원동기 (회사 지원 이유, 입사 후 포부, 직무 선택 이유 등)
        2: 직무경험 (문제 해결, 프로젝트 경험, 실무 역량, 협업 경험 등)
        3: 성격장단점 (본인의 성격적 특징, 생활 신조, 장단점 등)
        4: 팀워크/갈등해결 (공동 목표 달성 과정, 의견 차이 조율, 협력 사례 등)
        5: 도전/실패극복 (새로운 도전, 실패 사례, 회복 탄력성, 레슨런 등)
        6: 직무전문성 (보유 지식, 기술, 연구 경험, 특화된 Hard Skill 증명 등)
        7: 산업/사회이슈 (최근 이슈에 대한 견해, 가치관, 인사이트 등)
        
        출력 형식: 숫자 하나만 출력 (예: 4)"""
        
        response = self.client.models.generate_content(
            model='gemma-3-12b-it',
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.0,
                max_output_tokens=10,
            ),
        )
        
        result = response.text.strip()
        mapping = {
            "1": "지원동기", "2": "직무경험", "3": "성격장단점", 
            "4": "팀워크/갈등해결", "5": "도전/실패극복", "6": "직무전문성", "7": "산업/사회이슈"
        }
        classified_type = mapping.get(result, "직무경험") # 기본값
        logger.info(f"🏷️ 정밀 분류 결과: {classified_type}")
        return classified_type

    def analyze_experience(self, user_data: dict, company_info: str) -> ExperienceAnalysis:
        """실무 면접관 관점에서 경험을 정밀 분석합니다."""
        logger.info(f"📡 API 호출 시작 (모델: {self.model_name})")
        
        prompt = EXPERIENCE_ANALYSIS_PROMPT.format(
            company_name=user_data['company'],
            company_info=company_info,
            question=user_data['question'],
            experience=user_data['experience'],
            feedback_answer=user_data.get('feedback_answer', '없음')
        )

        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction="당신은 냉철하지만 따뜻한 커리어 컨설턴트(omg-analyst)입니다. 반드시 JSON으로만 응답하세요.",
                    response_mime_type="application/json",
                    response_schema=ExperienceAnalysis,
                    temperature=0.2,
                    top_p=0.8,
                    max_output_tokens=8196,
                ),
            )
            
            if not response or not response.text:
                raise ValueError("API 응답이 비어있습니다.")
                
            clean_json = self._extract_json(response.text)
            return ExperienceAnalysis.model_validate_json(clean_json)

        except Exception as e:
            logger.error(f"❌ 분석 중 오류 발생: {str(e)}")
            return self._get_fallback_analysis()

    def _get_fallback_analysis(self) -> ExperienceAnalysis:
        return ExperienceAnalysis(
            is_sufficient=False,
            fit_analysis="⚠️ AI 분석 오류",
            evaluation_checklists=["내용을 다시 확인해 주세요."],
            follow_up_question="분석 중 오류가 발생했습니다. 내용을 조금 다듬어서 다시 시도해 주세요.",
            extracted_star="N/A",
            future_roadmap_plan="N/A",
            question_keyword="재시도"
        )

    def generate_draft(self, user_data: dict, analysis: ExperienceAnalysis, classified_type: str, target_length: int) -> str:
        """7대 유형 및 A/B/C 그룹 로직을 적용하여 최종 초안을 작성합니다."""
        from prompts.templates import STRUCTURE_INSTRUCTIONS, TEMPLATE_GROUPS

        # 유형별 그룹 라우팅 로직
        group_mapping = {
            "직무경험": "A_직무역량", "직무전문성": "A_직무역량",
            "성격장단점": "B_인성태도", "팀워크/갈등해결": "B_인성태도", "도전/실패극복": "B_인성태도",
            "지원동기": "C_로열티가치관", "산업/사회이슈": "C_로열티가치관"
        }
        group_key = group_mapping.get(classified_type, "A_직무역량")
        group_info = TEMPLATE_GROUPS[group_key]

        prompt = DRAFT_GEN_PROMPT.format(
            company_name=user_data['company'],
            role=user_data['role'],
            classified_type=classified_type,
            template_group=group_key,
            target_length=target_length,
            fit_analysis=analysis.fit_analysis,
            extracted_star=analysis.extracted_star,
            future_roadmap_plan=analysis.future_roadmap_plan,
            structure_instruction=STRUCTURE_INSTRUCTIONS.get(classified_type, ""),
            ratio_instruction=group_info["ratio"],
            special_instruction=group_info["special"]
        )

        response = self.client.models.generate_content(
            model=self.model_name,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=DRAFT_GEN_INSTRUCTION,
                temperature=0.7,
            ),
        )
        return response.text
