import asyncio
import edge_tts
import os
import base64
from google import genai
from core.logger import get_logger

logger = get_logger("SpeechManager")

class SpeechManager:
    def __init__(self, client: genai.Client = None):
        self.client = client
        self.voice = "ko-KR-SunHiNeural"  # 한국어 여성 음성 (권장)
        # ko-KR-InJoonNeural (남성)

    async def generate_tts(self, text: str, output_path: str = "temp_question.mp3"):
        """텍스트를 음성으로 변환하여 파일로 저장합니다."""
        try:
            communicate = edge_tts.Communicate(text, self.voice)
            await communicate.save(output_path)
            return output_path
        except Exception as e:
            logger.error(f"TTS generation failed: {e}")
            return None

    def stt_with_gemini(self, audio_bytes: bytes) -> str:
        """Gemini 3.1 Flash Live를 사용하여 오디오를 텍스트로 변환합니다."""
        if not self.client:
            return "Error: GenAI Client not initialized"
        
        try:
            # Gemini 3.1 Flash Live 모델 사용
            response = self.client.models.generate_content(
                model="gemini-3.1-flash-live",
                contents=[
                    "이 오디오는 면접 지원자의 답변입니다. 한국어로 정확하게 받아쓰기 해주세요. 부가 설명 없이 텍스트만 출력하세요.",
                    {"mime_type": "audio/wav", "data": audio_bytes}
                ]
            )
            return response.text.strip()
        except Exception as e:
            logger.error(f"STT with Gemini failed: {e}")
            return f"Error during STT: {e}"

    def get_audio_html(self, audio_path: str):
        """자동 재생되는 오디오 HTML 태그를 생성합니다."""
        if not os.path.exists(audio_path):
            return ""
        
        with open(audio_path, "rb") as f:
            audio_bytes = f.read()
            
        audio_base64 = base64.b64encode(audio_bytes).decode()
        return f'<audio autoplay="true" src="data:audio/mp3;base64,{audio_base64}">'
