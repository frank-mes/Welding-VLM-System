import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

# 1. 页面基础配置
st.set_page_config(page_title="焊接多模态专家系统", layout="wide")

# 2. 数据库连接初始化
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except Exception:
    st.error("数据库链接异常，请检查 Secrets 配置")

# 3. 核心推演引擎 (基于专家知识库)
def get_welding_logic(mat, thick, meth, grade):
    # --- 基础规则配置 ---
    base_i_map = {"Q345R": 110, "316L": 95, "S30408": 100}
    meth_f_map = {"GMAW": 1.0, "GTAW": 0.8, "LBW": 1.5}
    
    # --- 电流 (I) 推导过程 ---
    i_b = base_i_map.get(mat, 100)
    i_t = thick * 12
    m_f = meth_f_map.get(meth, 1.0)
    g_m = 0.95 if grade == "一级" else 1.0
    i_res = (i_b + i_t) * m_f * g_m
    
    # --- 电压 (U) 推导过程 ---
    v_c = 18 if grade == "一级" else 16
    v_r = 40 if grade == "一级" else 45
    u_res = v_c + (i_res / v_r)
    
    # --- 速度 (V) 推导过程 ---
    v_res = 200 + (thick * 8)
    
    # --- 合格率预测模型 (Confidence) ---
    base_conf = {"一级": 0.98, "二级": 0.95, "三级": 0.92}
    conf = base_conf.get(grade, 0.90) - (thick * 0.001)
    
    # 封装计算路径文本
    return {
        "i_exp": f"({i_b} + {i_t}) * {m_f} * {g_m}",
        "u_exp": f"{v_c} + ({round(i_res,1)} / {v_r})",
        "v_exp": f"200 + ({thick} * 8)",
        "i_val": round(i_res, 1),
        "u_val": round(u_res, 1),
        "v_val": round(v_res, 1),
        "conf": round(conf * 100, 1)
    }

# 4. 侧边栏：工艺特征输入层
st.sidebar.header("🛠
