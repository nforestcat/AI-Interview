import streamlit as st
import os
import json
from dotenv import load_dotenv, set_key
from google.genai import Client
from core.logger import get_logger
from core.cache_manager import CacheManager
from core.search_utils import SearchUtils
from core.pdf_parser import PDFParser
from core.interview_engine import InterviewEngine
from core.session_manager import SessionManager

# .env 파일 로드
env_path = ".env"
load_dotenv(env_path)

# 로거 및 세션 매니저 설정
logger = get_logger("AI_Interview_App")
session_manager = SessionManager()

# 페이지 설정
st.set_page_config(page_title="AI Interview - 실전형 모의 면접", layout="wide")

# Custom CSS 주입
st.markdown("""
<style>
    .main {
        background-color: #f8f9fa;
    }
    .stChatMessage {
        border-radius: 15px;
        padding: 10px;
        margin-bottom: 10px;
    }
    .stMetric {
        background-color: #ffffff;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    .feedback-card {
        background-color: #ffffff;
        padding: 20px;
        border-radius: 12px;
        border-left: 5px solid #007bff;
        margin-bottom: 20px;
    }
    .status-badge {
        padding: 4px 12px;
        border-radius: 20px;
        font-weight: bold;
        font-size: 0.8rem;
    }
    .badge-good { background-color: #d4edda; color: #155724; }
    .badge-average { background-color: #fff3cd; color: #856404; }
    .badge-poor { background-color: #f8d7da; color: #721c24; }
</style>
""", unsafe_allow_html=True)

def render_metric_with_badge(label, value):
    """평가 점수에 따라 색상 배지와 함께 메트릭을 렌더링합니다."""
    badge_class = "badge-average"
    if value == "좋음":
        badge_class = "badge-good"
    elif value == "부족":
        badge_class = "badge-poor"
    
    st.markdown(f"""
    <div style="text-align: center; background: white; padding: 10px; border-radius: 10px; box-shadow: 0 1px 3px rgba(0,0,0,0.1);">
        <div style="font-size: 0.9rem; color: #6c757d; margin-bottom: 5px;">{label}</div>
        <div class="status-badge {badge_class}">{value}</div>
    </div>
    """, unsafe_allow_html=True)

# 저장된 세션 데이터 로드 (첫 실행 시)
if "session_loaded" not in st.session_state:
    saved_data = session_manager.load_session()
    for key, value in saved_data.items():
        st.session_state[key] = value
    st.session_state.session_loaded = True

# 세션 상태 초기화 (기존 코드 유지 및 보완)
if "session_id" not in st.session_state:
    import time
    st.session_state.session_id = f"interview_{int(time.time())}"
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "company_info" not in st.session_state:
    st.session_state.company_info = ""
if "resume_text" not in st.session_state:
    st.session_state.resume_text = ""
if "parsed_resume" not in st.session_state:
    st.session_state.parsed_resume = ""
if "pre_analysis" not in st.session_state:
    st.session_state.pre_analysis = ""
if "current_interviewer" not in st.session_state:
    st.session_state.current_interviewer = None
if "feedback_data" not in st.session_state:
    st.session_state.feedback_data = None
if "is_interview_started" not in st.session_state:
    st.session_state.is_interview_started = False
if "is_analyzing" not in st.session_state:
    st.session_state.is_analyzing = False
if "is_starting_interview" not in st.session_state:
    st.session_state.is_starting_interview = False

def save_current_session():
    """현재 세션 상태를 파일에 저장합니다."""
    state_to_save = {
        "session_id": st.session_state.session_id,
        "chat_history": st.session_state.chat_history,
        "company_info": st.session_state.company_info,
        "resume_text": st.session_state.resume_text,
        "parsed_resume": st.session_state.parsed_resume,
        "pre_analysis": st.session_state.pre_analysis,
        "current_interviewer": st.session_state.current_interviewer,
        "feedback_data": st.session_state.feedback_data,
        "is_interview_started": st.session_state.is_interview_started
    }
    session_manager.save_session(state_to_save)

# 사이드바 설정
with st.sidebar:
    st.title("⚙️ 설정 및 관리")
    
    # 세션 상태 표시
    st.subheader("📊 진행 상태")
    status_cols = st.columns(2)
    with status_cols[0]:
        st.write("**기업 정보**")
        st.write("✅ 준비됨" if st.session_state.company_info else "❌ 미흡")
    with status_cols[1]:
        st.write("**서류 업로드**")
        st.write("✅ 준비됨" if st.session_state.resume_text else "❌ 미흡")
    
    # 준비도 계산 수정
    progress_val = 0
    if st.session_state.company_info: progress_val += 33
    if st.session_state.resume_text: progress_val += 33
    if st.session_state.is_interview_started: progress_val += 34
    
    st.progress(progress_val, text=f"전체 준비도: {progress_val}%")
    st.divider()

    # .env에서 기존 키 로드
    existing_api_key = os.getenv("GEMINI_API_KEY", "")
    api_key = st.text_input("Gemini API Key", value=existing_api_key, type="password")
    
    # API 키가 변경되었거나 새로 입력된 경우 .env에 저장
    if api_key and api_key != existing_api_key:
        set_key(env_path, "GEMINI_API_KEY", api_key)
        os.environ["GEMINI_API_KEY"] = api_key
        st.success("API Key가 .env 파일에 저장되었습니다.")
    
    if api_key:
        client = Client(api_key=api_key, http_options={'api_version': 'v1alpha'})
        cache_manager = CacheManager()
        search_utils = SearchUtils(client, model_name='gemma-4-26b-a4b-it')
        engine = InterviewEngine(session_id=st.session_state.session_id)
    else:
        st.warning("API Key를 입력해주세요.")
        st.stop()

    st.divider()
    company_name = st.text_input("지원 기업명", placeholder="예: 삼성전자")
    role_name = st.text_input("지원 직무", placeholder="예: 백엔드 개발자")
    
    if st.button("기업 정보 검색 및 분석"):
        if company_name:
            with st.spinner("최신 기업 정보를 수집 중입니다..."):
                cached_info = cache_manager.load_company_data(company_name)
                if cached_info:
                    st.session_state.company_info = cached_info
                    st.success("캐시된 정보를 불러왔습니다.")
                else:
                    info = search_utils.search_company_info(company_name)
                    st.session_state.company_info = info
                    cache_manager.save_company_data(company_name, info)
                    st.success("정보 검색이 완료되었습니다.")
                save_current_session()
        else:
            st.error("기업명을 입력해주세요.")

    if st.button("세션 초기화", type="secondary"):
        st.session_state.chat_history = []
        st.session_state.pre_analysis = ""
        st.session_state.current_interviewer = None
        st.session_state.feedback_data = None
        st.session_state.is_interview_started = False
        st.session_state.resume_text = ""
        st.session_state.parsed_resume = ""
        import time
        st.session_state.session_id = f"interview_{int(time.time())}"
        session_manager.clear_session()
        st.rerun()

# 메인 화면 레이아웃
col_left, col_right = st.columns([1.2, 1])

# --- [Column Left] 대화 및 입력 영역 ---
with col_left:
    st.header("💬 면접관과의 대화")
    
    # 📄 서류 업로드 및 관리 섹션
    with st.expander("📄 이력서 업로드 및 관리", expanded=not st.session_state.resume_text):
        if st.session_state.resume_text:
            st.success("✅ 현재 이력서가 업로드된 상태입니다.")
            if st.button("❌ 파일 삭제 및 다시 업로드"):
                st.session_state.resume_text = ""
                st.session_state.parsed_resume = ""
                st.session_state.pre_analysis = "" # 서류가 바뀌면 사전 분석도 초기화
                save_current_session()
                st.rerun()
        else:
            uploaded_files = st.file_uploader("이력서 또는 자기소개서 업로드 (여러 파일 선택 가능)", type=["pdf", "txt", "md"], accept_multiple_files=True)
            if uploaded_files:
                with st.spinner("서류들을 읽어오는 중..."):
                    combined_text = ""
                    for file in uploaded_files:
                        if file.type == "application/pdf":
                            # 임시 파일명이 겹치지 않게 처리
                            temp_filename = f"temp_{file.name}"
                            with open(temp_filename, "wb") as f:
                                f.write(file.getbuffer())
                            combined_text += f"\n--- [{file.name}] ---\n"
                            combined_text += PDFParser.extract_text(temp_filename)
                            os.remove(temp_filename)
                        else:
                            combined_text += f"\n--- [{file.name}] ---\n"
                            combined_text += file.read().decode("utf-8")
                    
                    st.session_state.resume_text = combined_text
                    save_current_session()
                st.success("📄 모든 서류 텍스트 추출이 완료되었습니다. 아래 '사전 분석' 버튼을 눌러 AI 면접 준비를 시작하세요!")
                st.rerun() # 업로드 후 상태 반영을 위해 리런
    
    if st.session_state.resume_text and st.session_state.company_info and not st.session_state.is_interview_started:
        if not st.session_state.pre_analysis:
            st.info("💡 서류와 기업 정보가 준비되었습니다. AI 에이전트들의 사전 분석을 진행해 주세요.")
            if st.button("🔍 서류 심층 분석 및 예상 질문 생성", use_container_width=True, type="primary"):
                with st.spinner("에이전트들이 서류를 구조화하고 분석 중입니다..."):
                    if not st.session_state.parsed_resume:
                        st.session_state.parsed_resume = engine.parse_resume(st.session_state.resume_text)
                    
                    st.session_state.pre_analysis = engine.generate_initial_pool(
                        st.session_state.parsed_resume,
                        st.session_state.company_info
                    )
                save_current_session()
                st.rerun()
        
        if st.session_state.pre_analysis:
            with st.expander("📝 사전 분석 결과 및 예상 질문", expanded=True):
                st.markdown(st.session_state.pre_analysis)
            
            if st.button("실전 면접 시작하기", use_container_width=True, type="primary", disabled=st.session_state.get("is_starting_interview", False)):
                st.session_state.is_starting_interview = True
                st.rerun()

        # 면접 시작 진행 상태일 때 실행
        if st.session_state.get("is_starting_interview", False):
            with st.spinner("첫 질문을 준비 중입니다..."):
                res = engine.get_next_question(
                    st.session_state.chat_history,
                    st.session_state.parsed_resume,
                    st.session_state.company_info
                )
                st.session_state.current_interviewer = res['interviewer']
                st.session_state.chat_history.append({"role": "assistant", "content": res['question'], "name": res['interviewer']})
            st.session_state.is_interview_started = True
            st.session_state.is_starting_interview = False
            save_current_session()
            st.rerun()

    for msg in st.session_state.chat_history:
        name = msg.get("name", "지원자")
        with st.chat_message(msg["role"]):
            if msg["role"] == "assistant":
                st.markdown(f"**[{name}]**")
            st.write(msg["content"])

    if st.session_state.is_interview_started:
        if user_input := st.chat_input("답변을 입력하세요..."):
            st.session_state.chat_history.append({"role": "user", "content": user_input})
            save_current_session()
            # 여기서 즉시 피드백 및 다음 질문 생성을 처리하지 않고 rerun하여
            # UI에 사용자 답변이 먼저 보이게 함. col_right에서 실제 처리를 수행.
            st.rerun()

# --- [Column Right] 실시간 분석 및 교정 ---
with col_right:
    st.header("📊 실시간 피드백 및 분석")
    
    # 마지막 질문과 답변이 있는 경우 피드백 생성
    if st.session_state.is_interview_started and st.session_state.chat_history and st.session_state.chat_history[-1]["role"] == "user":
        user_answer = st.session_state.chat_history[-1]["content"]
        
        # 이전 질문 찾기
        last_question = ""
        for i in range(len(st.session_state.chat_history)-2, -1, -1):
            if st.session_state.chat_history[i]["role"] == "assistant":
                last_question = st.session_state.chat_history[i]["content"]
                break
        
        st.subheader("💡 AI Analyst 분석 중...")
        feedback_placeholder = st.empty()
        
        full_feedback_text = ""
        # 프로그레스 바 추가
        progress_bar = st.progress(0, text="답변 분석 중...")
        
        # New streaming feedback from AnalystAgent
        for i, chunk in enumerate(engine.get_feedback_stream(
            last_question, 
            user_answer, 
            st.session_state.parsed_resume, 
            st.session_state.company_info
        )):
            full_feedback_text += chunk
            # Show raw JSON or cleaned up version in real-time
            feedback_placeholder.markdown(f"```json\n{full_feedback_text}\n```")
            progress_bar.progress(min(i * 2, 95), text="데이터 수신 중...")
        
        progress_bar.progress(100, text="분석 완료!")
        
        # JSON 파싱 시도 (InterviewEngine의 정규식 기반 파서 활용)
        st.session_state.feedback_data = engine.parse_json_response(full_feedback_text)
        
        # 피드백 완료 후 다음 질문 생성
        with st.status("면접관이 다음 질문을 준비 중입니다...", expanded=True) as status:
            res = engine.get_next_question(
                st.session_state.chat_history,
                st.session_state.parsed_resume,
                st.session_state.company_info,
                current_interviewer=st.session_state.current_interviewer
            )
            st.session_state.current_interviewer = res['interviewer']
            st.session_state.chat_history.append({"role": "assistant", "content": res['question'], "name": res['interviewer']})
            status.update(label="질문 준비 완료!", state="complete", expanded=False)
        
        save_current_session()
        st.rerun()
    
    if st.session_state.feedback_data:
        data = st.session_state.feedback_data
        if "error" in data:
            st.error(data["error"])
            with st.expander("원본 데이터 확인"):
                st.text(data.get("raw", ""))
        else:
            # 1. 평가 요약 (Custom Badges)
            st.subheader("✅ 답변 평가 요약")
            m1, m2, m3 = st.columns(3)
            evals = data.get("evaluation", {})
            with m1: render_metric_with_badge("명확성", evals.get("clarity", "-"))
            with m2: render_metric_with_badge("근거 충분성", evals.get("evidence", "-"))
            with m3: render_metric_with_badge("의도 파악", evals.get("intent_match", "-"))
            
            st.divider()

            # 2. 탭을 활용한 상세 분석
            tab1, tab2, tab3 = st.tabs(["🔍 상세 분석", "💡 교정 가이드", "✨ 모범 답안"])
            
            with tab1:
                details = data.get("evaluation_detail", {})
                st.markdown(f"**명확성:** {details.get('clarity', '')}")
                st.markdown(f"**근거 충분성:** {details.get('evidence', '')}")
                st.markdown(f"**의도 파악:** {details.get('intent_match', '')}")
                
                if "check_items" in data:
                    st.write("---")
                    st.write("**📌 핵심 체크포인트**")
                    for item in data["check_items"]:
                        st.write(f"✅ {item}")

            with tab2:
                st.info(data.get("improvement_guide", "가이드가 없습니다."))
                st.write("---")
                st.write("**💡 면접관의 시선**")
                st.write("지원자의 답변에서 질문의 핵심 의도를 얼마나 파악했는지와 논리적 비약이 없는지를 중점적으로 평가했습니다.")

            with tab3:
                st.success(data.get("model_answer_direction", "방향 제시가 없습니다."))
                st.write("---")
                st.caption("※ 위 내용은 인공지능이 생성한 가이드라인이며, 실제 본인의 경험을 바탕으로 자연스럽게 수정하여 활용하세요.")
    else:
        st.info("면접이 진행되면 이곳에 실시간 피드백이 표시됩니다.")
