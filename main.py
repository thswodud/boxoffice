import datetime
import json
import requests
import pandas as pd
import pytz
import streamlit as st

# 페이지 기본 설정 (타이틀, 레이아웃 등)
st.set_page_config(
    page_title="일별 박스오피스 조회",
    page_icon="🎬",
    layout="wide"
)

st.title("🎬 일별 박스오피스 조회")
st.caption("영화진흥위원회(KOBIS) Open API 기반 박스오피스 조회 앱입니다.")

# -----------------------------------------------------------------------------
# 1. API 키 검증 (Streamlit Secrets 설정 확인)
# -----------------------------------------------------------------------------
if "KOBIS_KEY" not in st.secrets or not st.secrets["KOBIS_KEY"]:
    st.error("❌ 비밀 금고(secrets)에서 'KOBIS_KEY'를 찾을 수 없거나 값이 비어 있습니다.")
    st.info(
        "💡 **확인 및 해결 방법:**\n"
        "1. Streamlit Cloud 앱 설정 화면의 **Secrets** 메뉴로 이동하세요.\n"
        "2. 아래 형식으로 발급받은 KOBIS API 키를 등록해 주세요:\n\n"
        '```toml\nKOBIS_KEY = "발급받은_키_문자열"\n```'
    )
    st.stop()

api_key = st.secrets["KOBIS_KEY"]

# -----------------------------------------------------------------------------
# 2. 한국 시간(KST) 기준 선택 가능 날짜 계산 (최대 '어제'까지)
# -----------------------------------------------------------------------------
kst = pytz.timezone("Asia/Seoul")
now_kst = datetime.datetime.now(kst)
yesterday_date = (now_kst - datetime.timedelta(days=1)).date()

# 최소 선택 날짜 (KOBIS API 서비스 시작 시점 기준)
min_date = datetime.date(2004, 1, 1)

# 달력 위젯으로 조회 날짜 선택
selected_date = st.date_input(
    label="📅 조회할 날짜를 선택하세요 (최대 어제까지 가능)",
    value=yesterday_date,
    min_value=min_date,
    max_value=yesterday_date
)

# API 요청용 yyyymmdd 형식 변환
target_date_str = selected_date.strftime("%Y%m%d")
display_date_str = selected_date.strftime("%Y년 %m월 %d일")

st.markdown(f"### 📅 **{display_date_str}** 박스오피스")

# -----------------------------------------------------------------------------
# 3. KOBIS API 데이터 요청
# -----------------------------------------------------------------------------
url = "https://www.kobis.or.kr/kobisopenapi/webservice/rest/boxoffice/searchDailyBoxOfficeList.json"
params = {
    "key": api_key,
    "targetDt": target_date_str
}

try:
    response = requests.get(url, params=params, timeout=10)
    response.raise_for_status()
    data = response.json()
except requests.exceptions.RequestException as err:
    st.error("❌ API 서버와의 네트워크 통신 중 오류가 발생했습니다.")
    st.warning(f"⚠️ **세부 오류:** {err}")
    st.info("💡 **확인해 보세요:** 인터넷 연결 상태를 확인하시거나 KOBIS API 서버 점검 여부를 확인해 주세요.")
    st.stop()
except json.JSONDecodeError:
    st.error("❌ API 응답 데이터를 해석(JSON Parsing)할 수 없습니다.")
    st.info("💡 **확인해 보세요:** API 서버 응답이 올바른 JSON 형태인지 확인해 주세요.")
    st.stop()

# -----------------------------------------------------------------------------
# 4. API 오류 응답 및 빈 데이터 예외 처리
# -----------------------------------------------------------------------------
# KOBIS API 인증키 오류 감지
if "faultInfo" in data:
    fault = data["faultInfo"]
    st.error("❌ API 응답 오류가 발생했습니다 (인증키 오류 가능성).")
    st.warning(f"⚠️ **오류 메시지:** {fault.get('message', '알 수 없는 오류')}")
    st.info("💡 **확인해 보세요:** Streamlit Secrets에 입력한 `KOBIS_KEY`가 오타 없이 정확한지 점검해 주세요.")
    st.stop()

box_office_result = data.get("boxOfficeResult", {})
daily_list = box_office_result.get("dailyBoxOfficeList", [])

# 영화 목록이 비어서 들어올 때
if not daily_list:
    st.warning("⚠️ 그날은 아직 집계 전입니다.")
    st.info("💡 **안내:** 영화진흥위원회 서버의 일별 박스오피스 데이터 집계가 완료된 후 조회가 가능합니다.")
    st.stop()

# -----------------------------------------------------------------------------
# 5. 데이터 전처리 (판다스 데이터프레임 생성 및 숫자 변환)
# -----------------------------------------------------------------------------
df = pd.DataFrame(daily_list)

# API 응답은 문자열로 오므로 숫자형으로 변환
numeric_cols = ["rank", "rankInten", "audiCnt", "audiAcc", "scrnCnt", "showCnt"]
for col in numeric_cols:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)

# -----------------------------------------------------------------------------
# 6. 전날 대비 순위 증감(rankInten) 및 트로피(🏆) 가공 함수
# -----------------------------------------------------------------------------
def format_rank_change(val):
    if val > 0:
        return f"🔺 {val}"
    elif val < 0:
        return f"🔹 {abs(val)}"
    else:
        return "-"

def format_movie_title(row):
    title = row["movieNm"]
    # 누적 관객수가 100만 명(1,000,000명) 이상인 경우 트로피 붙이기
    if row["audiAcc"] >= 1000000:
        return f"{title} 🏆"
    return title

# 가공된 데이터 칼럼 생성
df["rankChange"] = df["rankInten"].apply(format_rank_change)
df["displayMovieNm"] = df.apply(format_movie_title, axis=1)

# -----------------------------------------------------------------------------
# 7. 1위 영화 핵심 지표 카드 (Metrics Cards)
# -----------------------------------------------------------------------------
top_movie = df.iloc[0]

st.divider()
st.subheader(f"🥇 1위 영화: {top_movie['displayMovieNm']}")

col1, col2, col3 = st.columns(3)
with col1:
    st.metric(
        label="당일 관객수",
        value=f"{top_movie['audiCnt']:,} 명"
    )
with col2:
    st.metric(
        label="누적 관객수",
        value=f"{top_movie['audiAcc']:,} 명"
    )
with col3:
    st.metric(
        label="상영 스크린수",
        value=f"{top_movie['scrnCnt']:,} 개"
    )

st.divider()

# -----------------------------------------------------------------------------
# 8. 관객수 상위 5편 막대그래프
# -----------------------------------------------------------------------------
st.subheader("📊 상위 5개 영화 당일 관객수 비교")

top_5_df = df.head(5).copy()

# 막대그래프 생성을 위한 데이터 가공 (영화명을 인덱스로 지정)
chart_data = top_5_df[["displayMovieNm", "audiCnt"]].set_index("displayMovieNm")
chart_data.columns = ["관객수"]

st.bar_chart(chart_data)

st.divider()

# -----------------------------------------------------------------------------
# 9. 박스오피스 전체 순위 표 출력
# -----------------------------------------------------------------------------
st.subheader("📋 전체 순위 목록")

# 표시할 주요 칼럼 선택 및 가공된 칼럼 배치
display_cols = ["rank", "rankChange", "displayMovieNm", "openDt", "audiCnt", "audiAcc", "scrnCnt"]
display_df = df[display_cols].copy()

# 표 헤더 명칭 변경
display_df.columns = ["순위", "순위변동", "영화명", "개봉일", "관객수(명)", "누적관객(명)", "스크린수(개)"]

# 숫자 데이터 천 단위 쉼표 포맷 적용
formatted_df = display_df.copy()
formatted_df["관객수(명)"] = formatted_df["관객수(명)"].map("{:,}".format)
formatted_df["누적관객(명)"] = formatted_df["누적관객(명)"].map("{:,}".format)
formatted_df["스크린수(개)"] = formatted_df["스크린수(개)"].map("{:,}".format)

# 최종 데이터프레임 화면 표시
st.dataframe(
    formatted_df,
    use_container_width=True,
    hide_index=True
)
