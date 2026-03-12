import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

# --- 1. 基础页面配置 ---
st.set_page_config(page_title="焊接优化系统", layout="wide")

# --- 2. 数据库安全连接 ---
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except Exception:
    st.error("数据库链接初始化失败")

# --- 3. 推理引擎：全透明计算逻辑 ---
def get_inference(mat, thick, meth, grade):
    # 专家库基准
    i_base_map = {"Q345R": 110, "316L": 95, "S30408": 100}
    m_fact_map = {"GMAW": 1.0, "GTAW": 0.8, "LBW": 1.5}
    
    # A. 电流 (I) 逻辑推演
    i_b = i_base_map.get(mat, 100)
    i_t = thick * 12
    m_f = m_fact_map.get(meth, 1.0)
    g_m = 0.95 if grade == "一级" else 1.0
    
    # 基础电流结果
    i_res = (i_b + i_t) * m_f * g_m
    
    # B. 电压 (U) 协同推演
    v_c = 18 if grade == "一级" else 16
    v_r = 40 if grade == "一级" else 45
    u_res = v_c + (i_res / v_r)
    
    # C. 速度 (V) 经验推演
    v_res = 200 + (thick * 8)
    
    # 构造具体算式字符串
    calc_i = f"({i_b} + {i_t}) * {m_f} * {g_m}"
    calc_u = f"{v_c} + ({round(i_res,1)} / {v_r})"
    calc_v = f"200 + ({thick} * 8)"
    
    return i_res, u_res, v_res, calc_i, calc_u, calc_v

# --- 4. 侧边栏：参数输入 ---
st.sidebar.header("🛠 工艺特征输入")
in_mat = st.sidebar.selectbox("材料牌号", ["Q345R", "316L", "S30408"])
in_thick = st.sidebar.slider("材料厚度 (mm)", 2.0, 50.0, 10.0)
in
