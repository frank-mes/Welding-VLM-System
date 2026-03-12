import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

# 1. 基础配置
st.set_page_config(page_title="焊接多模态专家系统", layout="wide")

# 2. 数据库连接
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except Exception:
    st.error("数据库连接异常")

# 3. 专家推理引擎 (逻辑白盒化迭代)
def get_logic(mat, thick, meth, grade):
    # 专家库定义
    bm_lib = {
        "Q345R": {"base": 110, "info": "碳钢：热敏感度高"},
        "316L": {"base": 95, "info": "不锈钢：易过热变形"},
        "S30408": {"base": 100, "info": "合金钢：需稳态控制"}
    }
    mf_lib = {"GMAW": 1.0, "GTAW": 0.8, "LBW": 1.5}
    
    sel_bm = bm_lib.get(mat, {"base": 100, "info": "未知"})
    i_b = sel_bm["base"]
    i_t = thick * 12 # 补偿系数：12A/mm
    m_f = mf_lib.get(meth, 1.0)
    g_f = 0.95 if grade == "一级" else 1.0
    
    # 核心计算
    i_raw = (i_b + i_t) * m_f * g_f
    u_base = 18 if grade == "一级" else 16
    u_k = 40 if grade == "一级" else 45
    u_raw = u_base + (i_raw / u_k)
    v_raw = 200 + (thick * 8)
    conf = (98.0 if grade == "一级" else 94.0) - (thick * 0.1)
    
    return {
        "i_b": i_b, "i_t": i_t, "m_f": m_f, "g_f": g_f,
        "u_b": u_base, "u_k": u_k, "i_r": round(i_raw, 1),
        "u_r": round(u_raw, 1), "v_r": v_raw, "c_r": round(conf, 1),
        "desc": sel_bm["info"]
    }

# 4. 侧边栏输入
st.sidebar.header("参数输入面板")
v_mat = st.sidebar.selectbox("材料牌号", ["Q345R", "316L", "S30408"])
v_thick = st.sidebar.slider("板材厚度(mm)", 2.0, 50.0, 10.0)
v_meth = st.sidebar.selectbox("焊接方法", ["GMAW", "GTAW", "LBW"])
v_grade = st.sidebar.radio("焊缝等级", ["一级", "二级", "三级"])

# 5. 主页面标题
st.title("👨‍🏭 焊接工艺多模态优化系统")

# 迭代 1：宏观专家知识逻辑 (细致化说明)
with st.expander("📘 查看宏观专家知识逻辑说明", expanded=True):
    st.markdown("### 能量平衡与协同控制准则")
    st.latex(r"I_{final} = (I_{material} + \alpha \cdot h) \cdot \eta \cdot \delta")
    st.markdown("""
    **核心物理逻辑拆解：**
    - **热补偿原理
