import os
import re

class CacheManager:
    def __init__(self):
        self.company_dir = "company"
        self.draft_dir = "draft"
        self._ensure_dirs()

    def _ensure_dirs(self):
        """필요한 디렉토리가 없으면 생성합니다."""
        for d in [self.company_dir, self.draft_dir]:
            if not os.path.exists(d):
                os.makedirs(d)

    def get_safe_filename(self, name: str) -> str:
        """파일명으로 사용할 수 없는 문자를 제거합니다."""
        return re.sub(r'[\\/*?:"<>|]', "_", name).strip()

    def load_company_data(self, company_name: str) -> str:
        """로컬에 저장된 기업 정보를 불러옵니다."""
        safe_name = self.get_safe_filename(company_name)
        file_path = os.path.join(self.company_dir, f"{safe_name}.md")
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                return f.read()
        return ""

    def save_company_data(self, company_name: str, content: str):
        """검색된 기업 정보를 로컬에 저장합니다."""
        safe_name = self.get_safe_filename(company_name)
        file_path = os.path.join(self.company_dir, f"{safe_name}.md")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

    def delete_company_cache(self, company_name: str) -> bool:
        """특정 기업의 로컬 캐시 파일을 삭제합니다."""
        safe_name = self.get_safe_filename(company_name)
        file_path = os.path.join(self.company_dir, f"{safe_name}.md")
        if os.path.exists(file_path):
            os.remove(file_path)
            return True
        return False

    def save_draft(self, company: str, role: str, q_num: str, keyword: str, content: str) -> str:
        """생성된 초안을 계층형 폴더 구조로 저장합니다."""
        safe_company = self.get_safe_filename(company)
        safe_role = self.get_safe_filename(role)
        target_dir = os.path.join(self.draft_dir, f"{safe_company}_{safe_role}")
        
        if not os.path.exists(target_dir):
            os.makedirs(target_dir)
            
        import datetime
        now_str = datetime.datetime.now().strftime("%Y%m%d_%H%M")
        safe_keyword = self.get_safe_filename(keyword)
        filename = f"{q_num}_{safe_keyword}_{now_str}.md"
        
        file_path = os.path.join(target_dir, filename)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        return file_path
