import streamlit as st
import pandas as pd
import datetime
from datetime import date, timedelta
import random
import io
import json
import google.generativeai as genai
from gtts import gTTS

# ==========================================
# 1. 页面配置
# ==========================================
st.set_page_config(
    page_title="Le Menu du Jour - AI版", 
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

# --- B. AI 核心功能 (兼容版) ---
def ask_gemini_for_word_info(api_key, word):
    """
    调用 Gemini API 获取单词的详情
    使用 gemini-pro 模型，兼容性更好
    """
    if not api_key:
        return None, "请先在侧边栏输入 API Key"
    
    try:
        # 配置 API
        genai.configure(api_key=api_key)
        
        # 使用旧版稳定模型 gemini-pro
        # 注意：这里我们不使用 response_mime_type 参数，防止旧库报错
        model = genai.GenerativeModel('gemini-pro')
        
        prompt = f"""
        你是一个法语老师。请分析单词 "{word}"。
        请直接返回一个纯 JSON 字符串。
        严禁使用 Markdown 格式 (不要写 ```json ... ```)。
        
        JSON 格式如下:
        {{
            "meaning": "中文含义(简练)",
            "gender": "词性(如 m. / f. / v.)",
            "example": "简短的法语例句"
        }}
        """
        
        response = model.generate_content(prompt)
        
        # 手动清理数据 (防止 AI 有时候还是会加 markdown 符号)
        clean_text = response.text.strip()
        if clean_text.startswith("```json"):
            clean_text = clean_text[7:]
        if clean_text.startswith("```"):
            clean_text = clean_text[3:]
        if clean_text.endswith("```"):
            clean_text = clean_text[:-3]
        
        # 解析 JSON
        result_dict = json.loads(clean_text)
        return result_dict, None

    except Exception as e:
        return None, f"AI 调用失败: {str(e)}"

# --- C. 记忆曲线算法 ---
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
# 4. 侧边栏 (增加 API Key 输入框)
# ==========================================
with st.sidebar:
    st.title("🇫🇷 Menu Français")
    
    # --- API Key 配置 ---
    with st.expander("🔑 AI 设置 (必填)", expanded=not bool(st.session_state.get('gemini_key'))):
        user_api_key = st.text_input("输入 Google Gemini API Key:", type="password", help="去 aistudio.google.com 免费申请")
        if user_api_key:
            st.session_state['gemini_key'] = user_api_key
            st.success("已就绪!")
    
    st.divider()
    
    app_mode = st.radio("选择模式", ["🔍 AI 查单词 (Dictionary)", "📖 背单词 (Review)"])
    
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
# 5. 查单词模式 (AI版)
# ==========================================
if app_mode == "🔍 AI 查单词 (Dictionary)":
    st.header("🤖 AI 智能词典")
    st.caption("由 Google Gemini 提供支持")
    
    col_search, col_btn = st.columns([4, 1])
    with col_search:
        search_query = st.text_input("输入法语单词:", placeholder="例如: chat").strip()
    
    # 预初始化变量
    auto_cn, auto_pos, auto_ex = "", "", ""

    if search_query:
        # 1. 查重
        match = df[df['word'].str.lower() == search_query.lower()]
        if not match.empty:
            st.success("✅ 单词已存在！")
            exist_word = match.iloc[0]
            st.info(f"**{exist_word['word']}** ({exist_word['gender']}) : {exist_word['meaning']}")
            st.caption(f"例句: {exist_word['example']}")
        else:
            # 2. 调用 AI
            api_key = st.session_state.get('gemini_key')
            
            if not api_key:
                st.warning("⚠️ 请先在侧边栏输入 Google API Key 才能使用 AI 功能。")
            else:
                with st.spinner("🤖 AI 正在思考词性和造句..."):
                    ai_result, error_msg = ask_gemini_for_word_info(api_key, search_query)
                
                if error_msg:
                    st.error(error_msg)
                elif ai_result:
                    # 获取 AI 的结果
                    auto_cn = ai_result.get('meaning', '')
                    auto_pos = ai_result.get('gender', '')
                    auto_ex = ai_result.get('example', '')

                    # 显示结果
                    st.markdown(f"### 🇫🇷 {search_query}")
                    audio = get_audio_bytes(search_query)
                    if audio: st.audio(audio, format='audio/mp3')
                    
                    c1, c2, c3 = st.columns([1, 1, 2])
                    c1.metric("中文意思", auto_cn)
                    c2.metric("词性", auto_pos)
                    c3.info(f"**AI造句:** {auto_ex}")

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

# ==========================================
# 6. 背单词模式 (不变)
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

st.markdown("<br><div style='text-align:center; color:#ddd;'>Powered by Gemini AI</div>", unsafe_allow_html=True)

