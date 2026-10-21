import datetime
import requests
import pandas as pd
import pytz
import streamlit as st

# 페이지 기본 설정 (타이틀, 레이아웃)
st.set_page_config(
    page_title="어제 자 박스오피스",
    page_icon="🎬",
    layout="wide"
)

st.title("🎬 어제 자 일별 박스오피스")
st.caption("영화진흥위원회(KOBIS) Open API를 활용한 데이터 조회 앱입니다.")

# -----------------------------------------------------------------------------
# 1. API 키 불러오기 (secrets.toml 설정 확인)
# -----------------------------------------------------------------------------
if "KOBIS_KEY" not in st.secrets:
    st.error("❌ 비밀 금고(secrets)에 'KOBIS_KEY'가 설정되어 있지 않습니다.")
    st.info(
        "💡 **해결 방법:**\n"
        "1. 스트림릿 클라우드의 대시보드로 이동합니다.\n"
        "2. 앱 설정의 **Secrets** 탭을 엽니다.\n"
        "3. 아래와 같이 KOBIS 발급 키를 등록해 주세요:\n\n"
        '```toml\nKOBIS_KEY = "발급받은_키_문자열"\n```'
    )
    st.stop()

api_key = st.secrets["KOBIS_KEY"]

# -----------------------------------------------------------------------------
# 2. 한국 시간(KST) 기준 '어제' 날짜 계산
# -----------------------------------------------------------------------------
# 배포 서버의 기본 시계(UTC) 대신 한국 표준시(Asia/Seoul)를 사용합니다.
kst = pytz.timezone("Asia/Seoul")
now_kst = datetime.datetime.now(kst)
yesterday_kst = now_kst - datetime.timedelta(days=1)

# API 요청에 맞는 yyyymmdd 8자리 문자열 형식 생성
target_date_str = yesterday_kst.strftime("%Y%m%d")
display_date_str = yesterday_kst.strftime("%Y년 %m월 %d일")

st.markdown(f"### 📅 **{display_date_str}** 기준 데이터")

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
    st.error("❌ 영화진흥위원회 서버와 통신하는 중 에러가 발생했습니다.")
    st.info(f"💡 **상세 오류 내용:** {err}\n\n네트워크 상태를 확인하거나 잠시 후 다시 시도해 주세요.")
    st.stop()

# -----------------------------------------------------------------------------
# 4. 예외 및 오류 처리 (faultInfo 응답 및 데이터 유무 확인)
# -----------------------------------------------------------------------------
# KOBIS API는 인증키가 오류여도 HTTP STATUS 200과 함께 faultInfo 객체를 반환합니다.
if "faultInfo" in data:
    fault = data["faultInfo"]
    st.error("❌ API 응답 오류가 발생했습니다 (인증키 오류 가능성).")
    st.warning(f"⚠️ **오류 메시지:** {fault.get('message', '알 수 없는 오류')}")
    st.info("💡 **확인해 보세요:** Streamlit Secrets에 입력한 `KOBIS_KEY`가 올바른지 다시 점검해 주세요.")
    st.stop()

# 데이터 목록 추출
box_office_result = data.get("boxOfficeResult", {})
daily_list = box_office_result.get("dailyBoxOfficeList", [])

if not daily_list:
    st.warning("⚠️ 해당 날짜의 박스오피스 데이터가 비어 있습니다.")
    st.info(
        "💡 **확인해 보세요:**\n"
        "- 일시적인 API 서버 집계 지연일 수 있습니다.\n"
        "- KOBIS 홈페이지에서 해당 날짜 서비스 상태를 확인해 주세요."
    )
    st.stop()

# -----------------------------------------------------------------------------
# 5. 데이터 처리 및 전처리 (데이터 타입 변환)
# -----------------------------------------------------------------------------
df = pd.DataFrame(daily_list)

# KOBIS API는 모든 숫자를 문자열(String)로 전달하므로 정수(Integer)형으로 변환합니다.
numeric_columns = ["rank", "audiCnt", "audiAcc", "scrnCnt", "showCnt"]
for col in numeric_columns:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)

# -----------------------------------------------------------------------------
# 6. 1위 영화 지표 카드 (Metrics Cards)
# -----------------------------------------------------------------------------
top_movie = df.iloc[0]

st.divider()
st.subheader(f"🥇 1위: {top_movie['movieNm']}")

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
# 7. 관객수 상위 5편 막대그래프
# -----------------------------------------------------------------------------
st.subheader("📊 상위 5개 영화 당일 관객수 비교")

top_5_df = df.head(5).copy()

# 막대그래프 생성을 위해 필요한 칼럼만 추출 및 이름 변경
chart_data = top_5_df[["movieNm", "audiCnt"]].set_index("movieNm")
chart_data.columns = ["관객수"]

st.bar_chart(chart_data)

st.divider()

# -----------------------------------------------------------------------------
# 8. 박스오피스 데이터 표 출력
# -----------------------------------------------------------------------------
st.subheader("📋 일별 박스오피스 전체 순위")

# 표에 출력할 주요 칼럼 선택 및 한글 이름 변경
display_df = df[["rank", "movieNm", "openDt", "audiCnt", "audiAcc", "scrnCnt"]].copy()
display_df.columns = ["순위", "영화명", "개봉일", "관객수(명)", "누적관객(명)", "스크린수(개)"]

# 숫자에 천 단위 쉼표(,) 포맷 적용
formatted_df = display_df.copy()
formatted_df["관객수(명)"] = formatted_df["관객수(명)"].map("{:,}".format)
formatted_df["누적관객(명)"] = formatted_df["누적관객(명)"].map("{:,}".format)
formatted_df["스크린수(개)"] = formatted_df["스크린수(개)"].map("{:,}".format)

st.dataframe(
    formatted_df,
    use_container_width=True,
    hide_index=True
)
