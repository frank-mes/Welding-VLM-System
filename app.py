import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

# 1. 基础配置
st.set_page_config(page_title="焊接多模态专家系统", layout="wide")

# 2. 数据库连接
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except Exception:
    st.error("数据库连接初始化失败")

# 3. 专家推理引擎 (全参数透明化)
def get_inference_details(mat, thick, meth, grade):
    # 专家知识库基准
    base_i_map = {"Q345R": 110, "316L": 95, "S30408": 100}
    meth_f_map = {"GMAW": 1.0, "GTAW": 0.8, "LBW": 1.5}
    
    # --- 电流推理 (I) ---
    i_base = base_i_map.get(mat, 100)
    i_thick = thick * 12
    m_factor = meth_f_map.get(meth, 1.0)
    g_mod = 0.95 if grade == "一级" else 1.0
    curr_final = (i_base + i_thick) * m_factor * g_mod
    
    # --- 电压推理 (U) ---
    v_const = 18 if grade == "一级" else 16
    v_ratio = 40 if grade == "一级" else 45
    volt_final = v_const + (curr_final / v_ratio)
    
    # --- 速度推理 (V) ---
    spd_final = 200 + (thick * 8)
    
    # 封装计算过程
    trace = {
        "i_calc": f"({i_base} + {i_thick}) * {m_factor} * {g_mod}",
        "u_calc": f"{v_const} + ({round(curr_final,1)} / {v_ratio})",
        "v_calc": f"200 + ({thick} * 8)",
        "i_res
