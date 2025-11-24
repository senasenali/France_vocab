import streamlit as st
import random
import textwrap
import pandas as pd
import datetime

# ==========================================
# 1. 页面配置
# ==========================================
st.set_page_config(
    page_title="Le Menu du Jour", 
    page_icon="🥘",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# ==========================================
# 2. 样式设计
# ==========================================
style_css = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,600;1,600&family=Patrick+Hand&display=swap');

    .stApp {
        background-color: #FDFCF8;
        background-image: radial-gradient(#FDFCF8 20%, #F2EFE9 100%);
    }
    .menu-card {
        background-color: #FFF;
        padding: 50px 30px;
        margin-top: 20px;
        margin-bottom: 30px;
        border: 1px solid #D7CCC8; 
        box-shadow: 0 10px 25px rgba(93, 64, 55, 0.08); 
        text-align: center;
        position: relative;
    }
    .main-title {
        font-family: 'Playfair Display', serif;
        text-align: center;
        color: #3E2723;
        font-size: 42px;
        margin-bottom: 10px;
    }
    .sub-title {
        font-family: 'Patrick Hand', cursive;
        text-align: center;
        color: #8D6E63;
        font-size: 20px;
        margin-bottom: 40px;
    }
    .dish-name {
        font-family: 'Playfair Display', serif;
        font-size: 56px;
        color: #3E2723;
        margin-bottom: 5px;
        font-style: italic;
        letter-spacing: 1px;
        line-height: 1.2;
    }
    .dish-meta {
        font-family: 'Patrick Hand', cursive;
        font-size: 20px;
        color: #78909C;
        margin-bottom: 25px;
    }
    .chef-note {
        font-family: 'Patrick Hand', cursive;
        font-size: 28px;
        color: #8D6E63;
        margin-top: 20px;
    }
    .recipe-box {
        background-color: #FAFAFA;
        border: 1px dashed #BCAAA4;
        padding: 20px;
        margin-top: 30px;
        font-family: 'Patrick Hand', cursive;
        font-size: 22px;
        color: #5D4037;
        line-height: 1.5;
    }
    .menu-divider-top {
        border-top: 3px double #8D6E63;
        width: 60px;
        margin: 0 auto 30px auto;
    }
    .menu-divider-bottom {
        border-bottom: 1px solid #D7CCC8;
        width: 40%;
        margin: 30px auto 0 auto;
    }
    div.stButton > button {
        background-color: transparent;
        color: #5D4037;
        border: 2px solid #8D6E63;
        border-radius: 8px;
        font-family: 'Playfair Display', serif;
        font-size: 18px;
        padding: 12px 20px;
        transition: 0.3s;
        height: auto; 
        white-space: normal;
    }
    div.stButton > button:hover {
        background-color: #8D6E63;
        color: #FFF;
        border-color: #8D6E63;
    }
    @media only screen and (max-width: 600px) {
        .main-title { font-size: 32px; }
        .menu-card { padding: 30px 15px; }
        .dish-name { font-size: 40px; }
        .chef-note { font-size: 24px; }
        .recipe-box { font-size: 18px; padding: 15px; }
        .sub-title { margin-bottom: 20px; }
        div.stButton > button { font-size: 16px; padding: 10px 15px; }
    }
</style>
"""
st.markdown(style_css, unsafe_allow_html=True)

# ==========================================
# 3. 数据加载 (增加了强力纠错功能)
# ==========================================

@st.cache_data
def load_data():
    try:
        # 1. 强制使用 UTF-8 编码读取
        # 2. 自动去除列名两边的空格 (防止 ' word' 这种错误)
        df = pd.read_csv("vocab.csv", encoding='utf-8', keep_default_na=False)
        
        # 3. 清理列名（去除看不见的空格）
        df.columns = df.columns.str.strip()
        
        return df
    except Exception as e:
        return pd.DataFrame() # 返回空表防止报错

# 加载数据
df_all = load_data()
all_words = df_all.to_dict('records')

# ==========================================
# 🔍 调试侧边栏 (Debug Sidebar)
# 这一块能让你看到电脑到底读到了什么
# ==========================================
with st.sidebar:
    st.header("🕵️‍♂️ 厨房后台 (Debug)")
    if df_all.empty:
        st.error("⚠️ 没读到数据！请检查 vocab.csv 文件是否存在，且不是空的。")
    else:
        st.write("当前词汇表预览：")
        st.dataframe(df_all.head(5)) # 只显示前5行
        st.info(f"总共加载了 {len(all_words)} 个单词。")
        
        # 检查列名是否正确
        required_columns = ["word", "meaning", "gender", "example"]
        missing = [col for col in required_columns if col not in df_all.columns]
        if missing:
            st.error(f"❌ 缺少列名: {missing}")
            st.warning("请确保CSV第一行完全匹配: word,meaning,gender,example")
        else:
            st.success("✅ 列名格式正确！")

# ==========================================
# 每日复习逻辑
# ==========================================
if not all_words:
    st.error("暂无数据，请检查侧边栏的错误提示。")
    st.stop()

today_str = datetime.date.today().isoformat()
random.seed(today_str)

if len(all_words) <= 50:
    todays_list = all_words
else:
    todays_list = random.sample(all_words, 50)

random.seed() 

if 'current_dish' not in st.session_state:
    st.session_state.current_dish = random.choice(todays_list)
    st.session_state.show_ingredients = False

def next_dish():
    st.session_state.current_dish = random.choice(todays_list)
    st.session_state.show_ingredients = False

dish = st.session_state.current_dish

# ==========================================
# 4. 界面渲染
# ==========================================
st.markdown("<div class='main-title'>Menu du Vocabulaire</div>", unsafe_allow_html=True)
st.markdown(f"<div class='sub-title'>~ 今日特供: {len(todays_list)} 道菜 (Total: {len(all_words)}) ~</div>", unsafe_allow_html=True)

if not st.session_state.show_ingredients:
    # === 正面 ===
    # 这里我们再次确认引用的是 'word' 字段
    st.markdown(f"""
<div class="menu-card">
<div class="menu-divider-top"></div>
<div style="color: #999; font-family: 'Patrick Hand'; margin-bottom: 10px; font-size:16px;">Plat du Jour (今日特色)</div>
<div class="dish-name">{dish.get('word', 'Error')}</div>
<div style="margin-top: 40px; color: #BCAAA4; font-family: 'Patrick Hand';">
(Toucher pour voir la recette...)
</div>
<div class="menu-divider-bottom"></div>
</div>
""", unsafe_allow_html=True)

    col_a, col_b, col_c = st.columns([1, 2, 1])
    with col_b:
        if st.button("🍽️ Voir les ingrédients (看意思)", use_container_width=True):
            st.session_state.show_ingredients = True
            st.rerun()

else:
    # === 背面 ===
    st.markdown(f"""
<div class="menu-card">
<div class="menu-divider-top"></div>
<div class="dish-name">{dish.get('word', 'Error')}</div>
<div class="dish-meta">{dish.get('gender', '')}</div>
<div class="chef-note">
“ {dish.get('meaning', '')} ”
</div>
<div class="recipe-box">
<span style="color:#8D6E63; font-weight:bold;">Exemple:</span><br>
{dish.get('example', '')}
</div>
<div class="menu-divider-bottom"></div>
</div>
""", unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        if st.button("🍷 Délicieux (记住了)", use_container_width=True):
            st.toast("Bon appétit! 记住了！")
            next_dish()
            st.rerun()
    with col2:
        if st.button("🧂 Trop Salé (忘了)", use_container_width=True):
            next_dish()
            st.rerun()

st.markdown(
    "<br><div style='text-align: center; font-family: Patrick Hand; color: #D7CCC8; font-size: 14px;'>Fait avec amour par Python</div>",
    unsafe_allow_html=True)
