import json
import os
from typing import Dict, Any

class SessionManager:
    def __init__(self, state_dir: str = ".omg/state"):
        self.state_dir = state_dir
        self.session_file = os.path.join(self.state_dir, "app_session.json")
        self._ensure_dir()

    def _ensure_dir(self):
        if not os.path.exists(self.state_dir):
            os.makedirs(self.state_dir)

    def save_session(self, data: Dict[str, Any]):
        """세션 상태를 JSON 파일로 저장합니다."""
        try:
            with open(self.session_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"Error saving session: {e}")

    def load_session(self) -> Dict[str, Any]:
        """저장된 세션 상태를 불러옵니다."""
        if os.path.exists(self.session_file):
            try:
                with open(self.session_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error loading session: {e}")
        return {}

    def clear_session(self):
        """세션 저장 파일을 삭제합니다."""
        if os.path.exists(self.session_file):
            os.remove(self.session_file)
