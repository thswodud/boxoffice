import datetime
import requests
import pandas as pd
import pytz
import streamlit as st
import발생할 수 있는 오류의 원인은 크게 세 가지입니다. 코드를 복사하는 과정에서 **눈에 보이지 않는 특수 공백(NBSP)**이 섞여 들어가 파이썬 문법 오류(IndentationError)가 발생했거나, 새로 추가된 **`plotly` 라이브러리가 설치되지 않았을 경우**, 또는 **API 키가 잘못되었을 때의 예외 처리**가 누락되어 엉뚱한 에러가 났을 가능성이 높습니다.

이 문제들을 모두 해결하고, 복사-붙여넣기 시 공백 문자가 깨지지 않도록 정제한 전체 코드입니다.

### 1. `main.py` 전체 코드

```python
import datetime
import json
import requests
import pandas as pd
import pytz
import streamlit as st
import streamlit.components.v1 as components
import plotly.express as px

# -----------------------------------------------------------------------------
# 페이지 기본 설정
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="시네마 박스오피스",
    page_icon="🍿",
    layout="wide"
)

# -----------------------------------------------------------------------------
# 영화관 테마 Custom CSS (클래식 레드 커튼 & 골드 폰트)
# -----------------------------------------------------------------------------
st.markdown("""
<style>
    /* 전체 배경: 고급스러운 붉은 벨벳 커튼 느낌의 그라데이션 */
    .stApp {
        background: linear-gradient(180deg, #4a0404 0%, #2b0000 50%, #120000 100%);
        color: #fce38a;
    }
    
    /* 배경에 커튼 주름 패턴 효과 추가 */
    .stApp::before {
        content: "";
        position: fixed;
        top: 0; left: 0; right: 0; bottom: 0;
        background: repeating-linear-gradient(
            to right,
            transparent,
            transparent 50px,
            rgba(0,0,0,0.15) 50px,
            rgba(0,0,0,0.15) 100px
        );
        pointer-events: none;
        z-index: -1;
    }
    
    /* 제목 및 헤더를 클래식 시네마 스타일로 변경 */
    h1, h2, h3 {
        color: #ffd700 !important;
        font-family: 'Georgia', serif;
        text-shadow: 2px 2px 8px rgba(0,0,0,0.9);
        text-align: center;
    }
    
    /* 지표 카드 디자인 */
    div[data-testid="stMetric"] {
        background: rgba(40, 5, 5, 0.85);
        border: 2px solid #8c1c1c;
        border-radius: 12px;
        padding: 15px;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.7);
    }
    
    /* 데이터프레임/표 스타일 */
    div[data-testid="stDataFrame"] {
        background: rgba(20, 0, 0, 0.8);
        border-radius: 10px;
        border: 1px solid #ffd700;
    }
    
    /* 달력 입력기 다크레드 톤 맞춤 */
    .stDateInput > div {
        background-color: #2b0000 !important;
        color: #ffd700 !important;
        border-radius: 8px;
        border: 1px solid #ffd700;
    }
</style>
""", unsafe_allow_html=True)

st.title("🍿 클래식 시네마 박스오피스")
st.markdown("### 영화진흥위원회(KOBIS) 일별 상영 현황")

# -----------------------------------------------------------------------------
# 1. API 키 검증 (Streamlit Secrets)
# -----------------------------------------------------------------------------
if "KOBIS_KEY" not in st.secrets or not st.secrets["KOBIS_KEY"]:
    st.error("❌ 비밀 금고(secrets)에 'KOBIS_KEY'가 없습니다.")
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
    label="📅 조회할 날짜 선택 (최대 어제까지)",
    value=yesterday_date,
    min_value=min_date,
    max_value=yesterday_date
)

target_date_str = selected_date.strftime("%Y%m%d")
display_date_str = selected_date.strftime("%Y년 %m월 %d일")

st.markdown(f"### 🎟️ **{display_date_str}** 상영 현황")

# -----------------------------------------------------------------------------
# 3. KOBIS API 데이터 호출 함수
# -----------------------------------------------------------------------------
@st.cache_data(ttl=3600)
def fetch_box_office(key: str, target_dt: str):
    url = "[https://www.kobis.or.kr/kobisopenapi/webservice/rest/boxoffice/searchDailyBoxOfficeList.json](https://www.kobis.or.kr/kobisopenapi/webservice/rest/boxoffice/searchDailyBoxOfficeList.json)"
    params = {"key": key, "targetDt": target_dt}
    try:
        res = requests.get(url, params=params, timeout=10)
        res.raise_for_status()
        return res.json()
    except Exception as e:
        return {"error": str(e)}

data = fetch_box_office(api_key, target_date_str)

if "error" in data:
    st.error("❌ 통신 오류가 발생했습니다.")
    st.stop()

# API 인증 오류 방어 코드 추가
if "faultInfo" in data:
    st.error("❌ API 응답 오류가 발생했습니다. (인증키 오류 가능성)")
    st.warning(f"⚠️ 오류 메시지: {data['faultInfo'].get('message', '알 수 없는 오류')}")
    st.stop()

if not data.get("boxOfficeResult", {}).get("dailyBoxOfficeList"):
    st.warning("⚠️ 그날은 아직 집계 전입니다.")
    st.stop()

df = pd.DataFrame(data["boxOfficeResult"]["dailyBoxOfficeList"])
numeric_cols = ["rank", "rankInten", "audiCnt", "audiAcc", "scrnCnt", "showCnt"]
for col in numeric_cols:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)

def format_rank_change(val):
    if val > 0: return f"🔺 {val}"
    elif val < 0: return f"🔹 {abs(val)}"
    return "-"

df["rankChange"] = df["rankInten"].apply(format_rank_change)

# -----------------------------------------------------------------------------
# 4. 1위 영화 지표 출력
# -----------------------------------------------------------------------------
top_movie = df.iloc[0]

st.divider()
st.subheader(f"🥇 1위 영화: {top_movie['movieNm']}")

col1, col2, col3 = st.columns(3)
with col1: st.metric("당일 관객수", f"{top_movie['audiCnt']:,} 명")
with col2: st.metric("누적 관객수", f"{top_movie['audiAcc']:,} 명")
with col3: st.metric("상영 스크린수", f"{top_movie['scrnCnt']:,} 개")

st.divider()

# -----------------------------------------------------------------------------
# 5. 마우스 스크롤(줌) 방지 및 Plotly 기반 그래프 생성
# -----------------------------------------------------------------------------
st.subheader("📊 선택일 상위 5개 영화 관객수 비교 (1위에 마우스를 올려보세요!)")

top_5_df = df.head(5).copy()

# 막대 그래프 (스크롤 불가 설정)
fig_bar = px.bar(top_5_df, x="movieNm", y="audiCnt", text="audiCnt")
fig_bar.update_layout(
    plot_bgcolor="rgba(0,0,0,0)",
    paper_bgcolor="rgba(0,0,0,0)",
    font=dict(color="#fce38a"),
    xaxis_title="영화명",
    yaxis_title="관객수",
)
fig_bar.update_traces(textposition="outside", marker_color="#d62828")
st.plotly_chart(fig_bar, use_container_width=True, config={'scrollZoom': False, 'displayModeBar': False})

st.divider()

st.subheader("📈 상위 5개 영화 최근 7일 관객수 추이")

top_5_titles = df.head(5)["movieNm"].tolist()
past_7_dates = [selected_date - datetime.timedelta(days=i) for i in range(6, -1, -1)]

trend_records = []
for p_date in past_7_dates:
    p_data = fetch_box_office(api_key, p_date.strftime("%Y%m%d"))
    p_df = pd.DataFrame(p_data.get("boxOfficeResult", {}).get("dailyBoxOfficeList", []))
    if not p_df.empty:
        p_df["audiCnt"] = pd.to_numeric(p_df["audiCnt"], errors="coerce").fillna(0).astype(int)
        filtered = p_df[p_df["movieNm"].isin(top_5_titles)]
        for _, row in filtered.iterrows():
            trend_records.append({"날짜": p_date.strftime("%m/%d"), "영화명": row["movieNm"], "관객수": row["audiCnt"]})

if trend_records:
    trend_df = pd.DataFrame(trend_records)
    # 선 그래프 (스크롤 불가 설정)
    fig_line = px.line(trend_df, x="날짜", y="관객수", color="영화명", markers=True)
    fig_line.update_layout(
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#fce38a")
    )
    st.plotly_chart(fig_line, use_container_width=True, config={'scrollZoom': False, 'displayModeBar': False})

st.divider()

# -----------------------------------------------------------------------------
# 6. 표 출력
# -----------------------------------------------------------------------------
st.subheader("📋 전체 순위 목록")

display_cols = ["rank", "rankChange", "movieNm", "openDt", "audiCnt", "audiAcc", "scrnCnt"]
display_df = df[display_cols].copy()
display_df.columns = ["순위", "순위변동", "영화명", "개봉일", "관객수(명)", "누적관객(명)", "스크린수(개)"]

formatted_df = display_df.copy()
for col in ["관객수(명)", "누적관객(명)", "스크린수(개)"]:
    formatted_df[col] = formatted_df[col].map("{:,}".format)

st.dataframe(formatted_df, use_container_width=True, hide_index=True)

# -----------------------------------------------------------------------------
# 7. 1위 영화 마우스 호버 시 사이드 폭죽(트로피) 효과 Javascript 주입
# -----------------------------------------------------------------------------
top_movie_name_json = json.dumps(top_movie["movieNm"])

js_code = f"""
<script>
    const parent = window.parent.document;
    let isAnimating = false;
    
    function checkHover() {{
        if (isAnimating) return;
        const tooltips = parent.querySelectorAll('g.hovertext text');
        let found = false;
        tooltips.forEach(t => {{
            if (t.textContent.includes({top_movie_name_json})) {{
                found = true;
            }}
        }});
        
        if (found) {{
            isAnimating = true;
            showFireworks();
            setTimeout(() => {{ isAnimating = false; }}, 2000); 
        }}
    }}
    
    setInterval(checkHover, 150);
    
    function showFireworks() {{
        const leftTrophy = parent.createElement('div');
        leftTrophy.innerHTML = "🏆";
        leftTrophy.style.position = 'fixed';
        leftTrophy.style.bottom = '-20%';
        leftTrophy.style.left = '-10%';
        leftTrophy.style.fontSize = '15vw';
        leftTrophy.style.zIndex = '999999';
        leftTrophy.style.pointerEvents = 'none';
        leftTrophy.style.animation = 'shootLeftTrophy 1s cubic-bezier(0.25, 1, 0.5, 1) forwards';
        
        const rightTrophy = parent.createElement('div');
        rightTrophy.innerHTML = "🏆";
        rightTrophy.style.position = 'fixed';
        rightTrophy.style.bottom = '-20%';
        rightTrophy.style.right = '-10%';
        rightTrophy.style.fontSize = '15vw';
        rightTrophy.style.zIndex = '999999';
        rightTrophy.style.pointerEvents = 'none';
        rightTrophy.style.animation = 'shootRightTrophy 1s cubic-bezier(0.25, 1, 0.5, 1) forwards';
        
        const style = parent.createElement('style');
        style.innerHTML = `
            @keyframes shootLeftTrophy {{
                0% {{ transform: translate(0, 0) rotate(-45deg) scale(0.5); opacity: 1; }}
                50% {{ transform: translate(35vw, -60vh) rotate(360deg) scale(1.2); opacity: 1; }}
                100% {{ transform: translate(45vw, -70vh) rotate(720deg) scale(1.5); opacity: 0; }}
            }}
            @keyframes shootRightTrophy {{
                0% {{ transform: translate(0, 0) rotate(45deg) scale(0.5); opacity: 1; }}
                50% {{ transform: translate(-35vw, -60vh) rotate(-360deg) scale(1.2); opacity: 1; }}
                100% {{ transform: translate(-45vw, -70vh) rotate(-720deg) scale(1.5); opacity: 0; }}
            }}
        `;
        parent.head.appendChild(style);
        parent.body.appendChild(leftTrophy);
        parent.body.appendChild(rightTrophy);
        
        setTimeout(() => {{
            leftTrophy.remove();
            rightTrophy.remove();
            style.remove();
        }}, 1100);
    }}
</script>
"""
components.html(js_code, height=0, width=0)
