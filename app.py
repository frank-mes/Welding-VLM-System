import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

# 1. 基础配置
st.set_page_config(page_title="Welding VLM", layout="wide")

# 2. 数据库连接
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except Exception:
    st.error("DB Connection Error")

# 3. 计算引擎
def get_logic(mat, thick, meth, grade):
    # 专家参数
    bm = {"Q345R": 110, "316L": 95, "S30408": 100}
    mf = {"GMAW": 1.0, "GTAW": 0.8, "LBW": 1.5}
    
    ib = bm.get(mat, 100)
    it = thick * 12
    fac = mf.get(meth, 1.0)
    mod = 0.95 if grade == "一级" else 1.0
    
    # 核心推演
    ires = (ib + it) * fac * mod
    ures = (18 + ires/40) if grade == "一级" else (16 + ires/45)
    vres = 200 + (thick * 8)
    
    # 合格率预测
    conf_base = {"一级": 98.0, "二级": 95.0, "三级": 92.0}
    conf_res = conf_base.get(grade, 90.0) - (thick * 0.1)
    
    # 算式字符串
    calc_i = f"({ib} + {it}) * {fac} * {mod}"
    calc_u = f"Base + ({round(ires,1)} / K)"
    
    return ires, ures, vres, conf_res, calc_i, calc_u

# 4. 侧边栏输入 (变量名重构, 移除Emoji)
st.sidebar.header("Input Parameters")
v_mat = st.sidebar.selectbox("Material", ["Q345R", "316L", "S30408"])
v_thick = st.sidebar.slider("Thickness(mm)", 2.0, 50.0, 10.0)
v_meth = st.sidebar.selectbox("Method", ["GMAW", "GTAW", "LBW"])
v_grade = st.sidebar.radio("Grade", ["一级", "二级", "三级"])

# 5. 主页面标题
st.title("Welding Expert System (VLM Optimized)")

# 宏观逻辑展示 (使用 LaTeX 避免字符串截断报错)
with st.expander("Macro Logic Description", expanded=False):
    st.latex(r"I = (I_{base} + 12 \cdot h) \cdot \eta \cdot \delta")
    st.latex(r"U = U_{c} + I / k")
    st.write("Current compensates heat loss; Voltage maintains arc.")

st.markdown("---")

# 6. 计算
iv, uv, vv, cv, exp_i, exp_u = get_logic(v_mat, v_thick, v_meth, v_grade)

# 7. 实例推理路径
st.subheader("Process Traceability")
t1, t2, t3 = st.columns(3)

up_f = st.file_uploader("Upload Image", type=["jpg", "png", "jpeg"])
v_d = 5.0 if up_f else 0.0
f_i = round(iv + v_d, 1)

with t1:
    st.info("Current (I) Path")
    st
