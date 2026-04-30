import pdfplumber
import re
from core.logger import get_logger

logger = get_logger("PDFParser")

class PDFParser:
    @staticmethod
    def extract_text(file_path: str) -> str:
        """pdfplumber를 사용하여 PDF 파일에서 텍스트와 표(Table) 데이터를 정밀하게 추출합니다."""
        logger.info(f"📄 PDF 파싱 시작: {file_path}")
        
        try:
            full_text = ""
            with pdfplumber.open(file_path) as pdf:
                for page_num, page in enumerate(pdf.pages, 1):
                    # 1. 일반 텍스트 추출
                    page_text = page.extract_text()
                    if page_text:
                        full_text += f"\n[Page {page_num} 본문]\n"
                        full_text += page_text + "\n"
                    
                    # 2. 표(Table) 데이터 추출 (Resumes often use tables for layout)
                    tables = page.extract_tables()
                    if tables:
                        full_text += f"\n[Page {page_num} 표 데이터]\n"
                        for table in tables:
                            for row in table:
                                clean_row = [str(cell).replace('\n', ' ').strip() if cell else "" for cell in row]
                                if any(clean_row):
                                    full_text += " | ".join(clean_row) + "\n"
                            full_text += "\n"

            # 3. 토큰 최적화: 3번 이상 연속된 줄바꿈을 2번으로 압축
            full_text = re.sub(r'\n{3,}', '\n\n', full_text)
            
            logger.info(f"✅ PDF 파싱 완료 (총 {len(pdf.pages)}페이지)")
            return full_text.strip()
            
        except Exception as e:
            logger.error(f"❌ PDF 추출 오류: {str(e)}")
            return f"PDF 추출 오류: {str(e)}"
