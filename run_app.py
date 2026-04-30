import streamlit.web.cli as stcli
import os, sys, threading, time, webview, signal, socket

# 시그널 핸들러 에러 방지를 위한 패치
def patch_signal():
    signal.signal = lambda *args, **kwargs: None

def resolve_path(path):
    """PyInstaller 환경에서도 경로를 올바르게 찾도록 도와줍니다."""
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, path)
    return os.path.join(os.path.abspath("."), path)

def get_free_port():
    """사용 가능한 빈 포트를 찾아 반환합니다."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0))
        return s.getsockname()[1]

def run_streamlit(port):
    patch_signal() # 스레드 내부에서 시그널 함수를 가짜 함수로 대체
    app_path = resolve_path("app.py")
    # --server.headless=true 를 설정하여 브라우저가 별도로 뜨지 않게 합니다.
    sys.argv = [
        "streamlit",
        "run",
        app_path,
        "--global.developmentMode=false",
        f"--server.port={port}",
        "--server.headless=true",
    ]
    stcli.main()

if __name__ == "__main__":
    # 사용할 포트 결정 (자동 할당)
    port = get_free_port()
    
    # Streamlit을 백그라운드 스레드에서 실행
    t = threading.Thread(target=run_streamlit, args=(port,))
    t.daemon = True
    t.start()

    # Streamlit 서버가 뜰 때까지 대기
    time.sleep(5)

    # 전용 윈도우 창 생성
    webview.create_window("AI Interview Auto - 실전형 모의 면접", f"http://localhost:{port}", width=1280, height=800, text_select=True, zoomable=True)

    # 우클릭 메뉴(context menu)를 위해 debug=True 사용, 단 개발자 도구는 자동으로 뜨지 않게 설정
    webview.settings['OPEN_DEVTOOLS_IN_DEBUG'] = False
    webview.start(debug=True)

    
    # 창을 닫으면 프로세스 강제 종료
    os._exit(0)
