import streamlit as st
import pandas as pd
import datetime
from datetime import date, timedelta
import random
import io
import requests
from bs4 import BeautifulSoup
from gtts import gTTS
from deep_translator import GoogleTranslator

# ==========================================
# 1. 页面配置
# ==========================================
st.set_page_config(
    page_title="Le Menu du Jour - Lite", 
    page_icon="🥐",
    layout="centered",
    initial_sidebar_state="expanded"
)

# ==========================================
# 2. 核心功能函数
# ==========================================

# --- A. 发音功能 ---
@st.cache_data(show_spinner=False)
def get_audio_bytes(text, lang='fr'):
    if not text or text == "Error": return None
    try:
        tts = gTTS(text=text, lang=lang, slow=False)
        fp = io.BytesIO()
        tts.write_to_fp(fp)
        return fp
    except Exception:
        return None

# --- B. 翻译功能 ---
@st.cache_data(show_spinner=False)
def translate_text(text):
    try:
        cn_meaning = GoogleTranslator(source='fr', target='zh-CN').translate(text)
        return cn_meaning
    except Exception:
        return ""

# --- C. 爬虫功能 (只抓词性，不再抓长长的例句) ---
@st.cache_data(show_spinner="正在查询词性...")
def get_wiktionary_pos(word):
    """
    只抓取词性 (Part of Speech)
    """
    word = word.strip().lower()
    url = f"https://fr.wiktionary.org/wiki/{word}"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    pos = "未知"      
    
    try:
        response = requests.get(url, headers=headers, timeout=5)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # 1. 精准抓取性别
            fr_section = soup.find(id="Français")
            if fr_section:
                parent = fr_section.find_parent()
                # 寻找包含性别的行
                gender_line = parent.find_next('span', class_='ligne-de-forme')
                
                if gender_line:
                    text = gender_line.get_text().lower()
                    if 'masculin' in text or ' m' in text:
                        pos = "m. (阳性)"
                    elif 'féminin' in text or ' f' in text:
                        pos = "f. (阴性)"
                
                # 如果没找到，尝试在标题找
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

# --- D. 记忆曲线算法 ---
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

# ==========================================
# 3. 数据加载
# ==========================================
# 虽然我们不显示example了，但为了兼容CSV文件格式，我们还是保留这个列，只是填空
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
# 4. 侧边栏
# ==========================================
with st.sidebar:
    st.title("🇫🇷 Menu Français")
    
    app_mode = st.radio("选择模式", ["🔍 查单词 (Dictionary)", "📖 背单词 (Review)"])
    st.divider()
    
    csv_buffer = st.session_state.df_all.to_csv(index=False, encoding='utf-8').encode('utf-8')
    st.download_button(
        label="📥 下载最新 vocab.csv",
        data=csv_buffer,
        file_name="vocab.csv",
        mime="text/csv",
        type="primary"
    )

# ==========================================
# 5. 查单词模式 (极简版)
# ==========================================
if app_mode == "🔍 查单词 (Dictionary)":
    
    # CSS 优化：让标题更好看
    st.markdown("""
    <style>
        .dict-title {
            font-family: 'Playfair Display', serif;
            font-size: 40px;
            color: #3E2723;
            text-align: center;
            margin-bottom: 30px;
        }
        .dict-meaning {
            font-family: 'Patrick Hand', sans-serif;
            font-size: 24px;
            color: #5D4037;
            text-align: center;
            background-color: #F5F5F5;
            padding: 15px;
            border-radius: 10px;
            margin-top: 10px;
        }
    </style>
    """, unsafe_allow_html=True)

    st.header("🔍 Dictionnaire Lite")
    
    col_search, col_btn = st.columns([4, 1])
    with col_search:
        search_query = st.text_input("输入法语单词:", placeholder="例如: chat").strip()
    
    auto_cn, auto_pos = "", ""

    if search_query:
        # 查重
        match = df[df['word'].str.lower() == search_query.lower()]
        if not match.empty:
            st.success("✅ 单词已存在！")
            exist_word = match.iloc[0]
            # 显示存在的单词卡片
            st.markdown(f"<div class='dict-title'>{exist_word['word']}</div>", unsafe_allow_html=True)
            st.markdown(f"<div style='text-align:center; color:#999; margin-top:-20px; margin-bottom:20px;'>{exist_word['gender']}</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='dict-meaning'>{exist_word['meaning']}</div>", unsafe_allow_html=True)
        else:
            # 联网查询
            with st.spinner("🔍 正在查询..."):
                auto_cn = translate_text(search_query)
                auto_pos = get_wiktionary_pos(search_query)

            if auto_cn:
                # === 优化后的显示界面 ===
                # 不再显示 "FR chat"，直接显示优雅的大字
                st.markdown(f"<div class='dict-title'>{search_query}</div>", unsafe_allow_html=True)
                
                # 发音
                audio = get_audio_bytes(search_query)
                if audio: st.audio(audio, format='audio/mp3')

                # 信息卡片
                st.markdown(f"<div style='text-align:center; color:#78909C; margin-bottom: 10px;'>{auto_pos}</div>", unsafe_allow_html=True)
                st.markdown(f"<div class='dict-meaning'>{auto_cn}</div>", unsafe_allow_html=True)

                st.divider()
                st.caption("📝 确认并保存")
                
                # 极简表单：没有例句了
                with st.form("add_word_form"):
                    col_a, col_b = st.columns([1, 2])
                    with col_a:
                        final_gender = st.text_input("词性", value=auto_pos)
                    with col_b:
                        final_meaning = st.text_input("中文意思", value=auto_cn)
                    
                    # 隐藏的 Word 字段
                    final_word = search_query 
                    
                    if st.form_submit_button("➕ 加入记忆列表", type="primary"):
                        new_row = {
                            'word': final_word,
                            'meaning': final_meaning,
                            'gender': final_gender,
                            'example': "", # 留空
                            'last_review': None,
                            'next_review': date.today().isoformat(),
                            'interval': 0
                        }
                        st.session_state.df_all = pd.concat([st.session_state.df_all, pd.DataFrame([new_row])], ignore_index=True)
                        st.toast(f"已保存: {final_word}", icon="🎉")
                        st.cache_data.clear()
            else:
                st.error("查询失败 (可能是网络原因)，请稍后再试。")

# ==========================================
# 6. 背单词模式 (无例句版)
# ==========================================
elif app_mode == "📖 背单词 (Review)":
    
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
        st.balloons()
        st.markdown("""
        <div style="text-align:center; padding: 50px;">
            <h1>🎉 Félicitations!</h1>
            <p>今日任务已完成！</p>
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
        
        # 样式优化：去掉了例句的CSS
        st.markdown("""
        <style>
            .flash-card {
                background-color: white; padding: 40px; border-radius: 12px;
                border: 1px solid #e0e0e0; box-shadow: 0 4px 12px rgba(0,0,0,0.05);
                text-align: center; margin-bottom: 20px;
            }
            .word-title { font-size: 52px; color: #2c3e50; font-family: 'Playfair Display', serif; margin-bottom: 10px; }
            .word-meaning { font-size: 28px; color: #e67e22; font-family: 'Patrick Hand', sans-serif; }
            .word-meta { color: #95a5a6; font-size: 20px; font-family: 'Patrick Hand', sans-serif;}
        </style>
        """, unsafe_allow_html=True)

        audio_bytes = get_audio_bytes(current_word_data['word'])
        if audio_bytes:
            st.audio(audio_bytes, format='audio/mp3', autoplay=True)

        if not st.session_state.show_back:
            # 正面
            st.markdown(f"""
            <div class="flash-card">
                <div style="color:#ccc; margin-bottom:10px;">点击下方按钮翻牌</div>
                <div class="word-title">{current_word_data['word']}</div>
                <br>
            </div>
            """, unsafe_allow_html=True)
            if st.button("🔍 查看答案", use_container_width=True):
                st.session_state.show_back = True
                st.rerun()
        else:
            # 背面：去掉了例句部分，只保留单词、词性和意思
            st.markdown(f"""
            <div class="flash-card">
                <div class="word-title">{current_word_data['word']}</div>
                <div class="word-meta">{current_word_data.get('gender', '')}</div>
                <hr style="opacity:0.2; margin: 20px 0;">
                <div class="word-meaning">“ {current_word_data['meaning']} ”</div>
            </div>
            """, unsafe_allow_html=True)
            
            c1, c2 = st.columns(2)
            with c1:
                if st.button("✅ 认识", use_container_width=True, type="primary"):
                    st.session_state.df_all.loc[cur_idx] = update_word_progress(current_word_data.copy(), 1)
                    st.session_state.study_queue.pop(0)
                    st.session_state.show_back = False
                    st.rerun()
            with c2:
                if st.button("❌ 模糊", use_container_width=True):
                    st.session_state.df_all.loc[cur_idx] = update_word_progress(current_word_data.copy(), 0)
                    st.session_state.study_queue.pop(0)
                    st.session_state.show_back = False
                    st.rerun()

st.markdown("<br><div style='text-align:center; color:#ddd;'>Powered by Python</div>", unsafe_allow_html=True)
