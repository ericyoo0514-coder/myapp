from datetime import datetime
from zoneinfo import ZoneInfo

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
import streamlit as st
from streamlit_gsheets import GSheetsConnection
from openai import OpenAI
plt.rcParams["font.family"] = ["NanumGothic", "AppleGothic", "Malgun Gothic"]  # 한글 글꼴

st.title("🤖 서술형AI피드백")

# 수업코드 입력하기(외부인이 토큰사용하지 못하도록)
code = st.text_input("수업코드", type = "password")
if code is "":
    st.warning("코드를 먼저 입력해주세요.")
elif code != st.secrets["SECRET_CODE"]:
    st.error("코드가 일치하지 않아요.")
    st.stop()
else:
    st.success("코드로 입장 성공!")

# 메인 화면에서 입력한 학번 꺼내기
student_id = st.session_state.get("학번")
if not student_id:
    st.warning("메인 화면에서 학번을 먼저 입력하세요.")
    st.stop()

st.subheader("서술형 문항 입력을 시작합니다. ")
conn = st.connection("gsheets", type=GSheetsConnection)
df = conn.read(worksheet=655941621, usecols=[0, 1, 2], ttl=60).dropna(how="all")
fig, ax = plt.subplots(figsize=(8, 3))
sns.boxplot(data=df, x="통학 시간(분)", y="반", whis=(0, 100), ax=ax)
st.pyplot(fig)

# 데이터 요약
summary = df.groupby("반").describe()
# st.write(summary)
question = "두 반의 상자그림을 보고 통학 시간의 분포를 비교하여 설명하세요."
st.markdown(f"문제. {question}")

with st.form("subj"):
    subj = st.text_area("답안", height=200)
    submitted = st.form_submit_button("제출하고 피드백받기")


rule_prompt = f"""너는 중학교 3학년 수학교사이고, 학생의 서술형 답안에 피드백을 줘. 
반별 요약: {summary}
채점기준 
1. 중앙값이나 상자의 위치로 어느 반이 상대적으로 더 긴지 비교했는가
2. 상자의 길이로 자료가 모여 있는 정도를 비교했는가
3. '모든 학생이' 같은 단정 대신 '상대적으로', '대체로' 같은 표현을 썼는가

피드백은 잘 한 점 한 가지와 보완할 점 한 가지를 각각 한 문장으로 해서 총 두 문장을 자연스럽게 말하듯이 써줘. 모범답안은 쓰지말고, 존댓말을 사용해줘. """

# st.write(st.secrets["OPENAI_API_KEY"])
if submitted and subj:
    rules = rule_prompt
    client = OpenAI(api_key = st.secrets["OPENAI_API_KEY"])
    with st.spinner("선생님이 답안을 읽고 있어요..."):
        response = client.chat.completions.create(
            model = "gpt-6-luna",
            messages = [
                {"role":"system", "content":rules},
                {"role":"user", "content":subj}
            ]
        )
    feedback = response.choices[0].message.content
    st.info(feedback)

    # 응답을 구글시트에 저장하기
    now = datetime.now(ZoneInfo("Asia/Seoul")).strftime("%Y-%m-%d %H:%M")
    log = conn.read(worksheet = 1003, usecols = [0,1,2,3], ttl=0)
    new_row = pd.DataFrame([[now, student_id, subj, feedback]], columns = log.columns)
    conn.update(worksheet = 1003, data = pd.concat([log, new_row], ignore_index = True))
    st.caption("답안이 저장되었습니니다. ")
elif submitted:
    st.warning("답안을 작성해주세요.")