import operator
from typing import Annotated, TypedDict, List, Dict, Any, Optional
from langgraph.graph import StateGraph, END
from google import genai
from google.genai import types
import os
import json
import time

from prompts.templates import (
    TECH_INTERVIEWER_PROMPT,
    HR_INTERVIEWER_PROMPT,
    EXEC_INTERVIEWER_PROMPT,
    ANALYST_PROMPT
)

# 1. 면접 상태(State) 정의
class InterviewState(TypedDict):
    # add_messages 대신 operator.add를 사용하여 순수 딕셔너리 리스트 유지
    messages: Annotated[List[Dict[str, Any]], operator.add]
    # 현재 면접관
    current_agent: str
    # 컨텍스트 (지원자 서류, 기업 정보, 피드백 등)
    context: Dict[str, Any]
    # 면접관별 질문 횟수 및 총 질문 횟수
    interviewer_counts: Dict[str, int]
    total_count: int
    # 종료 여부
    is_finished: bool

# 페르소나 매핑
PERSONA_MAP = {
    "Agent_Tech": TECH_INTERVIEWER_PROMPT,
    "Agent_HR": HR_INTERVIEWER_PROMPT,
    "Agent_Exec": EXEC_INTERVIEWER_PROMPT
}

# 유틸리티: 메시지 객체에서 텍스트와 역할 추출
def get_msg_content(msg):
    return msg.content if hasattr(msg, 'content') else msg.get('content', '')

def get_msg_role(msg):
    role = msg.type if hasattr(msg, 'type') else msg.get('role', '')
    # LangChain 'human' -> 'user', 'ai' -> 'model' (GenAI SDK 기준)
    if role == 'human': return 'user'
    if role == 'ai': return 'model'
    if role == 'assistant': return 'model'
    return role

# 2. 에이전트 노드 구현
def interviewer_node(state: InterviewState):
    """현재 면접관이 질문을 생성하는 노드"""
    agent_name = state.get('current_agent', "Agent_Tech")
    persona = PERSONA_MAP.get(agent_name, TECH_INTERVIEWER_PROMPT)
    
    client = state['context'].get('client')
    if not client:
        api_key = os.environ.get("GOOGLE_API_KEY")
        client = genai.Client(api_key=api_key)
    
    model_name = state['context'].get('model_name', 'gemma-4-31b-it')
    
    # LangChain 객체를 GenAI SDK용 딕셔너리로 변환
    history = state.get('messages', [])
    contents = []
    for m in history:
        contents.append({
            "role": get_msg_role(m),
            "parts": [{"text": get_msg_content(m)}]
        })
    
    # contents가 비어있으면 에러 방지
    if not contents:
        contents = "면접을 시작합니다. 지원자에게 첫 질문을 던져주세요."
    
    current_agent_count = state['interviewer_counts'].get(agent_name, 0)
    is_follow_up = (current_agent_count == 1)
    
    if is_follow_up:
        prompt_suffix = "\n[상황] 당신은 방금 질문을 던졌고 지원자의 답변을 들었습니다. 답변의 논리적 허점을 파고드는 날카로운 꼬리 질문을 하나만 하세요."
    else:
        prompt_suffix = f"\n[상황] 당신의 차례입니다. 지원자 서류와 이전 대화 맥락을 고려하여 새로운 메인 질문을 던지세요."

    try:
        response = client.models.generate_content(
            model=model_name,
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=persona + prompt_suffix,
                temperature=0.7,
            )
        )
    except Exception as e:
        return {
            "messages": [{"role": "assistant", "content": f"질문 생성 중 오류가 발생했습니다: {str(e)}", "name": agent_name}],
            "interviewer_counts": state['interviewer_counts'],
            "total_count": state['total_count'],
            "current_agent": agent_name
        }
    
    new_message = {"role": "assistant", "content": response.text, "name": agent_name}
    
    new_counts = state['interviewer_counts'].copy()
    new_counts[agent_name] = current_agent_count + 1
    
    return {
        "messages": [new_message],
        "interviewer_counts": new_counts,
        "total_count": state['total_count'] + 1,
        "current_agent": agent_name
    }

def analyst_node(state: InterviewState):
    """지원자의 마지막 답변을 분석하는 노드 (Background)"""
    messages = state.get('messages', [])
    if not messages:
        return {}

    # 마지막 메시지가 사용자의 답변인지 확인 (객체 타입 체크)
    last_msg = messages[-1]
    if get_msg_role(last_msg) != 'user':
        return {}

    client = state['context'].get('client')
    if not client:
        api_key = os.environ.get("GOOGLE_API_KEY")
        client = genai.Client(api_key=api_key)

    model_name = state['context'].get('model_name', 'gemma-4-31b-it')
    
    parsed_resume = state['context'].get('parsed_resume', '')
    company_info = state['context'].get('company_info', '')
    
    user_answer = get_msg_content(last_msg)
    last_question = ""
    # 역순으로 탐색하여 면접관의 마지막 질문 찾기
    for msg in reversed(messages[:-1]):
        if get_msg_role(msg) == 'model':
            last_question = get_msg_content(msg)
            break
            
    prompt = f"""
    질문: {last_question}
    답변: {user_answer}
    지원자 서류: {parsed_resume[:1000]}
    기업 정보: {company_info[:1000]}
    
    위 답변을 분석하여 지정된 JSON 형식으로 피드백을 제공하세요.
    """
    
    try:
        response = client.models.generate_content(
            model=model_name,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=ANALYST_PROMPT,
                temperature=0.7,
            )
        )
        new_context = state['context'].copy()
        new_context['last_feedback_raw'] = response.text
        return {"context": new_context}
    except:
        return {}

# 3. 라우팅 로직
def router(state: InterviewState):
    """면접 지속 여부 및 다음 면접관 결정"""
    # 총 질문 6회 완료 시 종료
    if state['total_count'] >= 6:
        return "end"
    
    # 현재 면접관이 2번 질문했다면 면접관 교체 준비
    current_agent = state['current_agent']
    if state['interviewer_counts'].get(current_agent, 0) >= 2:
        return "switch"
    
    return "continue"

# 4. 그래프 구성
def create_interview_graph():
    workflow = StateGraph(InterviewState)
    
    workflow.add_node("interviewer", interviewer_node)
    workflow.add_node("analyst", analyst_node)
    
    def switch_agent(state: InterviewState):
        agents = ["Agent_Tech", "Agent_HR", "Agent_Exec"]
        current_agent = state.get('current_agent', "Agent_Tech")
        current_idx = agents.index(current_agent)
        next_agent = agents[(current_idx + 1) % len(agents)]
        return {"current_agent": next_agent}

    workflow.add_node("interviewer_switch", switch_agent)

    # 1. 시작점 변경: analyst(분석)부터 시작하여 턴을 제어함
    workflow.set_entry_point("analyst")
    
    # 2. 분석 노드 이후 라우팅
    workflow.add_conditional_edges(
        "analyst",
        router,
        {
            "continue": "interviewer",
            "switch": "interviewer_switch",
            "end": END
        }
    )

    # 3. 면접관 교체 후 질문 생성 노드로 이동
    workflow.add_edge("interviewer_switch", "interviewer")
    
    # 4. ✨ 핵심 포인트: 질문을 하나 생성했으면 그래프 실행을 종료하고 UI(사용자 입력 대기)로 돌아감
    workflow.add_edge("interviewer", END)
    
    return workflow.compile()
