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

st.title("🍿 클래식 시네마 박
