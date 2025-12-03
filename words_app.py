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
       🛑 1. 输入框终极修复 (透明化内层，去红框)
       ============================================================ */
    
    div[data-testid="stTextInput"] label { display: none; }

    /* 外层容器 */
    div[data-baseweb="input"] {
        background-color: #FFFEFA !important; 
        border: 2px solid #E0D6CC !important; 
        border-radius: 50px !important;
        box-shadow: 0 4px 10px rgba(93, 64, 55, 0.05) !important; 
        padding: 8px 15px !important;
    }

    div[data-baseweb="input"]:focus-within {
        border-color: #C65D3B !important; 
        background-color: #FFFEFA !important; 
        box-shadow: 0 0 0 3px rgba(198, 93, 59, 0.15) !important; 
    }

    /* 内层容器透明化 (关键！) */
    div[data-baseweb="base-input"] {
        background-color: transparent !important;
    }
    
    input[type="text"] {
        background-color: transparent !important;
        color: #5D4037 !important;
        font-family: 'Patrick Hand', cursive !important;
        font-size: 24px !important;
        text-align: center !important;
        caret-color: #C65D3B !important;
    }

    /* ============================================================
       📋 2. 分体式卡片设计 (Split Card)
       ============================================================ */
    
    /* 上半部分：单词 + 词性 */
    .menu-card-top {
        background-color: #FFFEFA;
        padding: 40px 30px 10px 30px; /* 底部padding减小 */
        margin-top: 20px;
        border: 1px solid #E0D6CC; 
        border-bottom: none; /* 去掉底边框 */
        border-radius: 12px 12px 0 0; /* 只圆上面两个角 */
        text-align: center;
        position: relative;
    }

    /* 下半部分：中文意思 */
    .menu-card-bottom {
        background-color: #FFFEFA;
        padding: 10px 30px 40px 30px; /* 顶部padding减小 */
        margin-bottom: 30px;
        border: 1px solid #E0D6CC; 
        border-top: none; /* 去掉顶边框 */
        border-radius: 0 0 12px 12px; /* 只圆下面两个角 */
        box-shadow: 0 8px 20px rgba(93, 64, 55, 0.06); /* 阴影只加在下半部分 */
        text-align: center;
        position: relative;
    }

    /* 字体样式 */
    .french-word { font-family: 'Playfair Display', serif; font-size: 64px; font-weight: 600; color: #C65D3B; margin-bottom: 5px; letter-spacing: 1px; line-height: 1.1; }
    .word-meta { font-family: 'Patrick Hand', cursive; font-size: 24px; color: #78909C; font-style: italic; }
    .word-meaning { font-family: 'Patrick Hand', cursive; font-size: 32px; color: #5D4037; display: inline-block; padding: 15px 30px; border-radius: 12px; background-color: #F9F7F1; }

    /* ============================================================
       🔊 3. 发音按钮样式 (夹在中间)
       ============================================================ */
    
    /* 针对中间那个按钮的特殊样式 */
    div.row-widget.stButton > button {
        border-radius: 20px !important;
        border: 1px solid #E0D6CC !important;
        background-color: #FFFEFA !important; /* 跟卡片同色 */
        color: #8D6E63 !important;
        font-family: 'Patrick Hand', cursive !important;
        font-size: 18px !important;
        padding: 5px 20px !important;
        margin-top: -10px !important;    /* 稍微调整位置 */
        margin-bottom: -10px !important;
        z-index: 10 !important;
    }
    
    div.row-widget.stButton > button:hover {
        border-color: #C65D3B !important;
        color: #C65D3B !important;
        background-color: #FFF !important;
    }

    /* 底部通用按钮 (添加/记住了) */
    div.stButton > button[kind="primary"] {
        border-color: #C65D3B !important;
        color: #C65D3B !important;
        background-color: transparent !important;
        border-radius: 30px !important;
    }
    div.stButton > button[kind="primary"]:hover {
        background-color: #C65D3B !important;
        color: white !important;
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
    app_mode = st.radio("选择模式", ["🔍 Dictionary", "📖 Review"])
    st.divider()
    csv_buffer = st.session_state.df_all.to_csv(index=False, encoding='utf-8').encode('utf-8')
    st.download_button(
        label="📥 take away",
        data=csv_buffer,
        file_name="vocab.csv",
        mime="text/csv",
        type="primary"
    )

# ==========================================
# 6. 查单词模式
# ==========================================
if app_mode == "🔍 Dictionary":
    
    st.markdown("<h1 style='text-align:center;'>Le Dictionnaire</h1>", unsafe_allow_html=True)
    
    # 🌟 修改点：placeholder 为空，去除了提示语
    search_query = st.text_input("", placeholder="", label_visibility="collapsed").strip()
    
    auto_cn, auto_pos = "", ""

    if search_query:
        # 自动播放一次
        play_audio_hidden(search_query)

        match = df[df['word'].str.lower() == search_query.lower()]
        
        # 准备显示数据
        if not match.empty:
            exist_word = match.iloc[0]
            display_word = exist_word['word']
            display_pos = exist_word['gender']
            display_meaning = exist_word['meaning']
            is_new = False
        else:
            with st.spinner("🍳 cooking..."):
                auto_cn = translate_text(search_query)
                auto_pos = get_wiktionary_pos(search_query)
            display_word = search_query
            display_pos = auto_pos
            display_meaning = auto_cn
            is_new = True

        if display_meaning:
            # === 卡片展示逻辑 (三明治结构) ===
            
            # 1. 上层面包：单词 + 词性
            st.markdown(f"""
            <div class="menu-card-top">
                <div class="french-word">{display_word}</div>
                <div class="word-meta">{display_pos}</div>
            </div>
            """, unsafe_allow_html=True)

            # 2. 中间夹心：发音按钮 (居中)
            col1, col2, col3 = st.columns([1, 1, 1])
            with col2:
                if st.button("🔊 Pronunciation", use_container_width=True):
                    pass # 刷新页面重听

            # 3. 下层面包：中文意思
            st.markdown(f"""
            <div class="menu-card-bottom">
                <div class="word-meaning">{display_meaning}</div>
            </div>
            """, unsafe_allow_html=True)

            if is_new:
                st.caption("📝 add to menu")
                with st.form("add_word_form"):
                    col_a, col_b = st.columns([1, 2])
                    with col_a:
                        final_gender = st.text_input("词性", value=display_pos)
                    with col_b:
                        final_meaning = st.text_input("中文意思", value=display_meaning)
                    
                    final_word = search_query 
                    
                    if st.form_submit_button("🍽️ Ajouter", type="primary"):
                        new_row = {
                            'word': final_word,
                            'meaning': final_meaning,
                            'gender': final_gender,
                            'example': "", 
                            'last_review': None,
                            'next_review': date.today().isoformat(),
                            'interval': 0
                        }
                        st.session_state.df_all = pd.concat([st.session_state.df_all, pd.DataFrame([new_row])], ignore_index=True)
                        st.balloons()
                        st.toast(f"Bon appétit! {final_word} 已加入。", icon="🍷")
                        st.cache_data.clear()
            else:
                st.success("✅ already in the menu！")

        else:
             st.error("sorry.. we failed")
    
    else:
        st.markdown("<br><br><p style='text-align:center; color:#BCAAA4; font-family:Patrick Hand;'>Bon appétit !</p>", unsafe_allow_html=True)

# ==========================================
# 7. 背单词模式
# ==========================================
elif app_mode == "📖 Review":
    
    if 'study_queue' not in st.session_state:
        today_str = date.today().isoformat()
        mask = (st.session_state.df_all['next_review'] <= today_str) | (st.session_state.df_all['next_review'].isna())
        due_df = st.session_state.df_all[mask]
        
        if len(due_df) > 50:
            study_df = due_df.sample(50)
        else:
            study_df = due_df
            
        st.session_state.study_queue = study_df.index.tolist()
        random.shuffle(st.session_state.study_queue)
        st.session_state.show_back = False

    if not st.session_state.study_queue:
        st.markdown("""
        <div style="text-align:center; padding: 50px;">
            <div style="font-size: 60px;">🍷</div>
            <h1 style="color:#C65D3B;">C'est fini!</h1>
            <p style="font-family:'Patrick Hand'; font-size:20px; color:#5D4037;">今日的品鉴课程已结束。</p>
        </div>
        """, unsafe_allow_html=True)
    else:
        cur_idx = st.session_state.study_queue[0]
        if cur_idx not in st.session_state.df_all.index:
            st.session_state.study_queue.pop(0)
            st.rerun()
            
        current_word_data = st.session_state.df_all.loc[cur_idx]
        progress = 1.0 - (len(st.session_state.study_queue) / 50.0)
        st.progress(max(0.0, min(1.0, progress)))
        
        play_audio_hidden(current_word_data['word'])

        if not st.session_state.show_back:
            st.markdown(f"""
            <div class="menu-card-top" style="border-radius:12px; border-bottom:1px solid #E0D6CC;">
                <div style="color:#BCAAA4; font-family:'Patrick Hand'; margin-bottom:10px;">Plat du Jour</div>
                <div class="french-word">{current_word_data['word']}</div>
                <div style="margin-top:30px; color:#D7CCC8;">(点击下方按钮揭晓)</div>
            </div>
            """, unsafe_allow_html=True)
            
            # 这里的按钮稍微调整，为了美观
            col1, col2, col3 = st.columns([1,1,1])
            with col2:
                if st.button("🔊 Pronunciation", key="review_audio", use_container_width=True):
                    pass

            if st.button("🔍 Voir", use_container_width=True):
                st.session_state.show_back = True
                st.rerun()
        else:
            # === 背面卡片 (三明治结构) ===
            st.markdown(f"""
            <div class="menu-card-top">
                <div class="french-word">{current_word_data['word']}</div>
                <div class="word-meta">{current_word_data.get('gender', '')}</div>
            </div>
            """, unsafe_allow_html=True)

            col1, col2, col3 = st.columns([1,1,1])
            with col2:
                if st.button("🔊 Pronunciation", key="review_audio_back", use_container_width=True):
                    pass

            st.markdown(f"""
            <div class="menu-card-bottom">
                <div class="word-meaning">{current_word_data['meaning']}</div>
            </div>
            """, unsafe_allow_html=True)

            c1, c2 = st.columns(2)
            with c1:
                if st.button("🍷 Délicieux!", use_container_width=True, type="primary"):
                    st.session_state.df_all.loc[cur_idx] = update_word_progress(current_word_data.copy(), 1)
                    st.session_state.study_queue.pop(0)
                    st.session_state.show_back = False
                    st.rerun()
            with c2:
                if st.button("🧂 Trop Salé...", use_container_width=True):
                    st.session_state.df_all.loc[cur_idx] = update_word_progress(current_word_data.copy(), 0)
                    st.session_state.study_queue.pop(0)
                    st.session_state.show_back = False
                    st.rerun()

st.markdown("<br><div style='text-align:center; color:#D7CCC8; font-family:Patrick Hand;'>Fait avec amour par Python</div>", unsafe_allow_html=True)
