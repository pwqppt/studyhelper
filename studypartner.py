import streamlit as st
from PyPDF2 import PdfReader
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

from openai import OpenAI
from dotenv import load_dotenv
import base64

load_dotenv("key.env")
client = OpenAI()

import uuid

# 1. 초기 설정
st.set_page_config(page_title="스마트 암기 조력자", layout="wide")
llm = ChatOpenAI(model="gpt-4o", temperature=0.5)

# 세션 상태 초기화 (폴더 및 채팅 데이터 저장)
if "folders" not in st.session_state:
    st.session_state.folders = {} # {폴더명: {채팅ID: {데이터}}}
if "current_folder" not in st.session_state:
    st.session_state.current_folder = None
if "current_chat_id" not in st.session_state:
    st.session_state.current_chat_id = None

# --- 함수 정의 ---
def extract_text_with_page(pdf_file):
    reader = PdfReader(pdf_file)
    pages_content = []
    for i, page in enumerate(reader.pages):
        text = page.extract_text()
        if text:
            pages_content.append({"page": i + 1, "content": text})
    return pages_content

def generate_quiz_system(pages_content, quiz_type):
    # 전체 텍스트 결합 (프롬프트 전달용)
    full_context = "\n".join([f"[Page {p['page']}] {p['content']}" for p in pages_content])
    
    template = """
    당신은 학생의 암기를 돕는 조력자입니다. 
    제공된 텍스트의 흐름을 분석하여 다음 요청을 수행하세요.

    1. [개괄 요약]: 이 개념이 어떤 배경/니즈에서 고안되었는지, 어떤 흐름으로 구성되었는지 한 줄로 요약하세요.
    2. [핵심 키워드]: 전체를 관통하는 핵심 단어 5개를 뽑으세요.
    3. [5문제 퀴즈]: {quiz_type} 유형으로 5문제를 만드세요.
    4. [출처]: 각 문제마다 참고한 페이지 번호와 해당 문장의 핵심 문구를 아주 작게 표시하세요.

    텍스트 내용:
    {context}

    형식:
    ### 1. 개괄 요약
    (내용)
    ### 2. 핵심 키워드
    (내용)
    ---
    ### 3. 퀴즈 문제 (정답 미포함)
    Q1... Q5...
    ---
    ### 4. 정답 및 해설 (출처 포함)
    (각 문제별 상세 해설 및 'Page X: 문구' 표시)
    """
    
    prompt = ChatPromptTemplate.from_template(template)
    chain = prompt | llm
    response = chain.invoke({"quiz_type": quiz_type, "context": full_context})
    return response.content

# --- 사이드바: 폴더 및 채팅 관리 ---
with st.sidebar:
    st.title("📂 학습 보관함")
    
    # 폴더(과목) 추가
    new_folder = st.text_input("새 과목(폴더) 추가").strip()
    if st.button("과목 생성") and new_folder:
        if new_folder not in st.session_state.folders:
            st.session_state.folders[new_folder] = {}
            st.session_state.current_folder = new_folder
    
    st.divider()
    
    if st.session_state.folders:
        folder_list = list(st.session_state.folders.keys())
        st.session_state.current_folder = st.selectbox("과목 선택", folder_list)
        
        # 채팅(회차) 추가
        chat_name = st.text_input("새 학습 회차(채팅) 이름")
        if st.button("학습 시작") and chat_name:
            chat_id = str(uuid.uuid4())
            st.session_state.folders[st.session_state.current_folder][chat_id] = {
                "name": chat_name,
                "quiz_data": None
            }
            st.session_state.current_chat_id = chat_id
            
        st.divider()
        
        # 현재 폴더 내 채팅 목록
        current_chats = st.session_state.folders[st.session_state.current_folder]
        for c_id, c_data in current_chats.items():
            if st.button(f"📄 {c_data['name']}", key=c_id):
                st.session_state.current_chat_id = c_id

# --- 메인 화면 ---
if st.session_state.current_chat_id:
    curr_chat = st.session_state.folders[st.session_state.current_folder][st.session_state.current_chat_id]
    st.title(f"📖 {st.session_state.current_folder} > {curr_chat['name']}")
    
    if not curr_chat["quiz_data"]:
        uploaded_file = st.file_uploader("PDF 파일을 업로드하세요", type="pdf")
        quiz_type = st.radio("문제 유형", ("단답형", "객관식", "OX"), horizontal=True)
        
        if uploaded_file and st.button("퀴즈 생성"):
            with st.spinner("AI가 내용을 분석 중입니다..."):
                pages_content = extract_text_with_page(uploaded_file)
                quiz_result = generate_quiz_system(pages_content, quiz_type)
                curr_chat["quiz_data"] = quiz_result
                st.rerun()
    else:
        # 결과 출력 지점
        data = curr_chat["quiz_data"]
        # 결과 데이터를 '---' 기준으로 분리 (문제 파트 / 해설 파트)
        parts = data.split("---")
        
        # 상단 요약 및 키워드
        st.markdown(parts[0])
        
        # 문제 파트
        st.markdown(parts[1])
        
        # 해설 보기 (접이식 UI 사용)
        with st.expander("💡 정답 및 상세 해설 보기 (출처 포함)"):
            st.markdown(parts[2])
            
        if st.button("다시 생성하기"):
            curr_chat["quiz_data"] = None
            st.rerun()
else:
    st.info("왼쪽 사이드바에서 과목을 선택하고 새로운 학습 회차를 만들어주세요.")
    
    
# 실행 방법 안내
# 터미널에 'streamlit run (파일명)' 입력