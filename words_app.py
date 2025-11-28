import streamlit as st
import pandas as pd
import datetime
from datetime import date, timedelta
import random
import io
import base64
import requests
from bs4 import BeautifulSoup
from gtts import gTTS
from deep_translator import GoogleTranslator

# ==========================================
# 1. 页面配置
# ==========================================
st.set_page_config(
    page_title="Le Menu du Jour", 
    page_icon="🥘",
    layout="centered",
    initial_sidebar_state="expanded"
)

# ==========================================
# 2. 🎨 UI/UX 设计 (Ratatouille & Ernest Style)
# ==========================================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,600;1,600&family=Patrick+Hand&display=swap');

    /* 全局背景 */
    .stApp {
        background-color: #F9F7F1; 
        background-image: radial-gradient(#F9F7F1 20%, #EFEBE0 100%);
    }

    section[data-testid="stSidebar"] {
        background-color: #F4F0E6;
        border-right: 1px dashed #D7CCC8;
    }

    h1, h2, h3 {
        font-family: 'Playfair Display', serif !important;
        color: #3E2723 !important;
    }

    /* ============================================================
       🛑 1. 输入框深度修复 (Targeting BaseWeb)
       ============================================================ */
    
    /* 隐藏 Label */
    div[data-testid="stTextInput"] label { display: none; }

    /* 锁定输入框的最底层容器 */
    div[data-baseweb="input"] {
        background-color: #FFFEFA !important;
        border: 2px solid #E0D6CC !important; 
        border-radius: 50px !important;
        box-shadow: 0 4px 10px rgba(93, 64, 55, 0.05) !important; 
        padding: 5px 10px !important; /* 调整内边距 */
    }

    /* 锁定：鼠标点击/输入时的状态 (Focus) */
    div[data-baseweb="input"]:focus-within {
        border-color: #C65D3B !important; /* 强制铜锅色 */
        background-color: #FFF !important;
        box-shadow: 0 0 0 3px rgba(198, 93, 59, 0.15) !important; /* 柔和铜色光晕，覆盖默认红框 */
    }

    /* 输入文字的样式 */
    input[type="text"] {
        color: #5D4037 !important;
        font-family: 'Patrick Hand', cursive !important;
        font-size: 24px !important;
        text-align: center !important;
        caret-color: #C65D3B !important; /* 光标颜色也改成铜色 */
    }

    /* ============================================================
       🐭 2. 小老鼠按钮：完全透明化
       ============================================================ */
    
    /* 针对放在列(column)里的小老鼠按钮进行覆盖 */
    div[data-testid="column"] button {
        background-color: transparent !important;
        border: none !important;
        box-shadow: none !important;
        text-shadow: none !important;
        padding: 0px !important;
        font-size: 36px !important; /* 图标大一点 */
        line-height: 1 !important;
    }

    /* 悬停、点击、聚焦状态全部去除背景 */
    div[data-testid="column"] button:hover,
    div[data-testid="column"] button:active,
    div[data-testid="column"] button:focus {
        background-color: transparent !important;
        border: none !important;
        box-shadow: none !important;
        color: inherit !important;
        transform: scale(1.1) rotate(10deg) !important; /* 只保留动效 */
    }

    /* ============================================================
       📋 3. 卡片容器
       ============================================================ */
    .menu-card {
        background-color: #FFFEFA;
        padding: 50px 30px 40px 30px;
        margin-top: -35px; /* 负边距，让小老鼠趴在框上 */
        margin-bottom: 30px;
        border-radius: 12px;
        border: 1px solid #E0D6CC; 
        box-shadow: 0 8px 20px rgba(93, 64, 55, 0.06); 
        text-align: center;
        position: relative;
        z-index: 1; 
    }

    .menu-divider { border-top: 3px double #C65D3B; width: 80px; margin: 20px auto; opacity: 0.6; }
    .french-word { font-family: 'Playfair Display', serif; font-size: 60px; font-weight: 600; color: #C65D3B; margin-bottom: 5px; letter-spacing: 1px; line-height: 1.1; }
    .word-meta { font-family: 'Patrick Hand', cursive; font-size: 24px; color: #78909C; font-style: italic; margin-bottom: 20px;}
    .word-meaning { font-family: 'Patrick Hand', cursive; font-size: 30px; color: #5D4037; display: inline-block; padding: 10px 25px; border-radius: 10px; background-color: #F9F7F1; }

    /* 通用操作按钮 (底部按钮) */
    div.stButton > button { 
        border-radius: 30px; 
        font-family: 'Playfair Display', serif; 
        border: 1px solid #D7CCC8;
    }
    /* 排除掉小老鼠按钮，只给下面的按钮加背景动效 */
    div.stButton > button:not(:has(div[data-testid="column"])):hover {
        background-color: #F2EFE9;
    }
    
    div.stButton > button[kind="primary"] {
        border-color: #C65D3B;
        color: #C65D3B;
        background-color: transparent;
    }
    div.stButton > button[kind="primary"]:hover {
        background-color: #C65D3B;
        color: white;
    }

</style>
""", unsafe_allow_html=True)

# ==========================================
# 3. 核心功能函数
# ==========================================

def play_audio_hidden(text, lang='fr'):
    if not text: return
    try:
        tts = gTTS(text=text, lang=lang, slow=False)
        fp = io.BytesIO()
        tts.write_to_fp(fp)
        b64 = base64.b64encode(fp.getvalue()).decode()
        md = f"""
            <audio autoplay style="display:none;">
            <source src="data:audio/mp3;base64,{b64}" type="audio/mp3">
            </audio>
            """
        st.markdown(md, unsafe_allow_html=True)
    except Exception:
        pass

@st.cache_data(show_spinner=False)
def translate_text(text):
    try:
        cn_meaning = GoogleTranslator(source='fr', targe
