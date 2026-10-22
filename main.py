import datetime
import json
import requests
import pandas as pd
import pytz
import streamlit as st
import altair as alt

# -----------------------------------------------------------------------------
# 페이지 기본 설정
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="시네마 박스오피스",
    page_icon="🍿",
    layout="wide"
)

# -----------------------------------------------------------------------------
# 영화관 테마(버건디/레드 카펫) AI 배경 및 폭죽 애니메이션 CSS 적용
# -----------------------------------------------------------------------------
BACKGROUND_IMAGE_URL = "https://lh3.googleusercontent.com/gg/AAY1a9qPThfL_0L-EaQ-pGz5Y1B52iG5bW_10285800603"

st.markdown(f"""
<style>
    /* 전체 배경: 어두운 검정 대신 영화관을 연상시키는 벨벳 레드/버건디 오버레이 적용 */
    .stApp {{
        background: linear-gradient(rgba(100, 15, 25, 0.7), rgba(40, 5, 10, 0.85)),
                    url('{BACKGROUND_IMAGE_URL}');
        background-size: cover;
        background-position: center;
        background-attachment: fixed;
        color: #fdf5e6;
    }}
    
    /* 제목 및 주요 헤더를 영화관 간판 같은 골드 톤으로 강조 */
    h1, h2, h3 {{
        color: #fce38a !important;
        font-family: 'Pretendard', sans-serif;
        text-shadow: 2px 2px 5px rgba(0,0,0,0.6);
    }}
    
    /* 지표 카드 투명도 및 테두리 (레드&골드) */
    div[data-testid="stMetric"] {{
        background: rgba(80, 15, 25, 0.6);
        border: 1px solid rgba(252, 227, 138, 0.5);
        border-radius: 12px;
        padding: 15px;
        box-shadow: 0 5px 15px rgba(0, 0, 0, 0.5);
        backdrop-filter: blur(5px);
    }}
    
    /* 데이터프레임 표 스타일 (버건디 배경) */
    div[data-testid="stDataFrame"] {{
        background: rgba(60, 10, 20, 0.75);
        border-radius: 10px;
        border: 1px solid rgba(252, 227, 138, 0.3);
        backdrop-filter: blur(5px);
    }}
    
    /* 달력 위젯 스타일 */
    .stDateInput > div {{
        background-color: rgba(90, 20, 30, 0.85) !important;
        color: #ffffff !important;
        border-radius: 8px;
        border: 1px solid #d4af37;
    }}
    
    /* 커스텀 HTML 막대그래프 전용 스타일 */
    .cinema-bar-chart {{
        display: flex;
        justify-content: space-around;
        align-items: flex-end;
        height: 350px;
        background: rgba(0, 0, 0, 0.3);
        padding: 20px 10px;
        border-radius: 10px;
        border-bottom: 3px solid #d4af37;
        position: relative;
    }}
    .cinema-bar-wrapper {{
        display: flex;
        flex-direction: column;
        align-items: center;
        width: 18%;
        height: 100%;
        justify-content: flex-end;
    }}
    .cinema-bar {{
        width: 100%;
        background: linear-gradient(to top, #a61b29, #ff4500);
        border-radius: 6px 6px 0 0;
        transition: transform 0.2s, filter 0.2s;
        box-shadow: 2px 0 10px rgba(0,0,0,0.5);
        position: relative;
    }}
    .cinema-bar:hover {{
        transform: scaleY(1.03);
        filter: brightness(1.3);
        cursor: pointer;
    }}
    .bar-value {{
        color: #fff; font-weight: bold; font-size: 0.9rem; margin-bottom: 5px;
    }}
    .bar-label {{
        color: #fce38a; font-size: 0.85rem; margin-top: 10px; text-align: center; word-break: keep-all; height: 40px;
    }}
    
    /* 1위 막대 호버 시 작동할 폭죽 효과 컨테이너 */
    .fireworks-overlay {{
        position: fixed;
        top: 0; left: 0; width: 100vw; height: 100vh;
        pointer-events: none;
        z-index: 999999;
        display: none; /* 기본은 숨김 */
    }}
    
    /* .highest-bar(최고 막대)에 마우스를 올리면 폭죽 오버레이 표시 */
    .highest-bar:hover ~ .fireworks-overlay {{
        display: block;
    }}
    
    /* 폭죽 파티클(트로피) 애니메이션 설정 */
    .trophy-particle {{
        position: absolute;
        top: 50%; left: 50%;
        font-size: 4rem;
        opacity: 0;
    }}
    
    /* 1초 동안만 사방으로 터지고 사라지는 애니메이션 (forwards로 종료 상태 유지) */
    .highest-bar:hover ~ .fireworks-overlay .p1 {{ animation: pop1 1s ease-out forwards; }}
    .highest-bar:hover ~ .fireworks-overlay .p2 {{ animation: pop2 1s ease-out forwards; }}
    .highest-bar:hover ~ .fireworks-overlay .p3 {{ animation: pop3 1s ease-out forwards; }}
    .highest-bar:hover ~ .fireworks-overlay .p4 {{ animation: pop4 1s ease-out forwards; }}
    .highest-bar:hover ~ .fireworks-overlay .p5 {{ animation: pop5 1s ease-out forwards; }}
    
    @keyframes pop1 {{ 0% {{ transform: translate(0, 0) scale(0.5); opacity: 1; }} 100% {{ transform: translate(-30vw, -40vh) scale(2.5) rotate(-45deg); opacity: 0; }} }}
    @keyframes pop2 {{ 0% {{ transform: translate(0, 0) scale(0.5); opacity: 1; }} 100% {{ transform: translate(30vw, -40vh) scale(2.5) rotate(45deg); opacity: 0; }} }}
    @keyframes pop3 {{ 0% {{ transform: translate(0, 0) scale(0.5); opacity: 1; }} 100% {{ transform: translate(-40vw, 10vh) scale(2.5) rotate(-90deg); opacity: 0; }} }}
    @keyframes pop4 {{ 0% {{ transform: translate(0, 0) scale(0.5); opacity: 1; }} 100% {{ transform: translate(40vw, 10vh) scale(2.5) rotate(90deg); opacity: 0; }} }}
    @keyframes pop5 {{ 0% {{ transform: translate(0, 0) scale(0.5); opacity: 1; }} 100% {{ transform: translate(0, -50vh) scale(3); opacity: 0; }} }}
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
# 3. KOBIS API 데이터 가져오기
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
    st.error("❌ API 응답 오류가 발생했습니다 (인증키 오류 가능성).")
    st.stop()

daily_list = data.get("boxOfficeResult", {}).get("dailyBoxOfficeList", [])
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

df["rankChange"] = df["rankInten"].apply(format_rank_change)

# -----------------------------------------------------------------------------
# 5. 1위 영화 지표 카드
# -----------------------------------------------------------------------------
top_movie = df.iloc[0]

st.divider()
st.subheader(f"🥇 1위 영화: {top_movie['movieNm']}")

col1, col2, col3 = st.columns(3)
with col1:
    st.metric(label="당일 관객수", value=f"{top_movie['audiCnt']:,} 명")
with col2:
    st.metric(label="누적 관객수", value=f"{top_movie['audiAcc']:,} 명")
with col3:
    st.metric(label="상영 스크린수", value=f"{top_movie['scrnCnt']:,} 개")

st.divider()

# -----------------------------------------------------------------------------
# 6. 최근 7일간 추이 꺾은선 그래프 (스크롤 줌(Zoom) 문제 해결을 위해 Altair 사용)
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
    
    # Altair를 이용해 인터랙티브 요소를 제어 (스크롤로 줌 인/아웃되는 현상 방지)
    line_chart = alt.Chart(trend_df).mark_line(point=True).encode(
        x=alt.X("날짜:O", sort=None, title="날짜"),
        y=alt.Y("관객수:Q", title="관객수(명)"),
        color=alt.Color("영화명:N", title="영화명"),
        tooltip=["날짜", "영화명", "관객수"]
    ).properties(height=400)
    
    st.altair_chart(line_chart, use_container_width=True)

st.divider()

# -----------------------------------------------------------------------------
# 7. 관객수 상위 5편 커스텀 막대그래프 (1위 막대 호버 시 트로피 폭죽 효과)
# -----------------------------------------------------------------------------
st.subheader("📊 선택일 상위 5개 영화 관객수 비교 (1위 막대에 마우스를 올려보세요!)")

top_5_df = df.head(5).copy()
max_audi = top_5_df["audiCnt"].max()

# HTML 문자열 조립: 1위 막대에만 'highest-bar' 클래스 부여
html_chart = '<div class="cinema-bar-chart">'

for idx, row in top_5_df.iterrows():
    height_pct = (row["audiCnt"] / max_audi) * 100 if max_audi > 0 else 0
    is_highest = "highest-bar" if row["audiCnt"] == max_audi else ""
    
    html_chart += f"""
    <div class="cinema-bar-wrapper">
        <div class="bar-value">{row['audiCnt']:,}</div>
        <div class="cinema-bar {is_highest}" style="height: {height_pct}%;"></div>
        <div class="bar-label">{row['movieNm']}</div>
    </div>
    """

# 폭죽(트로피) 효과를 내기 위한 숨겨진 오버레이 추가 (막대그래프와 같은 형제 노드에 위치)
html_chart += """
    <div class="fireworks-overlay">
        <div class="trophy-particle p1">🏆</div>
        <div class="trophy-particle p2">🏆</div>
        <div class="trophy-particle p3">🏆</div>
        <div class="trophy-particle p4">🏆</div>
        <div class="trophy-particle p5">🏆</div>
    </div>
</div>
"""

st.markdown(html_chart, unsafe_allow_html=True)

st.divider()

# -----------------------------------------------------------------------------
# 8. 박스오피스 전체 순위 표 출력
# -----------------------------------------------------------------------------
st.subheader("📋 전체 순위 목록")

display_cols = ["rank", "rankChange", "movieNm", "openDt", "audiCnt", "audiAcc", "scrnCnt"]
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
