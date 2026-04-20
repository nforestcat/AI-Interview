from google.genai import types
from prompts.templates import COMPANY_SEARCH_PROMPT, COMPANY_SEARCH_INSTRUCTION

class SearchUtils:
    def __init__(self, client, model_name='gemma-4-26b-a4b-it'):
        self.client = client
        self.model_name = model_name

    def search_company_info(self, company_name: str) -> str:
        """실시간 구글 검색을 통해 기업 정보를 수집합니다."""
        prompt = COMPANY_SEARCH_PROMPT.format(company_name=company_name)
        
        google_search_tool = types.Tool(google_search=types.GoogleSearch())

        response = self.client.models.generate_content(
            model=self.model_name,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=COMPANY_SEARCH_INSTRUCTION,
                tools=[google_search_tool]
            )
        )
        
        return f"# [기업 정보] {company_name}\n\n" + response.text
