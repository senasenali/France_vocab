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

    /* 手机端适配 */
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
# 3. 数据加载与每日逻辑 (核心修改部分)
# ==========================================

@st.cache_data
def load_data():
    try:
        # 读取同目录下的 vocab.csv 文件
        # keep_default_na=False 防止把法语单词 "Null" 误读为空值
        df = pd.read_csv("vocab.csv", keep_default_na=False)
        return df.to_dict('records')
    except FileNotFoundError:
        return []


# 加载全部单词
all_words = load_data()

# === 每日复习逻辑 ===
if not all_words:
    st.error("找不到单词表 (vocab.csv)。请先上传文件！")
    st.stop()

# 获取今天的日期字符串 (例如 "2023-10-27")
today_str = datetime.date.today().isoformat()

# 使用今天的日期作为随机数种子
# 这样保证在同一天内，随机挑选出的50个单词是固定的
random.seed(today_str)

# 确定今日复习列表
if len(all_words) <= 50:
    todays_list = all_words  # 不足50个，就复习全部
else:
    # 从总库中随机抽取50个，但这50个在今天是不变的
    todays_list = random.sample(all_words, 50)

# 重置随机种子，以免影响后面按钮点击时的随机切换
# (我们需要列表是固定的，但切换单词时需要真随机)
random.seed()

# 初始化 Session State
if 'current_dish' not in st.session_state:
    st.session_state.current_dish = random.choice(todays_list)
    st.session_state.show_ingredients = False


def next_dish():
    # 从今日列表中随机选一个
    st.session_state.current_dish = random.choice(todays_list)
    st.session_state.show_ingredients = False


dish = st.session_state.current_dish

# ==========================================
# 4. 界面渲染
# ==========================================
st.markdown("<div class='main-title'>Menu du Vocabulaire</div>", unsafe_allow_html=True)
# 显示今日复习数量
st.markdown(f"<div class='sub-title'>~ 今日特供: {len(todays_list)} 道菜 (Total: {len(all_words)}) ~</div>",
            unsafe_allow_html=True)

if not st.session_state.show_ingredients:
    # === 正面 ===
    st.markdown(f"""
<div class="menu-card">
<div class="menu-divider-top"></div>
<div style="color: #999; font-family: 'Patrick Hand'; margin-bottom: 10px; font-size:16px;">Plat du Jour (今日特色)</div>
<div class="dish-name">{dish['word']}</div>
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
<div class="dish-name">{dish['word']}</div>
<div class="dish-meta">{dish['gender']}</div>
<div class="chef-note">
“ {dish['meaning']} ”
</div>
<div class="recipe-box">
<span style="color:#8D6E63; font-weight:bold;">Exemple:</span><br>
{dish['example']}
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

# 页脚
st.markdown(
    "<br><div style='text-align: center; font-family: Patrick Hand; color: #D7CCC8; font-size: 14px;'>Fait avec amour par Python</div>",
    unsafe_allow_html=True)