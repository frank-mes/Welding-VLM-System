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

# 3. 专家推理引擎 (逻辑加固版)
def get_inference_details(mat, thick, meth, grade):
    # 专家知识库基准
    base_i_map = {"Q345R": 110, "316L": 95, "S30408": 100}
    meth_f_map = {"GMAW": 1.0, "GTAW": 0.8, "LBW": 1.5}
    
    # 计算电流 (I)
    i_b = base_i_map.get(mat, 100)
    i_t = thick * 12
    m_f = meth_f_map.get(meth, 1.0)
    g_m = 0.95 if grade == "一级" else 1.0
    
    curr_f = (i_b + i_t) * m_f * g_m
    
    # 计算电压 (U)
    v_c = 18 if grade == "一级" else 16
    v_r = 40 if grade == "一级" else 45
    volt_f = v_c + (curr_f / v_r)
    
    # 计算速度 (V)
    spd_f = 200 + (thick * 8)
    
    # 构造展示用的算式字符串 (分段构造防止截断)
    i_str = f"({i_b} + {i_t}) * {m_f} * {g_m}"
    u_str = f"{v_c} + ({round(curr_f, 1)} / {v_r})"
    v_str = f"200 + ({thick} * 8)"
    
    return {
        "i_calc": i_str,
        "u_calc": u_str,
        "v_calc": v_str,
        "i_res": round(curr_f, 1),
        "u_res": round(volt_f, 1),
        "v_res": round(spd_f, 1)
    }

# 4. 侧边栏输入
st.sidebar.header("🛠 输入特征")
in_mat = st.sidebar.selectbox("材料牌号", ["Q345R", "316L", "S30408"])
in_thick = st.sidebar.slider("板材厚度 (mm)", 2.0, 50.0, 10.0)
in_meth = st.sidebar.selectbox("焊接方法", ["GMAW", "GTAW", "LBW"])
in_grade = st.sidebar.radio("质量等级", ["一级", "二级", "三级"])

# 5. 主页面标题
st.title("👨‍🏭 焊接工艺多模态优化系统")

# 宏观逻辑说明
with st.expander("📘 查看宏观专家知识逻辑", expanded=False):
    st.markdown("""
    **推理原则说明：**
    1. **热输入模型**：电流
    
