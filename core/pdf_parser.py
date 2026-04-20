import pdfplumber
from core.logger import get_logger

logger = get_logger("PDFParser")

class PDFParser:
    @staticmethod
    def extract_text(file_path: str) -> str:
        """PDF 파일에서 텍스트를 추출합니다."""
        text = ""
        try:
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
            logger.info(f"Successfully extracted text from {file_path}")
        except Exception as e:
            logger.error(f"Error extracting text from {file_path}: {e}")
        return text.strip()
