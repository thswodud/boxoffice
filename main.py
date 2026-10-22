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
# ------------------------------------------------
