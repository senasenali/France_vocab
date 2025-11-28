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
    /* 引入字体 */
    @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,600;1,600&family=Patrick+Hand&display=swap');

    /* --- 全局背景 --- */
    .stApp {
        background-color: #F9F7F1; 
        background-image: radial-gradient(#F9F7F1 20%, #EFEBE0 100%);
    }

    /* --- 侧边栏 --- */
    section[data-testid="stSidebar"] {
        background-color: #F4F0E6;
        border-right: 1px dashed #D7CCC8;
    }

    /* --- 标题样式 --- */
    h1, h2, h3 {
        font-family: 'Playfair Display', serif !important;
        color: #3E2723 !important;
    }

    /* -------------------------------------------
       1. 搜索框美化 (彻底修复红色边框)
       ------------------------------------------- */
    div[data-testid="stTextInput"] label { display: none; } /* 隐藏Label */
    
    div[data-testid="stTextInput"] input {
        background-color: #FFFEFA; 
        border: 2px solid #E0D6CC !important; /* 强制覆盖默认边框 */
        border-radius: 50px;       
        padding: 15px 25px;        
        color: #5D4037;            
        font-family: 'Patrick Hand', cursive;
        font-size: 22px;           
        text-align: center;        
        box-shadow: 0 4px 10px rgba(93, 64, 55, 0.05); 
        transition: 0.3s all;
        outline: none !important; /* 去掉默认轮廓 */
    }
    
    /* 鼠标点进去时的样式：变成铜锅色，而不是默认的红色 */
    div[data-testid="stTextInput"] input:focus {
        border-color: #C65D3B !important; 
        box-shadow: 0 0 0 2px rgba(198, 93, 59, 0.2) !important; /* 柔和的铜色光晕 */
    }

    /* -------------------------------------------
       2. 小老鼠音频按钮 (左上角悬浮)
       ------------------------------------------- */
    /* 这是一个特殊的 CSS Hack，用来定位那个小老鼠按钮 */
    .mouse-audio-btn {
        border: none !important;
        background: transparent !important;
        font-size: 30px !important; /* 图标放大 */
        padding: 0 !important;
        margin-bottom: -60px !important; /* 关键：负边距，让它沉入下面的卡片里 */
        margin-left: 10px !important;
        position: relative;
        z-index: 999; /* 保证在最上层 */
        cursor: pointer;
        transition: transform 0.2s;
    }
    
    .mouse-audio-btn:hover {
        transform: scale(1.2) rotate(-10deg); /* 悬停时小老鼠动一下 */
        background: transparent !important; /* 保持透明 */
        color: inherit !important;
        border: none !important;
        box-shadow: none !important;
    }
    
    /* 消除 Streamlit 默认按钮的边框和背景 */
    div.stButton > button:first-child {
        /* 注意：这里会影响页面上第一个按钮，所以我们要小心布局 */
    }

    /* -------------------------------------------
       3. 卡片容器
       ------------------------------------------- */
    .menu-card {
        background-color: #FFFEFA;
        padding: 50px 30px 40px 30px; /* 顶部留多一点空间给单词 */
        margin-top: 10px; 
        margin-bottom: 30px;
        border-radius: 12px;
        border: 1px solid #E0D6CC; 
        box-shadow: 0 8px 20px rgba(93, 64, 55, 0.06); 
        text-align: center;
        position: relative;
    }

    .menu-divider { border-top: 3px double #C65D3B; width: 80px; margin: 20px auto; opacity: 0.6; }
    .french-word { font-family: 'Playfair Display', serif; font-size: 60px; font-weight: 600; color: #C65D3B; margin-bottom: 5px; letter-spacing: 1px; line-height: 1.1; }
    .word-meta { font-family: 'Patrick Hand', cursive; font-size: 24px; color: #78909C; font-style: italic; margin-bottom: 20px;}
    .word-meaning { font-family: 'Patrick Hand', cursive; font-size: 30px; color: #5D4037; display: inline-block; padding: 10px 25px; border-radius: 10px; background-color: #F9F7F1; }

    /* 通用按钮样式 (用于添加、背单词等) */
    div.stButton > button { 
        border-radius: 30px; 
        font-family: 'Playfair Display', serif; 
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
        cn_meaning = GoogleTranslator(source='fr', target='zh-CN').translate(text)
        return cn_meaning
    except Exception:
        return ""

@st.cache_data(show_spinner="正在查阅主厨的食谱 (Wiktionary)...")
def get_wiktionary_pos(word):
    word = word.strip().lower()
    url = f"https://fr.wiktionary.org/wiki/{word}"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
    pos = "未知"      
    try:
        response = requests.get(url, headers=headers, timeout=5)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            fr_section = soup.find(id="Français")
            if fr_section:
                parent = fr_section.find_parent()
                gender_line = parent.find_next('span', class_='ligne-de-forme')
                if gender_line:
                    text = gender_line.get_text().lower()
                    if 'masculin' in text or ' m' in text: pos = "m. (阳性)"
                    elif 'féminin' in text or ' f' in text: pos = "f. (阴性)"
                
                if pos == "未知":
                    all_pos_headers = soup.find_all('span', class_='titredef')
                    for header in all_pos_headers:
                        if 'nom' in header.get_text().lower():
                            next_line = header.find_next('p')
                            if next_line:
                                txt = next_line.get_text().lower()
                                if 'masculin' in txt: 
                                    pos = "m. (阳性)"
                                    break
                                elif 'féminin' in txt: 
                                    pos = "f. (阴性)"
                                    break
                            pos = "n. (名词)"
                        elif 'verbe' in header.get_text().lower():
                            pos = "v. (动词)"
                            break
                        elif 'adjectif' in header.get_text().lower():
                            pos = "adj. (形容词)"
                            break
        return pos
    except Exception:
        return "未知"

def update_word_progress(word_row, quality):
    today = date.today()
    current_interval = int(word_row.get('interval', 0))
    if quality == 0:
        new_interval = 1
    else:
        new_interval = 1 if current_interval == 0 else int(current_interval * 2.2)
    word_row['last_review'] = today.isoformat()
    word_row['next_review'] = (today + timedelta(days=new_interval)).isoformat()
    word_row['interval'] = new_interval
    return word_row

REQUIRED_COLS = ['word', 'meaning', 'gender', 'example'] 
SRS_COLS = ['last_review', 'next_review', 'interval']

def load_data():
    try:
        df = pd.read_csv("vocab.csv", encoding='utf-8', keep_default_na=False, quotechar='"')
        df.columns = df.columns.str.strip()
        for col in SRS_COLS:
            if col not in df.columns:
                df[col] = None if col == 'last_review' else 0
        if 'next_review' in df.columns:
            df['next_review'] = pd.to_datetime(df['next_review'], errors='coerce')
            df['next_review'] = df['next_review'].dt.strftime('%Y-%m-%d')
            df['next_review'] = df['next_review'].fillna(date.today().isoformat())
        return df
    except Exception:
        return pd.DataFrame(columns=REQUIRED_COLS + SRS_COLS)

if 'df_all' not in st.session_state:
    st.session_state.df_all = load_data()

df = st.session_state.df_all

# ==========================================
# 5. 侧边栏
# ==========================================
with st.sidebar:
    st.markdown("<h1 style='font-size:24px; color:#5D4037;'>🧑‍🍳 Chef's Kitchen</h1>", unsafe_allow_html=True)
    app_mode = st.radio("选择模式", ["🔍 查单词 (Dictionary)", "📖 背单词 (Review)"])
    st.divider()
    csv_buffer = st.session_state.df_all.to_csv(index=False, encoding='utf-8').encode('utf-8')
    st.download_button(
        label="📥 打包带走 (下载 CSV)",
        data=csv_buffer,
        file_name="vocab.csv",
        mime="text/csv",
        type="primary"
    )

# ==========================================
# 6. 查单词模式
# ==========================================
if app_mode == "🔍 查单词 (Dictionary)":
    
    st.markdown("<h1 style='text-align:center;'>Le Dictionnaire</h1>", unsafe_allow_html=True)
    
    search_query = st.text_input("", placeholder="在此输入法语单词...", label_visibility="collapsed").strip()
    
    auto_cn, auto_pos = "", ""

    if search_query:
        # 默认自动播放一次
        play_audio_hidden(search_query)

        match = df[df['word'].str.lower() == search_query.lower()]
        
        # 准备显示的数据
        if not match.empty:
            exist_word = match.iloc[0]
            display_word = exist_word['word']
            display_pos = exist_word['gender']
            display_meaning = exist_word['meaning']
            is_new = False
        else:
            with st.spinner("🍳 正在烹饪中..."):
                auto_cn = translate_text(search_query)
                auto_pos = get_wiktionary_pos(search_query)
            display_word = search_query
            display_pos = auto_pos
            display_meaning = auto_cn
            is_new = True

        if display_meaning:
            # === 小老鼠按钮逻辑 ===
            # 我们用 CSS (mouse-audio-btn) 把这个按钮定位到卡片左上角
            # 这里的 columns 只是为了布局占位，重要的是按钮本身
            col_audio, col_empty = st.columns([1, 10])
            with col_audio:
                # 这是一个“透明”按钮，点击后页面刷新，触发上面的 play_audio_hidden
                # 按钮文字是小老鼠
                st.markdown("""
                <style>
                /* 只针对这个小老鼠按钮的特殊样式覆盖 */
                div.row-widget.stButton > button {
                    background-color: transparent !important;
                    border: none !important;
                    font-size: 28px !important;
                    padding: 0px !important;
                }
                div.row-widget.stButton > button:hover {
                    transform: scale(1.2);
                    box-shadow: none !important;
                }
                </style>
                """, unsafe_allow_html=True)
                
                if st.button("🐁", key="replay_btn", help="点击小老鼠重听"):
                    pass # 刷新页面重新播放
            
            # === 卡片展示 (通过 CSS 这里的 margin-top 把它拉上来) ===
            # 注意：CSS中 .menu-card 的 margin-top 稍微调整，配合上面的按钮
            st.markdown(f"""
            <div class="menu-card" style="margin-top: -20px;">
                <div class="french-word">{display_word}</div>
                <div class="word-meta">{display_pos}</div>
                <div class="word-meaning">{display_meaning}</div>
            </div>
            """, unsafe_allow_html=True)

            # 如果是新词，显示添加表单
            if is_new:
                st.caption("📝 加入今日菜单")
                with st.form("add_word_form"):
                    col_a, col_b = st.columns([1, 2])
                    with col_a:
                        final_gender = st.text_input("词性", value=display_pos)
                    with col_b:
                        final_meaning = st.text_input("中文意思", value=display_meaning)
                    
                    final_word = search_query 
                    
                    if st.form_submit_button("🍽️ 上菜
