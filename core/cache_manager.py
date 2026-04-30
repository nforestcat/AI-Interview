import os
import re
import json
import datetime
from core.logger import get_logger

logger = get_logger("CacheManager")

class CacheManager:
    def __init__(self):
        self.cache_root = ".cache"
        self.company_dir = os.path.join(self.cache_root, "company")
        self.draft_dir = os.path.join(self.cache_root, "draft")
        self._ensure_dirs()

    def _ensure_dirs(self):
        """필요한 디렉토리가 없으면 생성합니다."""
        for d in [self.cache_root, self.company_dir, self.draft_dir]:
            if not os.path.exists(d):
                os.makedirs(d)

    def get_safe_filename(self, name: str) -> str:
        """파일명으로 사용할 수 없는 문자를 제거합니다."""
        return re.sub(r'[\\/*?:"<>|]', "_", name).strip()

    def is_cache_expired(self, last_updated_str: str, days: int = 30) -> bool:
        """캐시가 지정된 날짜보다 오래되었는지 확인합니다."""
        if not last_updated_str:
            return True
        try:
            # 날짜 부분만 추출 (예: 2026-04-29)
            date_part = last_updated_str[:10] 
            last_updated = datetime.datetime.strptime(date_part, "%Y-%m-%d")
            delta = datetime.datetime.now() - last_updated
            return delta.days > days
        except Exception as e:
            logger.warning(f"⚠️ 날짜 파싱 실패 ('{last_updated_str}'): {e}")
            return True

    def load_company_data(self, company_name: str):
        """로컬에 저장된 기업 정보(JSON)를 불러옵니다."""
        safe_name = self.get_safe_filename(company_name)
        
        # 1. 신규 JSON 형식 확인
        json_path = os.path.join(self.company_dir, f"{safe_name}.json")
        if os.path.exists(json_path):
            try:
                with open(json_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if not self.is_cache_expired(data.get("last_updated", "")):
                        return data
                    logger.info(f"⌛ '{company_name}' 캐시 만료됨 (재검색 필요)")
            except Exception as e:
                logger.warning(f"⚠️ '{company_name}' JSON 캐시 읽기 실패: {e}")

        # 2. 하위 호환성: 기존 MD 형식 확인
        md_path = os.path.join(self.company_dir, f"{safe_name}.md")
        if os.path.exists(md_path):
            try:
                with open(md_path, "r", encoding="utf-8") as f:
                    return f.read() # 문자열 반환
            except Exception as e:
                logger.warning(f"⚠️ '{company_name}' MD 캐시 읽기 실패: {e}")
                
        return None

    def save_company_data(self, company_name: str, data):
        """기업 정보(JSON 또는 문자열)를 로컬에 저장합니다."""
        safe_name = self.get_safe_filename(company_name)
        
        if isinstance(data, dict):
            file_path = os.path.join(self.company_dir, f"{safe_name}.json")
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        else:
            file_path = os.path.join(self.company_dir, f"{safe_name}.md")
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(str(data))

    def delete_company_cache(self, company_name: str) -> bool:
        """특정 기업의 로컬 캐시 파일을 삭제합니다."""
        safe_name = self.get_safe_filename(company_name)
        deleted = False
        for ext in [".json", ".md"]:
            file_path = os.path.join(self.company_dir, f"{safe_name}{ext}")
            if os.path.exists(file_path):
                os.remove(file_path)
                deleted = True
        return deleted

    def save_draft(self, company: str, role: str, q_num: str, keyword: str, content: str) -> str:
        """생성된 초안을 계층형 폴더 구조로 저장합니다."""
        safe_company = self.get_safe_filename(company)
        safe_role = self.get_safe_filename(role)
        target_dir = os.path.join(self.draft_dir, f"{safe_company}_{safe_role}")
        
        if not os.path.exists(target_dir):
            os.makedirs(target_dir, exist_ok=True)
            
        now_str = datetime.datetime.now().strftime("%Y%m%d_%H%M")
        safe_keyword = self.get_safe_filename(keyword)
        filename = f"{q_num}_{safe_keyword}_{now_str}.md"
        
        file_path = os.path.join(target_dir, filename)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        return file_path
