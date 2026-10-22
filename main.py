import datetime
import json
import requests
import pandas as pd
import pytz
import streamlit as st
import altair as alt
import streamlit.components.v1 as components

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
    
    /* 제목 및 주요 헤더 골드 톤 강조 */
    h1, h2, h3 {{
        color: #fce38a !important;
        font-family: 'Pretendard', sans-serif;
        text-shadow: 3px 3px 6px rgba(0,0,0,0.9);
    }}
    
    /* 카드 / 지표 반투명 오버레이 패널 */
    div[data-testid="stMetric"] {{
        background: rgba(20, 10, 15, 0.75);
        border: 1px solid rgba(252, 227, 138, 0.3);
        border-radius: 12px;
        padding: 15px;
        box-shadow: 0 8px 20px rgba(0, 0, 0, 0.7);
        backdrop-filter: blur(5px);
    }}
    
    /* 데이터프레임 표 스타일 */
    div[data-testid="stDataFrame"] {{
        background: rgba(15, 8, 12, 0.75);
        border-radius: 10px;
        border: 1px solid rgba(252, 227, 138, 0.2);
        backdrop-filter: blur(5px);
    }}
    
    /* 날짜 선택 위젯 커스텀 */
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
# 3. KOBIS API 데이터 호출 함수
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
    if val > 0:
        return f"🔺 {val}"
    elif val < 0:
        return f"🔹 {abs(val)}"
    else:
        return "-"

df["rankChange"] = df["rankInten"].apply(format_rank_change)

# -----------------------------------------------------------------------------
# 5. 1위 영화 핵심 지표 카드 (Metrics Cards)
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
# 6. Top 5 영화의 최근 7일간 일별 관객수 추이 선 그래프 (마우스 스크롤 고정 적용)
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
    
    # Altair를 사용하여 스크롤 시 줌(Zoom) 기능이 비활성화된 차트 생성
    line_chart = alt.Chart(trend_df).mark_line(point=True).encode(
        x=alt.X('날짜', sort=None, title='날짜'),
        y=alt.Y('관객수', title='관객수 (명)'),
        color=alt.Color('영화명', legend=alt.Legend(title="영화명", orient="bottom")),
        tooltip=['날짜', '영화명', '관객수']
    ).properties(height=400)
    
    st.altair_chart(line_chart, use_container_width=True)

st.divider()

# -----------------------------------------------------------------------------
# 7. 관객수 상위 5편 막대그래프 (가장 높은 막대 호버 시 트로피 이펙트 적용)
# -----------------------------------------------------------------------------
st.subheader("📊 선택일 상위 5개 영화 관객수 비교")

top_5_df = df.head(5).copy()

# HTML 컴포넌트에 전달할 데이터를 JSON 문자열로 변환
labels_json = json.dumps(top_5_df["movieNm"].tolist())
data_json = json.dumps(top_5_df["audiCnt"].tolist())

# Chart.js를 이용해 스크롤 고정 및 호버 이벤트를 감지하는 커스텀 막대그래프 렌더링
html_code = f"""
<!DOCTYPE html>
<html>
<head>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body {{ margin: 0; background: transparent; font-family: sans-serif; }}
        .chart-container {{ position: relative; height: 400px; width: 100%; }}
    </style>
</head>
<body>
    <div class="chart-container">
        <canvas id="barChart"></canvas>
    </div>
    <script>
        // 메인 Streamlit 윈도우에 전체 화면 트로피 오버레이 생성
        let overlay;
        try {{
            overlay = window.parent.document.getElementById('global-trophy-overlay');
            if (!overlay) {{
                overlay = window.parent.document.createElement('div');
                overlay.id = 'global-trophy-overlay';
                overlay.innerHTML = '🏆';
                Object.assign(overlay.style, {{
                    position: 'fixed', top: '0', left: '0', width: '100vw', height: '100vh',
                    backgroundColor: 'rgba(0,0,0,0.85)', color: 'gold', fontSize: '200px',
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    zIndex: '999999', opacity: '0', pointerEvents: 'none', transition: 'opacity 0.3s ease'
                }});
                window.parent.document.body.appendChild(overlay);
            }}
        }} catch (e) {{
            console.log("부모 창 접근 권한이 없습니다.");
        }}

        const ctx = document.getElementById('barChart').getContext('2d');
        let trophyTimeout = null;

        new Chart(ctx, {{
            type: 'bar',
            data: {{
                labels: {labels_json},
                datasets: [{{
                    label: '관객수',
                    data: {data_json},
                    backgroundColor: 'rgba(252, 227, 138, 0.7)',
                    borderColor: 'rgba(252, 227, 138, 1)',
                    borderWidth: 1,
                    borderRadius: 4
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{
                    legend: {{ display: false }},
                    tooltip: {{
                        callbacks: {{
                            label: function(context) {{
                                return context.raw.toLocaleString() + ' 명';
                            }}
                        }}
                    }}
                }},
                scales: {{
                    y: {{
                        beginAtZero: true,
                        grid: {{ color: 'rgba(255, 255, 255, 0.1)' }},
                        ticks: {{ color: '#f1e4e6' }}
                    }},
                    x: {{
                        grid: {{ display: false }},
                        ticks: {{ color: '#f1e4e6' }}
                    }}
                }},
                // 마우스 호버 이벤트 감지
                onHover: (event, elements) => {{
                    if (elements.length > 0) {{
                        // 첫 번째 요소(가장 높은 1위 막대)인지 확인
                        const index = elements[0].index;
                        if (index === 0 && overlay && overlay.style.opacity === '0') {{
                            overlay.style.opacity = '1';
                            clearTimeout(trophyTimeout);
                            trophyTimeout = setTimeout(() => {{
                                overlay.style.opacity = '0';
                            }}, 2000);
                        }}
                    }}
                }}
            }}
        }});
    </script>
</body>
</html>
"""
components.html(html_code, height=450)

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
