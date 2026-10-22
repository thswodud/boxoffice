import datetime
import json
import requests
import pandas as pd
import pytz
import altair as alt
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
# 영화관 AI 배경 이미지 적용 Custom CSS
# -----------------------------------------------------------------------------
BACKGROUND_IMAGE_URL = "https://lh3.googleusercontent.com/gg/AAY1a9qPThfL_0L-EaQ-pGz5Y1B52iG5bW_10285800603"

st.markdown(f"""
<style>
    /* 전체 배경: 영화관 내부 이미지 및 어두운 오버레이 */
    .stApp {{
        background: linear-gradient(rgba(10, 5, 8, 0.85), rgba(10, 5, 8, 0.85)),
                    url('{BACKGROUND_IMAGE_URL}');
        background-size: cover;
        background-position: center;
        background-attachment: fixed;
        color: #f1e4e6;
    }}
    
    h1, h2, h3 {{
        color: #fce38a !important;
        font-family: 'Pretendard', sans-serif;
        text-shadow: 3px 3px 6px rgba(0,0,0,0.9);
    }}
    
    div[data-testid="stMetric"] {{
        background: rgba(20, 10, 15, 0.75);
        border: 1px solid rgba(252, 227, 138, 0.3);
        border-radius: 12px;
        padding: 15px;
        box-shadow: 0 8px 20px rgba(0, 0, 0, 0.7);
        backdrop-filter: blur(5px);
    }}
    
    div[data-testid="stDataFrame"] {{
        background: rgba(15, 8, 12, 0.75);
        border-radius: 10px;
        border: 1px solid rgba(252, 227, 138, 0.2);
        backdrop-filter: blur(5px);
    }}
    
    .stDateInput > div {{
        background-color: rgba(25, 12, 18, 0.85) !important;
        color: #ffffff !important;
        border-radius: 8px;
        border: 1px solid #8c2a3c;
    }}
</style>
""", unsafe_allow_html=True)

st.title("🍿 시네마 일별 박스오피스")
st.caption("영화진흥위원회(KOBIS) Open API 기반 박스오피스 조회 앱")

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
# 3. KOBIS API 단일 날짜 호출 함수
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
    st.stop()

if "faultInfo" in data:
    fault = data["faultInfo"]
    st.error("❌ API 응답 오류가 발생했습니다.")
    st.stop()

box_office_result = data.get("boxOfficeResult", {})
daily_list = box_office_result.get("dailyBoxOfficeList", [])

if not daily_list:
    st.warning("⚠️ 그날은 아직 집계 전입니다.")
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
    if val > 0: return f"🔺 {val}"
    elif val < 0: return f"🔹 {abs(val)}"
    else: return "-"

def format_movie_title(row):
    title = row["movieNm"]
    if row["audiAcc"] >= 1000000: return f"{title} 🏆"
    return title

df["rankChange"] = df["rankInten"].apply(format_rank_change)
df["displayMovieNm"] = df.apply(format_movie_title, axis=1)

# -----------------------------------------------------------------------------
# 5. 1위 영화 핵심 지표 카드
# -----------------------------------------------------------------------------
top_movie = df.iloc[0]

st.divider()
st.subheader(f"🥇 1위 영화: {top_movie['displayMovieNm']}")

col1, col2, col3 = st.columns(3)
with col1: st.metric(label="당일 관객수", value=f"{top_movie['audiCnt']:,} 명")
with col2: st.metric(label="누적 관객수", value=f"{top_movie['audiAcc']:,} 명")
with col3: st.metric(label="상영 스크린수", value=f"{top_movie['scrnCnt']:,} 개")

st.divider()

# -----------------------------------------------------------------------------
# 6. Top 5 영화의 최근 7일간 일별 관객수 추이 선 그래프 (휠 스크롤 잠금 적용)
# -----------------------------------------------------------------------------
st.subheader("📈 상위 5개 영화의 최근 7일 관객수 추이")

top_5_titles = df.head(5)["movieNm"].tolist()
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
        filtered_p = p_df[p_df["movieNm"].isin(top_5_titles)]
        for _, row in filtered_p.iterrows():
            trend_records.append({
                "날짜": date_label,
                "영화명": row["movieNm"],
                "관객수": row["audiCnt"]
            })

if trend_records:
    trend_df = pd.DataFrame(trend_records)
    
    # 줌/스크롤을 막고 툴팁만 남긴 Altair 라인 차트 생성
    line_chart = alt.Chart(trend_df).mark_line(point=True).encode(
        x=alt.X("날짜", type="nominal", title="날짜", sort=None),
        y=alt.Y("관객수", type="quantitative", title="당일 관객수(명)"),
        color=alt.Color("영화명", type="nominal", title="영화명"),
        tooltip=["날짜", "영화명", alt.Tooltip("관객수", format=",")]
    ).properties(height=400)
    
    st.altair_chart(line_chart, use_container_width=True)

st.divider()

# -----------------------------------------------------------------------------
# 7. 관객수 상위 5편 막대그래프 (휠 스크롤 잠금 적용)
# -----------------------------------------------------------------------------
st.subheader("📊 선택일 상위 5개 영화 관객수 비교")

top_5_df = df.head(5).copy()

# 줌/스크롤을 막고 툴팁만 남긴 Altair 막대 차트 생성
bar_chart = alt.Chart(top_5_df).mark_bar(color="#fce38a").encode(
        x=alt.X("displayMovieNm", type="nominal", title="영화명", sort=None, axis=alt.Axis(labelAngle=-45)),
        y=alt.Y("audiCnt", type="quantitative", title="당일 관객수(명)"),
        tooltip=["displayMovieNm", alt.Tooltip("audiCnt", format=",")]
    ).properties(height=400)

st.altair_chart(bar_chart, use_container_width=True)

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

st.dataframe(formatted_df, use_container_width=True, hide_index=True)
