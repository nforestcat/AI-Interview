import json
import re
import datetime
from google.genai import types
from prompts.templates import COMPANY_SEARCH_PROMPT, COMPANY_SEARCH_INSTRUCTION
from core.logger import get_logger

logger = get_logger("SearchUtils")

class SearchUtils:
    def __init__(self, client, model_name='gemma-4-26b-a4b-it'):
        self.client = client
        self.model_name = model_name

    def _extract_json(self, text: str) -> str:
        """응답 텍스트에서 순수 JSON 부분만 안전하게 추출합니다."""
        text = text.replace("```json", "").replace("```", "").strip()
        match = re.search(r"(\{.*\})", text, re.DOTALL)
        if match: 
            return match.group(1)
        return text

    def search_company_info(self, company_name: str) -> dict:
        """실시간 구글 검색을 통해 기업 정보를 수집하여 JSON 객체로 반환합니다."""
        logger.info(f"🔍 '{company_name}' 구글 실시간 검색 시작")
        prompt = COMPANY_SEARCH_PROMPT.format(company_name=company_name)
        
        google_search_tool = types.Tool(google_search=types.GoogleSearch())
        
        response_text = ""

        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=COMPANY_SEARCH_INSTRUCTION,
                    tools=[google_search_tool],
                    response_mime_type="application/json"
                )
            )
            response_text = response.text if hasattr(response, 'text') else ""
            
            clean_json = self._extract_json(response_text)
            company_data = json.loads(clean_json)
            
            # 검색을 수행한 시점을 최종 업데이트 날짜로 지정
            company_data["last_updated"] = datetime.datetime.now().strftime("%Y-%m-%d")
            logger.info(f"✅ '{company_name}' 구글 검색 완료 및 JSON 파싱 성공")
            return company_data
        except Exception as e:
            logger.error(f"❌ '{company_name}' 구글 검색 및 파싱 실패: {e}")
            return {
                "company_name": company_name,
                "target_division": "",
                "vision_mission": "정보를 불러오는 중 오류가 발생했습니다.",
                "core_values": [],
                "ideal_candidate": [],
                "organizational_culture": [],
                "business_strategy": [],
                "tech_roadmap": [],
                "recent_issues": [],
                "last_updated": datetime.datetime.now().strftime("%Y-%m-%d"),
                "raw_text": response_text or str(e)
            }

    def format_company_info_for_llm(self, company_data: dict) -> str:
        """JSON 데이터를 LLM이 이해하기 쉬운 마크다운 문자열로 변환합니다."""
        if isinstance(company_data, str):
            return company_data
            
        md = f"# [기업 정보] {company_data.get('company_name', '알 수 없음')}\n\n"
        md += f"## 🏢 사업 부문\n{company_data.get('target_division', '-')}\n\n"
        md += f"## 🎯 비전 및 미션\n{company_data.get('vision_mission', '-')}\n\n"
        
        md += "## ✨ 핵심 가치\n"
        for val in company_data.get('core_values', []):
            md += f"- {val}\n"
        md += "\n"
        
        md += "## 👤 인재상\n"
        for trait in company_data.get('ideal_candidate', []):
            md += f"- {trait}\n"
        md += "\n"
        
        md += "## 🚀 주요 사업 전략\n"
        for strategy in company_data.get('business_strategy', []):
            md += f"- **{strategy.get('title')}**: {strategy.get('description')}\n"
        md += "\n"
        
        md += "## 🛠️ 기술 로드맵\n"
        for tech in company_data.get('tech_roadmap', []):
            md += f"- {tech}\n"
        md += "\n"
        
        md += "## 📰 최근 이슈\n"
        for issue in company_data.get('recent_issues', []):
            md += f"- **{issue.get('issue')}**: {issue.get('impact')}\n"
        
        return md
