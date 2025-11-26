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
    page_title="Le Menu du Jour - Pro", 
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

# --- B. 翻译功能 (获取中文意思) ---
@st.cache_data(show_spinner=False)
def translate_text(text):
    try:
        cn_meaning = GoogleTranslator(source='fr', target='zh-CN').translate(text)
        en_meaning = GoogleTranslator(source='fr', target='en').translate(text)
        return cn_meaning, en_meaning
    except Exception:
        return "", ""

# --- C. 爬虫功能 (获取词性和例句) ---
# 这是一个高级功能，去爬取 Larousse 词典的网页
@st.cache_data(show_spinner="正在查阅 Larousse 词典...")
def get_larousse_details(word):
    url = f"https://www.larousse.fr/dictionnaires/francais/{word.strip().lower()}"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
    
    pos = ""      # 词性
    example = ""  # 例句
    
    try:
        response = requests.get(url, headers=headers, timeout=5)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # 1. 抓取词性 (Category)
            # Larousse 通常把词性放在 class="Catgramme" 里
            cat_tag = soup.find('p', class_='Catgramme')
            if cat_tag:
                raw_cat = cat_tag.get_text().strip().lower()
                # 简化显示
                if "masculin" in raw_cat: pos = "m. (阳性)"
                elif "féminin" in raw_cat: pos = "f. (阴性)"
                elif "verbe" in raw_cat: pos = "v. (动词)"
                elif "adjectif" in raw_cat: pos = "adj. (形容词)"
                else: pos = raw_cat # 其他情况直接显示原文

            # 2. 抓取例句 (Example)
            # Larousse 的例句通常在 class="Exemple" 里
            ex_tag = soup.find('span', class_='Exemple')
            if ex_tag:
                example = ex_tag.get_text().strip()
                
        return pos, example
    except Exception as e:
        # 如果爬取失败，返回空字符串，不影响主程序
        return "", ""

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
    st.caption("💾 数据同步")
    csv_buffer = st.session_state.df_all.to_csv(index=False, encoding='utf-8').encode('utf-8')
    st.download_button(
        label="📥 下载最新 vocab.csv",
        data=csv_buffer,
        file_name="vocab.csv",
        mime="text/csv",
        type="primary"
    )

# ==========================================
# 5. 查单词模式 (功能升级版)
# ==========================================
if app_mode == "🔍 查单词 (Dictionary)":
    st.header("🔍 Dictionnaire Intelligent")
    
    # 搜索框
    col_search, col_btn = st.columns([4, 1])
    with col_search:
        search_query = st.text_input("输入法语单词:", placeholder="例如: chat").strip()
    
    # 初始化变量，防止报错
    auto_cn = ""
    auto_pos = ""
    auto_ex = ""

    if search_query:
        # 1. 检查是否已存在
        match = df[df['word'].str.lower() == search_query.lower()]
        if not match.empty:
            st.success("✅ 这个词已经在生词本里了！")
            exist_word = match.iloc[0]
            st.info(f"**{exist_word['word']}** ({exist_word['gender']}) : {exist_word['meaning']}")
            st.caption(f"例句: {exist_word['example']}")
        
        else:
            # 2. 联网查询 (翻译 + 爬虫)
            with st.spinner("正在分析单词..."):
                # 获取翻译
                auto_cn, _ = translate_text(search_query)
                # 获取词性和例句 (爬虫)
                auto_pos, auto_ex = get_larousse_details(search_query)

            # 显示结果卡片
            if auto_cn:
                st.markdown(f"### 🇫🇷 {search_query}")
                
                # 播放发音
                audio = get_audio_bytes(search_query)
                if audio:
                    st.audio(audio, format='audio/mp3')

                # 展示抓取到的信息
                c1, c2, c3 = st.columns([1, 1, 2])
                c1.metric("中文意思", auto_cn)
                c2.metric("词性", auto_pos if auto_pos else "未知")
                c3.info(f"**例句:** {auto_ex}" if auto_ex else "暂无例句")

                st.divider()
                st.write("📝 **确认并加入生词本**")
                
                # 自动填充表单
                with st.form("add_word_form"):
                    col_a, col_b = st.columns(2)
                    with col_a:
                        final_word = st.text_input("单词", value=search_query)
                        # 自动填入爬取到的词性
                        final_gender = st.text_input("词性", value=auto_pos, placeholder="m. / f.")
                    with col_b:
                        # 自动填入翻译到的意思
                        final_meaning = st.text_input("中文意思", value=auto_cn)
                        # 自动填入爬取到的例句
                        final_example = st.text_input("例句", value=auto_ex, placeholder="输入例句...")
                    
                    submitted = st.form_submit_button("➕ 加入记忆列表 (Ajouter)")
                    
                    if submitted:
                        new_row = {
                            'word': final_word,
                            'meaning': final_meaning,
                            'gender': final_gender,
                            'example': final_example,
                            'last_review': None,
                            'next_review': date.today().isoformat(),
                            'interval': 0
                        }
                        st.session_state.df_all = pd.concat([st.session_state.df_all, pd.DataFrame([new_row])], ignore_index=True)
                        st.toast(f"已保存: {final_word}！别忘了下载 CSV。", icon="🎉")
                        st.cache_data.clear()
            else:
                st.error("查询失败，请检查网络或单词拼写。")

# ==========================================
# 6. 背单词模式 (保持不变)
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
        
        # 样式
        st.markdown("""
        <style>
            .flash-card {
                background-color: white; padding: 40px; border-radius: 12px;
                border: 1px solid #e0e0e0; box-shadow: 0 4px 12px rgba(0,0,0,0.05);
                text-align: center; margin-bottom: 20px;
            }
            .word-title { font-size: 48px; color: #2c3e50; font-family: 'Playfair Display', serif; }
            .word-meaning { font-size: 24px; color: #e67e22; font-family: 'Patrick Hand', sans-serif; }
            .word-meta { color: #95a5a6; font-size: 18px; }
        </style>
        """, unsafe_allow_html=True)

        audio_bytes = get_audio_bytes(current_word_data['word'])
        if audio_bytes:
            st.audio(audio_bytes, format='audio/mp3', autoplay=True)

        if not st.session_state.show_back:
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
            st.markdown(f"""
            <div class="flash-card">
                <div class="word-title">{current_word_data['word']}</div>
                <div class="word-meta">{current_word_data.get('gender', '')}</div>
                <hr style="opacity:0.2">
                <div class="word-meaning">“ {current_word_data['meaning']} ”</div>
                <div style="margin-top:20px; color:#555; font-style:italic;">
                    {current_word_data.get('example', '')}
                </div>
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
