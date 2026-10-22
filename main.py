import datetime
import json
import requests
import pandas as pd
import pytz
import plotly.express as px
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
# 영화관 테마 Custom CSS 및 1위 영화 호버 시 폭죽/트로피 애니메이션 설정
# -----------------------------------------------------------------------------
BACKGROUND_IMAGE_URL = "https://lh3.googleusercontent.com/gg/AAY1a9qPThfL_0L-EaQ-pGz5Y1B52iG5bW_10285800603"

st.markdown(f"""
<style>
    /* 1. 전체 배경: 극장 스크린 불빛과 어두운 객석 느낌의 그라데이션 + 극장 이미지 */
    .stApp {{
        background: radial-gradient(circle at 50% 0%, rgba(60, 20, 25, 0.8) 0%, rgba(10, 5, 8, 0.95) 70%),
                    url('{BACKGROUND_IMAGE_URL}');
        background-size: cover;
        background-position: top center;
        background-attachment: fixed;
        color: #fce38a;
    }}
    
    /* 2. 제목 및 주요 텍스트 폰트/색상 (골드 톤) */
    h1, h2, h3, p, span {{
        color: #fce38a !important;
        font-family: 'Pretendard', sans-serif;
    }}
    h1 {{ text-shadow: 0 0 15px rgba(252, 227, 138, 0.5); text-align: center; }}
    
    /* 3. 카드 및 표 디자인 (영화관 스크린 프레임 느낌) */
    div[data-testid="stMetric"] {{
        background: linear-gradient(145deg, #2a0810, #170408);
        border: 2px solid #8c2a3c;
        border-radius: 12px;
        padding: 20px;
        box-shadow: 0 10px 20px rgba(0, 0, 0, 0.8), inset 0 0 10px rgba(140, 42, 60, 0.5);
        text-align: center;
    }}
    div[data-testid="stDataFrame"] {{
        background: rgba(15, 8, 12, 0.85);
        border: 1px solid #8c2a3c;
        border-radius: 10px;
    }}
    
    /* 4. 날짜 입력창 커스텀 */
    .stDateInput > div {{
        background-color: #1a080c !important;
        border: 1px solid #fce38a;
        color: #fce38a !important;
    }}
    
    /* ---------------------------------------------------------
       5. 커스텀 막대그래프 & 1위 호버 폭죽 애니메이션 CSS
       --------------------------------------------------------- */
    .custom-bar-chart {{
        display: flex; align-items: flex-end; justify-content: space-around;
        height: 350px; background: rgba(0,0,0,0.4); border-bottom: 3px solid #8c2a3c;
        padding: 20px 10px 0 10px; border-radius: 10px 10px 0 0;
    }}
    .bar-wrapper {{
        display: flex; flex-direction: column; justify-content: flex-end; align-items: center;
        width: 15%; height: 100%;
    }}
    .movie-bar {{
        width: 100%; background: linear-gradient(to top, #5c1622, #e50914);
        border-radius: 6px 6px 0 0; position: relative; transition: all 0.3s;
        box-shadow: 0 0 10px rgba(229, 9, 20, 0.5);
    }}
    .movie-bar:hover {{ filter: brightness(1.3); cursor: pointer; }}
    .bar-value {{ margin-bottom: 8px; font-size: 0.9rem; font-weight: bold; text-shadow: 1px 1px 2px black; }}
    .bar-label {{ margin-top: 12px; font-size: 0.85rem; text-align: center; word-break: keep-all; height: 40px; }}
    
    /* 전체 화면 트로피/폭죽 오버레이 (초기 상태 숨김) */
    .fullscreen-trophy {{
        position: fixed; top: 0; left: 0; width: 100vw; height: 100vh;
        background: radial-gradient(circle, rgba(0,0,0,0.6) 0%, rgba(0,0,0,0.95) 100%);
        display: flex; flex-direction: column; justify-content: center; align-items: center;
        z-index: 999999; opacity: 0; pointer-events: none; visibility: hidden;
    }}
    .fullscreen-trophy span {{ font-size: 10rem; text-shadow: 0 0 50px gold; }}
    .fullscreen-trophy p {{ font-size: 2rem; color: gold; margin-top: 20px; font-weight: bold; }}
    
    /* 1위 막대(.max-bar)에 마우스를 올렸을 때 애니메이션 실행 (1초 동안 유지 후 투명화) */
    .max-bar:hover .fullscreen-trophy {{
        visibility: visible;
        animation: pop-firework 1s ease-out forwards;
    }}
    
    @keyframes pop-firework {{
        0% {{ opacity: 0; transform: scale(0.5); }}
        20% {{ opacity: 1; transform: scale(1.2); }}
        80% {{ opacity: 1; transform: scale(1); }}
        100% {{ opacity: 0; transform: scale(1.5); visibility: hidden; }}
    }}
</style>
""", unsafe_allow_html=True)

st.title("🍿 시네마 박스오피스 라운지")

# -----------------------------------------------------------------------------
# 1. API 키 검증
# -----------------------------------------------------------------------------
if "KOBIS_KEY" not in st.secrets or not st.secrets["KOBIS_KEY"]:
    st.error("❌ 비밀 금고(secrets)에 'KOBIS_KEY'가 설정되어 있지 않습니다.")
    st.stop()
api_key = st.secrets["KOBIS_KEY"]

# -----------------------------------------------------------------------------
# 2. 날짜 선택 (최대 어제까지)
# -----------------------------------------------------------------------------
kst = pytz.timezone("Asia/Seoul")
now_kst = datetime.datetime.now(kst)
yesterday_date = (now_kst - datetime.timedelta(days=1)).date()

col_date, _ = st.columns([1, 2])
with col_date:
    selected_date = st.date_input(
        label="📅 상영 일자 선택",
        value=yesterday_date,
        min_value=datetime.date(2004, 1, 1),
        max_value=yesterday_date
    )

target_date_str = selected_date.strftime("%Y%m%d")
st.markdown(f"<h3 style='text-align:center;'>🎟️ {selected_date.strftime('%Y년 %m월 %d일')} 박스오피스</h3>", unsafe_allow_html=True)
st.divider()

# -----------------------------------------------------------------------------
# 3. 데이터 가져오기 함수 (캐싱 적용)
# -----------------------------------------------------------------------------
@st.cache_data(ttl=3600)
def fetch_box_office(key: str, target_dt: str):
    url = "https://www.kobis.or.kr/kobisopenapi/webservice/rest/boxoffice/searchDailyBoxOfficeList.json"
    try:
        res = requests.get(url, params={"key": key, "targetDt": target_dt}, timeout=10)
        res.raise_for_status()
        return res.json()
    except Exception as e:
        return {"error": str(e)}

data = fetch_box_office(api_key, target_date_str)

if "error" in data or "faultInfo" in data:
    st.error("❌ 데이터를 불러올 수 없습니다. API 키 및 네트워크를 확인해 주세요.")
    st.stop()

daily_list = data.get("boxOfficeResult", {}).get("dailyBoxOfficeList", [])
if not daily_list:
    st.warning("⚠️ 그날은 아직 집계 전입니다.")
    st.stop()

# -----------------------------------------------------------------------------
# 4. 데이터 전처리
# -----------------------------------------------------------------------------
df = pd.DataFrame(daily_list)
numeric_cols = ["rank", "rankInten", "audiCnt", "audiAcc", "scrnCnt"]
for col in numeric_cols:
    df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)

def format_rank_change(val):
    if val > 0: return f"🔺 {val}"
    elif val < 0: return f"🔹 {abs(val)}"
    return "-"

df["rankChange"] = df["rankInten"].apply(format_rank_change)

# -----------------------------------------------------------------------------
# 5. 1위 영화 핵심 지표 카드
# -----------------------------------------------------------------------------
top_movie = df.iloc[0]
st.markdown(f"<h2 style='text-align:center;'>🥇 오늘의 1위 영화: {top_movie['movieNm']}</h2>", unsafe_allow_html=True)

col1, col2, col3 = st.columns(3)
with col1: st.metric(label="당일 관객수", value=f"{top_movie['audiCnt']:,} 명")
with col2: st.metric(label="누적 관객수", value=f"{top_movie['audiAcc']:,} 명")
with col3: st.metric(label="상영 스크린수", value=f"{top_movie['scrnCnt']:,} 개")
st.divider()

# -----------------------------------------------------------------------------
# 6. 상위 5개 영화 최근 7일 관객수 추이 (마우스 스크롤 문제 해결: Plotly 사용)
# -----------------------------------------------------------------------------
st.subheader("📈 상위 5개 영화 7일 관객수 추이")

top_5_titles = df.head(5)["movieNm"].tolist()
past_7_dates = [selected_date - datetime.timedelta(days=i) for i in range(6, -1, -1)]

trend_records = []
for p_date in past_7_dates:
    p_data = fetch_box_office(api_key, p_date.strftime("%Y%m%d"))
    p_list = p_data.get("boxOfficeResult", {}).get("dailyBoxOfficeList", [])
    
    for item in p_list:
        if item["movieNm"] in top_5_titles:
            trend_records.append({
                "날짜": p_date.strftime("%m/%d"),
                "영화명": item["movieNm"],
                "관객수": int(item.get("audiCnt", 0))
            })

if trend_records:
    trend_df = pd.DataFrame(trend_records)
    
    # Plotly를 사용하여 스크롤 시 확대/축소되지 않도록 고정(fixedrange)
    fig = px.line(trend_df, x="날짜", y="관객수", color="영화명", markers=True)
    fig.update_layout(
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#fce38a"),
        dragmode=False,  # 드래그 줌 방지
        hovermode="x unified"
    )
    fig.update_xaxes(fixedrange=True, showgrid=False) # X축 스크롤/줌 방지
    fig.update_yaxes(fixedrange=True, gridcolor="rgba(252, 227, 138, 0.2)") # Y축 스크롤/줌 방지
    
    st.plotly_chart(fig, use_container_width=True, config={'scrollZoom': False})

st.divider()

# -----------------------------------------------------------------------------
# 7. 선택일 상위 5개 영화 관객수 (HTML/CSS 기반 호버 팡파르 애니메이션)
# -----------------------------------------------------------------------------
st.subheader("📊 상위 5개 영화 관객수 비교 (1위 영화 막대에 마우스를 올려보세요!)")

top_5_df = df.head(5)
max_audi = top_5_df["audiCnt"].max()

# 순수 HTML/CSS로 그래프 생성
html_bars = '<div class="custom-bar-chart">'
for _, row in top_5_df.iterrows():
    pct = (row["audiCnt"] / max_audi) * 100 if max_audi > 0 else 0
    is_max = (row["audiCnt"] == max_audi)
    
    bar_class = "movie-bar max-bar" if is_max else "movie-bar"
    
    # 1위 영화 막대에만 전체화면 팡파르 오버레이 삽입
    trophy_overlay = f"""
    <div class="fullscreen-trophy">
        <span>🏆 🎉 🎊</span>
        <p>{row['movieNm']} 1위 달성!</p>
    </div>
    """ if is_max else ""
    
    html_bars += f"""
    <div class="bar-wrapper">
        <div class="bar-value">{row['audiCnt']:,}명</div>
        <div class="{bar_class}" style="height: {pct}%;">
            {trophy_overlay}
        </div>
        <div class="bar-label">{row['movieNm']}</div>
    </div>
    """
html_bars += '</div>'

# 렌더링
st.markdown(html_bars, unsafe_allow_html=True)
st.divider()

# -----------------------------------------------------------------------------
# 8. 박스오피스 전체 순위 표 출력 (100만 이모지 제거)
# -----------------------------------------------------------------------------
st.subheader("📋 전체 순위 목록")

display_cols = ["rank", "rankChange", "movieNm", "openDt", "audiCnt", "audiAcc", "scrnCnt"]
display_df = df[display_cols].copy()
display_df.columns = ["순위", "순위변동", "영화명", "개봉일", "관객수(명)", "누적관객(명)", "스크린수(개)"]

for col in ["관객수(명)", "누적관객(명)", "스크린수(개)"]:
    display_df[col] = display_df[col].map("{:,}".format)

st.dataframe(display_df, use_container_width=True, hide_index=True)
