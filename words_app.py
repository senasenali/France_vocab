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
    page_title="Le Menu du Jour - Classic", 
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

# --- B. 翻译功能 (使用 deep-translator) ---
@st.cache_data(show_spinner=False)
def translate_text(text):
    try:
        # 使用 Google 翻译接口
        cn_meaning = GoogleTranslator(source='fr', target='zh-CN').translate(text)
        return cn_meaning
    except Exception:
        return ""

# --- C. 爬虫功能 (增强版：精准抓取阴阳性与过滤例句) ---
@st.cache_data(show_spinner="正在查阅维基词典...")
def get_wiktionary_details(word):
    """
    爬取 fr.wiktionary.org
    修复了 'chat' 抓取不到阴阳性和抓到错误例句的问题
    """
    word = word.strip().lower()
    url = f"https://fr.wiktionary.org/wiki/{word}"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    pos = "未知"      
    example = ""  
    
    try:
        response = requests.get(url, headers=headers, timeout=5)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # === 1. 精准抓取性别 (Gender) ===
            # 策略：直接在“法语”部分的定义行里找 "masculin" 或 "féminin" 关键字
            # 维基词典通常在 class="ligne-de-forme" 或者定义头里写性别
            
            # 先找到法语区 (id="Français")
            fr_section = soup.find(id="Français")
            if fr_section:
                # 缩小搜索范围，只看法语部分
                parent = fr_section.find_parent()
                # 寻找包含性别的行
                gender_line = parent.find_next('span', class_='ligne-de-forme')
                
                if gender_line:
                    text = gender_line.get_text().lower()
                    if 'masculin' in text or ' m' in text:
                        pos = "m. (阳性)"
                    elif 'féminin' in text or ' f' in text:
                        pos = "f. (阴性)"
                
                # 如果上面没找到，尝试在所有 title="Nom commun" 附近找
                if pos == "未知":
                    all_pos_headers = soup.find_all('span', class_='titredef')
                    for header in all_pos_headers:
                        if 'nom' in header.get_text().lower():
                            # 往后找一行
                            next_line = header.find_next('p')
                            if next_line:
                                txt = next_line.get_text().lower()
                                if 'masculin' in txt: 
                                    pos = "m. (阳性)"
                                    break
                                elif 'féminin' in txt: 
                                    pos = "f. (阴性)"
                                    break
                            pos = "n. (名词)" # 找到了名词但没分出性别
            
            # === 2. 智能抓取例句 (Example) ===
            # 策略：过滤掉短标签（如 Félinologie），只保留像句子的文本
            
            # 优先找明确标记为例句的 span
            ex_tags = soup.find_all('span', class_='exemple')
            for ex in ex_tags:
                txt = ex.get_text().strip()
                if len(txt) > 15: # 长度过滤
                    example = txt
                    break
            
            # 如果没找到，遍历所有列表里的斜体字 (维基词典惯用格式)
            if not example:
                li_tags = soup.find_all('li')
                for li in li_tags:
                    # 必须包含斜体 (通常例句是斜体)
                    italic = li.find('i')
                    if italic:
                        raw_text = italic.get_text().strip()
                        
                        # === 核心过滤逻辑 ===
                        # 1. 长度必须 > 15 (过滤掉 "Félinologie")
                        # 2. 不能以 "(" 开头 (过滤掉解释性文字)
                        # 3. 必须包含空格 (确保是句子)
                        if len(raw_text) > 15 and not raw_text.startswith('(') and ' ' in raw_text:
                            # 4. (可选) 最好包含原单词
                            # if word in raw_text.lower(): 
                            example = raw_text
                            break

        # === 3. 兜底造句 (如果还是没抓到) ===
        if not example:
            if "m." in pos: example = f"Le {word} est ici."
            elif "f." in pos: example = f"La {word} est belle."
            elif "v." in pos: example = f"Je veux {word}."
            elif "adj" in pos: example = f"C'est très {word}."
        
        # 如果词性依然是未知，尝试根据常见后缀猜一下 (Beta)
        if pos == "未知" or pos == "n. (名词)":
            if word.endswith('e') and not word.endswith('age') and not word.endswith('isme'):
                suggestion = "f. (阴性?)"
            else:
                suggestion = "m. (阳性?)"
            if pos == "n. (名词)": pos = f"n. {suggestion}"

        return pos, example

    except Exception:
        return "未知", ""
        
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
# 3. 数据加载 (安全版)
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
        
        # 强制修复日期格式 (防止 TypeError)
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
# 5. 查单词模式 (Wiki + Translation)
# ==========================================
if app_mode == "🔍 查单词 (Dictionary)":
    st.header("🔍 Dictionnaire (Wiki版)")
    
    col_search, col_btn = st.columns([4, 1])
    with col_search:
        search_query = st.text_input("输入法语单词:", placeholder="例如: chat").strip()
    
    # 预初始化
    auto_cn, auto_pos, auto_ex = "", "", ""

    if search_query:
        # 查重
        match = df[df['word'].str.lower() == search_query.lower()]
        if not match.empty:
            st.success("✅ 单词已存在！")
            exist_word = match.iloc[0]
            st.info(f"**{exist_word['word']}** ({exist_word['gender']}) : {exist_word['meaning']}")
            st.caption(f"例句: {exist_word['example']}")
        else:
            # 联网查询
            with st.spinner("🔍 正在检索维基词典..."):
                # 1. 翻译意思
                auto_cn = translate_text(search_query)
                # 2. 爬取详情
                auto_pos, auto_ex = get_wiktionary_details(search_query)

            if auto_cn:
                st.markdown(f"### 🇫🇷 {search_query}")
                audio = get_audio_bytes(search_query)
                if audio: st.audio(audio, format='audio/mp3')
                
                c1, c2, c3 = st.columns([1, 1, 2])
                c1.metric("中文意思", auto_cn)
                c2.metric("词性", auto_pos if auto_pos else "未知")
                c3.info(f"**例句:** {auto_ex}" if auto_ex else "暂无")

                st.divider()
                st.write("📝 **加入生词本**")
                with st.form("add_word_form"):
                    col_a, col_b = st.columns(2)
                    with col_a:
                        final_word = st.text_input("单词", value=search_query)
                        final_gender = st.text_input("词性", value=auto_pos)
                    with col_b:
                        final_meaning = st.text_input("中文意思", value=auto_cn)
                        final_example = st.text_input("例句", value=auto_ex)
                    
                    if st.form_submit_button("➕ 加入记忆列表"):
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
                        st.toast(f"已保存: {final_word}！", icon="🎉")
                        st.cache_data.clear()
            else:
                st.error("查询失败 (可能是网络原因)，请稍后再试。")

# ==========================================
# 6. 背单词模式 (复习)
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

st.markdown("<br><div style='text-align:center; color:#ddd;'>Powered by Wiktionary & Python</div>", unsafe_allow_html=True)

