import streamlit.web.cli as stcli
import os, sys, threading, time, webview, signal

# 시그널 핸들러 에러 방지를 위한 패치
def patch_signal():
    signal.signal = lambda *args, **kwargs: None

def resolve_path(path):
    """PyInstaller 환경에서도 경로를 올바르게 찾도록 도와줍니다."""
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, path)
    return os.path.join(os.path.abspath("."), path)

def run_streamlit():
    patch_signal() # 스레드 내부에서 시그널 함수를 가짜 함수로 대체
    app_path = resolve_path("app.py")
    # --server.headless=true 를 설정하여 브라우저가 별도로 뜨지 않게 합니다.
    sys.argv = [
        "streamlit",
        "run",
        app_path,
        "--global.developmentMode=false",
        "--server.port=8501",
        "--server.headless=true",
    ]
    stcli.main()

if __name__ == "__main__":
    # Streamlit을 백그라운드 스레드에서 실행
    t = threading.Thread(target=run_streamlit)
    t.daemon = True
    t.start()

    # Streamlit 서버가 뜰 때까지 대기
    time.sleep(5)

    # 전용 윈도우 창 생성
    webview.create_window("AI Interview Auto - 실전형 모의 면접", "http://localhost:8501", width=1280, height=800)
    webview.start()
    
    # 창을 닫으면 프로세스 강제 종료
    os._exit(0)
