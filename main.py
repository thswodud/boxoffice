import datetime
import json
import requests
import pandas as pd
import pytz
import streamlit as st

# -----------------------------------------------------------------------------
# 페이지 기본 설정
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="시네마 박스오피스",
    page_icon="🍿",
    layout="wide"
)

# -----------------------------------------------------------------------------
# 영화관 테마 Custom CSS 주입 (다크 버건디 테마)
# -----------------------------------------------------------------------------
st.markdown("""
<style>
    /* 전체 배경: 어두운 시네마 홀 느낌 */
    .stApp {
        background: linear-gradient(135deg, #0d0205 0%, #1a080c 50%, #050203 100%);
        color: #f1e4e6;
    }
    
    /* 제목 및 헤더 스타일 */
    h1, h2, h3 {
        color: #f3ce72 !important;
        font-family: 'Pretendard', sans-serif;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.8);
    }
    
    /* 카드 / 지표 상자 스타일링 */
    div[data-testid="stMetric"] {
        background: rgba(35, 12, 18, 0.7);
        border: 1px solid #5a1e28;
        border-radius: 12px;
        padding: 15px;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.5);
    }
    
    /* 데이터프레임/표 스타일 */
    div[data-testid="stDataFrame"] {
        background: rgba(20, 7, 10, 0.6);
        border-radius: 10px;
        border: 1px solid #42161e;
    }
    
    /* 버튼 및 인풋 위젯 스타일 */
    .stDateInput > div {
        background-color: #1f0b10 !important;
        color: #ffffff !important;
        border-radius: 8px;
        border: 1px solid #6b2330;
    }
</style>
""", unsafe_allow_html=True)

st.title("🍿 시네마 일별 박스오피스")
st.caption("영화진흥위원회(KOBIS) Open API 기반 조회 앱")

# -----------------------------------------------------------------------------
# 1. API 키 검증 (Streamlit Secrets)
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
# 2. 한국 시간(KST) 기준 날짜 선택
# -----------------------------------------------------------------------------
kst = pytz.timezone("Asia/Seoul")
now_kst = datetime.datetime.now(kst)
yesterday_date = (now_kst - datetime.timedelta(days=1)).date()
min_date = datetime.date(2004, 1, 1)

selected_date = st.date_input(
    label="📅 조회할 날짜를 선택하세요 (최대 어제까지 가능)",
    value=yesterday_date,
    min_value=min_date,
    max_value=yesterday_date
)

target_date_str = selected_date.strftime("%Y%m%d")
display_date_str = selected_date.strftime("%Y년 %m월 %d일")

st.markdown(f"### 🎟️ **{display_date_str}** 상영 현황")

# -----------------------------------------------------------------------------
# 3. KOBIS API 단일 날짜 호출 함수 및 데이터 가져오기
# -----------------------------------------------------------------------------
@st.cache_data(ttl=3600)
def fetch_box_office(key: str, target_dt: str):
    url = "https://www.kobis.or.kr/kobisopenapi/webservice/rest/boxoffice/searchDailyBoxOfficeList.json"
    params = {"key": key, "targetDt": target_dt}
    try:
        res = requests.get(url, params=params, timeout=10)
        res.raise_for_status()
        return res.json()
    except Exception as e:
        return {"error": str(e)}

data = fetch_box_office(api_key, target_date_str)

if "error" in data:
    st.error("❌ API 서버와의 통신 중 오류가 발생했습니다.")
    st.warning(f"⚠️ **세부 오류:** {data['error']}")
    st.stop()

if "faultInfo" in data:
    fault = data["faultInfo"]
    st.error("❌ API 응답 오류가 발생했습니다 (인증키 오류 가능성).")
    st.warning(f"⚠️ **오류 메시지:** {fault.get('message', '알 수 없는 오류')}")
    st.stop()

box_office_result = data.get("boxOfficeResult", {})
daily_list = box_office_result.get("dailyBoxOfficeList", [])

if not daily_list:
    st.warning("⚠️ 그날은 아직 집계 전입니다.")
    st.info("💡 **안내:** 영화진흥위원회 서버의 일별 박스오피스 데이터 집계가 완료된 후 조회가 가능합니다.")
    st.stop()

# -----------------------------------------------------------------------------
# 4. 선택일 데이터 전처리
# -----------------------------------------------------------------------------
df = pd.DataFrame(daily_list)
numeric_cols = ["rank", "rankInten", "audiCnt", "audiAcc", "scrnCnt", "showCnt"]
for col in numeric_cols:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)

def format_rank_change(val):
    if val > 0:
        return f"🔺 {val}"
    elif val < 0:
        return f"🔹 {abs(val)}"
    else:
        return "-"

def format_movie_title(row):
    title = row["movieNm"]
    if row["audiAcc"] >= 1000000:
        return f"{title} 🏆"
    return title

df["rankChange"] = df["rankInten"].apply(format_rank_change)
df["displayMovieNm"] = df.apply(format_movie_title, axis=1)

# -----------------------------------------------------------------------------
# 5. 1위 영화 핵심 지표 카드 (Metrics Cards)
# -----------------------------------------------------------------------------
top_movie = df.iloc[0]

st.divider()
st.subheader(f"🥇 1위 영화: {top_movie['displayMovieNm']}")

col1, col2, col3 = st.columns(3)
with col1:
    st.metric(label="당일 관객수", value=f"{top_movie['audiCnt']:,} 명")
with col2:
    st.metric(label="누적 관객수", value=f"{top_movie['audiAcc']:,} 명")
with col3:
    st.metric(label="상영 스크린수", value=f"{top_movie['scrnCnt']:,} 개")

st.divider()

# -----------------------------------------------------------------------------
# 6. Top 5 영화의 최근 7일간 일별 관객수 추이 그래프
# -----------------------------------------------------------------------------
st.subheader("📈 상위 5개 영화의 최근 7일 관객수 추이")

# 선택된 날짜 기준 상위 5개 영화 이름 가져오기
top_5_titles = df.head(5)["movieNm"].tolist()

# 선택일 포함 이전 7일간의 날짜 리스트 생성
past_7_dates = [selected_date - datetime.timedelta(days=i) for i in range(6, -1, -1)]

trend_records = []
for p_date in past_7_dates:
    p_date_str = p_date.strftime("%Y%m%d")
    p_data = fetch_box_office(api_key, p_date_str)
    
    p_list = p_data.get("boxOfficeResult", {}).get("dailyBoxOfficeList", [])
    p_df = pd.DataFrame(p_list)
    
    date_label = p_date.strftime("%m/%d")
    
    if not p_df.empty and "movieNm" in p_df.columns:
        p_df["audiCnt"] = pd.to_numeric(p_df["audiCnt"], errors="coerce").fillna(0).astype(int)
        # 선택된 Top 5 영화만 필터링
        filtered_p = p_df[p_df["movieNm"].isin(top_5_titles)]
        for _, row in filtered_p.iterrows():
            trend_records.append({
                "날짜": date_label,
                "영화명": row["movieNm"],
                "관객수": row["audiCnt"]
            })

if trend_records:
    trend_df = pd.DataFrame(trend_records)
    # 피벗 테이블 형태로 변환 (행: 날짜, 열: 영화명, 값: 관객수)
    pivot_trend = trend_df.pivot(index="날짜", columns="영화명", values="관객수").fillna(0)
    st.line_chart(pivot_trend)
else:
    st.info("💡 이전 날짜 추이 데이터를 불러오는 중입니다.")

st.divider()

# -----------------------------------------------------------------------------
# 7. 관객수 상위 5편 막대그래프 (당일 기준)
# -----------------------------------------------------------------------------
st.subheader("📊 선택일 상위 5개 영화 관객수 비교")

top_5_df = df.head(5).copy()
chart_data = top_5_df[["displayMovieNm", "audiCnt"]].set_index("displayMovieNm")
chart_data.columns = ["관객수"]

st.bar_chart(chart_data)

st.divider()

# -----------------------------------------------------------------------------
# 8. 박스오피스 전체 순위 표 출력
# -----------------------------------------------------------------------------
st.subheader("📋 전체 순위 목록")

display_cols = ["rank", "rankChange", "displayMovieNm", "openDt", "audiCnt", "audiAcc", "scrnCnt"]
display_df = df[display_cols].copy()
display_df.columns = ["순위", "순위변동", "영화명", "개봉일", "관객수(명)", "누적관객(명)", "스크린수(개)"]

formatted_df = display_df.copy()
formatted_df["관객수(명)"] = formatted_df["관객수(명)"].map("{:,}".format)
formatted_df["누적관객(명)"] = formatted_df["누적관객(명)"].map("{:,}".format)
formatted_df["스크린수(개)"] = formatted_df["스크린수(개)"].map("{:,}".format)

st.dataframe(
    formatted_df,
    use_container_width=True,
    hide_index=True
)
