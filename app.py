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
if "interviewer_question_count" not in st.session_state:
    st.session_state.interviewer_question_count = 0
if "total_question_count" not in st.session_state:
    st.session_state.total_question_count = 0
if "is_finished" not in st.session_state:
    st.session_state.is_finished = False
if "is_awaiting_reverse_question" not in st.session_state:
    st.session_state.is_awaiting_reverse_question = False
if "final_report" not in st.session_state:
    st.session_state.final_report = ""
if "is_generating_report" not in st.session_state:
    st.session_state.is_generating_report = False

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
        "interviewer_question_count": st.session_state.interviewer_question_count,
        "total_question_count": st.session_state.total_question_count,
        "is_finished": st.session_state.is_finished,
        "is_awaiting_reverse_question": st.session_state.is_awaiting_reverse_question,
        "final_report": st.session_state.final_report,
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
                    st.session_state.company_info,
                    current_count=st.session_state.interviewer_question_count
                )
                st.session_state.current_interviewer = res['interviewer']
                st.session_state.interviewer_question_count = res['count']
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

    if st.session_state.is_interview_started and not st.session_state.is_finished:
        if user_input := st.chat_input("답변을 입력하세요..."):
            st.session_state.chat_history.append({"role": "user", "content": user_input})
            # 사용자가 답변할 때마다 총 질문 횟수 증가
            st.session_state.total_question_count += 1
            save_current_session()
            st.rerun()
    elif st.session_state.is_finished:
        st.chat_input("면접이 종료되었습니다.", disabled=True)

# --- [Column Right] 실시간 분석 및 교정 ---
with col_right:
    st.header("📊 실시간 피드백 및 분석")
    
    # 마지막 질문과 답변이 있는 경우 피드백 생성
    if st.session_state.is_interview_started and not st.session_state.is_finished and st.session_state.chat_history and st.session_state.chat_history[-1]["role"] == "user":
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
            feedback_placeholder.markdown(f"```json\n{full_feedback_text}\n```")
            progress_bar.progress(min(i * 2, 95), text="데이터 수신 중...")
        
        progress_bar.progress(100, text="분석 완료!")
        st.session_state.feedback_data = engine.parse_json_response(full_feedback_text)
        
        # 피드백 완료 후 다음 질문(또는 종료 멘트) 생성
        with st.status("면접관이 다음 단계를 준비 중입니다...", expanded=True) as status:
            res = engine.get_next_question(
                st.session_state.chat_history,
                st.session_state.parsed_resume,
                st.session_state.company_info,
                current_interviewer=st.session_state.current_interviewer,
                current_count=st.session_state.interviewer_question_count,
                total_count=st.session_state.total_question_count
            )
            st.session_state.current_interviewer = res['interviewer']
            st.session_state.interviewer_question_count = res['count']
            st.session_state.chat_history.append({"role": "assistant", "content": res['question'], "name": res['interviewer']})
            
            # AI가 종료 신호를 보냈다면 역질문 대기 상태로 전환
            if res.get('is_final'):
                st.session_state.is_awaiting_reverse_question = True
                status.update(label="마무리 멘트 준비 완료!", state="complete", expanded=False)
            else:
                status.update(label="다음 질문 준비 완료!", state="complete", expanded=False)
        
        # 만약 방금 답변이 마지막 역질문이었다면 완전히 종료
        if st.session_state.is_awaiting_reverse_question and len(st.session_state.chat_history) > 0 and st.session_state.chat_history[-1]["role"] == "user":
             # 역질문에 대한 피드백까지 완료된 시점이므로 종료
             if st.session_state.total_question_count > 6: # 종료 멘트 이후의 입력임
                st.session_state.is_finished = True
                st.session_state.is_awaiting_reverse_question = False
                st.session_state.is_generating_report = True # 리포트 생성 시작
        
        save_current_session()
        st.rerun()

    # --- [Final Report Generation] ---
    if st.session_state.is_generating_report and not st.session_state.final_report:
        with st.spinner("채용 위원장이 최종 평가 리포트를 작성 중입니다. 잠시만 기다려 주세요..."):
            try:
                report = engine.generate_final_report(
                    st.session_state.chat_history,
                    st.session_state.parsed_resume,
                    st.session_state.company_info
                )
                st.session_state.final_report = report
                st.session_state.is_generating_report = False
                save_current_session()
                st.rerun()
            except Exception as e:
                st.error(f"리포트 생성 중 오류 발생: {e}")
                st.session_state.is_generating_report = False

    # 최종 리포트가 있으면 화면 하단에 표시
    if st.session_state.final_report:
        st.divider()
        st.header("🏆 최종 면접 평가 리포트")
        st.markdown(st.session_state.final_report)
        
        # 다운로드 버튼 (간단 구현)
        st.download_button(
            label="📄 리포트 다운로드 (Markdown)",
            data=st.session_state.final_report,
            file_name=f"Interview_Report_{st.session_state.session_id}.md",
            mime="text/markdown"
        )
    
    if st.session_state.feedback_data:
        data = st.session_state.feedback_data
        if "error" in data:
            st.error(f"⚠️ 분석 데이터를 화면에 표시할 수 없습니다: {data['error']}")
            with st.expander("📝 AI 응답 원본 확인 (디버깅용)"):
                st.code(data.get("raw", "데이터 없음"), language="json")
                st.info("위 원본 데이터를 복사해서 알려주시면 문제 해결에 큰 도움이 됩니다.")
        else:
            # --- 지능형 데이터 추출 및 보정 로직 (강화판) ---
            def get_any(keys, default_val="-"):
                """여러 개의 후보 키 중 첫 번째로 발견되는 값을 반환"""
                for k in keys:
                    if k in data: return data[k]
                return default_val

            def extract_feedback_data(prefix, kor_name):
                # 1. 등급(Score) 추출: 영문/한글 후보 키 모두 검색
                score_keys = [f"score_{prefix}", f"{prefix}_score", f"{kor_name}_등급", f"{kor_name}_점수", prefix, kor_name]
                score = get_any(score_keys, "-")
                
                # 만약 score에 너무 긴 문장이 들어온 경우 (보정)
                detail_from_score = None
                if len(str(score)) > 10:
                    detail_from_score = score
                    score = "분석완료"
                
                # 2. 상세(Detail) 추출: 영문/한글 후보 키 모두 검색
                detail_keys = [f"detail_{prefix}", f"{prefix}_detail", f"{kor_name}_상세", f"{kor_name}_분석", f"{kor_name}_설명"]
                detail = get_any(detail_keys, "")
                
                # 3. 보정: 상세가 비어있으면 score에서 넘쳐흐른 문장을 가져옴
                if (not detail or len(detail) < 5) and detail_from_score:
                    detail = detail_from_score
                
                if not detail: detail = "상세 분석 결과가 생성되지 않았습니다."
                
                return str(score), str(detail)

            # 각 항목 데이터 지능형 추출
            s_clarity, d_clarity = extract_feedback_data("clarity", "명확성")
            s_evidence, d_evidence = extract_feedback_data("evidence", "근거")
            s_intent, d_intent = extract_feedback_data("intent", "의도")

            # 1. 평가 요약 (Custom Badges)
            st.subheader("✅ 답변 평가 요약")
            m1, m2, m3 = st.columns(3)
            with m1: render_metric_with_badge("명확성", s_clarity)
            with m2: render_metric_with_badge("근거 충분성", s_evidence)
            with m3: render_metric_with_badge("의도 파악", s_intent)
            
            st.divider()

            # 2. 상세 분석 및 가이드 (Tabs)
            tab1, tab2, tab3 = st.tabs(["🔍 상세 분석", "💡 교정 가이드", "✨ 모범 답안"])
            
            with tab1:
                st.markdown(f"**명확성:** {d_clarity}")
                st.markdown(f"**근거 충분성:** {d_evidence}")
                st.markdown(f"**의도 파악:** {d_intent}")
                
                # 체크포인트도 지능형 추출
                check_list = get_any(["check_items", "체크포인트", "핵심_체크포인트"], [])
                if check_list and isinstance(check_list, list):
                    st.write("---")
                    st.write("**📌 핵심 체크포인트**")
                    for item in check_list:
                        st.write(f"✅ {item}")

            with tab2:
                # 가이드도 지능형 추출
                guide = get_any(["improvement_guide", "교정_가이드", "개선_방안"], "제공된 교정 가이드가 없습니다.")
                st.info(guide)

            with tab3:
                # 모범답안 지능형 추출
                m_answer = get_any(["model_answer", "model_answer_direction", "모범_답안", "모범_답변"], "제시된 모범 답안이 없습니다.")
                st.success(m_answer)
                st.write("---")
                st.caption("※ 위 내용은 인공지능이 생성한 가이드라인이며, 실제 본인의 경험을 바탕으로 자연스럽게 수정하여 활용하세요.")
    else:
        st.info("면접이 진행되면 이곳에 실시간 피드백이 표시됩니다.")
