import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

# 1. 基础配置
st.set_page_config(page_title="焊接工艺多模态优化系统", layout="wide")

# 2. 数据库连接
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except Exception:
    st.error("数据库连接失败，请检查配置")

# 3. 核心计算引擎
def get_logic(mat, thick, meth, grade):
    # 专家规则库
    bm = {"Q345R": 110, "316L": 95, "S30408": 100}
    mf = {"GMAW": 1.0, "GTAW": 0.8, "LBW": 1.5}
    
    ib = bm.get(mat, 100)
    it = thick * 12
    fac = mf.get(meth, 1.0)
    mod = 0.95 if grade == "一级" else 1.0
    
    # 执行推演
    ires = (ib + it) * fac * mod
    ures = (18 + ires/40) if grade == "一级" else (16 + ires/45)
    vres = 200 + (thick * 8)
    
    # 合格率预测 (经验模型)
    conf_base = {"一级": 98.0, "二级": 95.0, "三级": 92.0}
    conf_res = conf_base.get(grade, 90.0) - (thick * 0.1)
    
    # 构造具体算式字符串
    calc_i = f"({ib} + {it}) * {fac} * {mod}"
    calc_u = f"基准 + ({round(ires,1)} / 协同系数)"
    
    return ires, ures, vres, conf_res, calc_i, calc_u

# 4. 侧边栏参数输入
st.sidebar.header("参数输入面板")
v_mat = st.sidebar.selectbox("材料牌号", ["Q345R", "316L", "S30408"])
v_thick = st.sidebar.slider("板材厚度(mm)", 2.0, 50.0, 10.0)
v_meth = st.sidebar.selectbox("焊接方法", ["GMAW", "GTAW", "LBW"])
v_grade = st.sidebar.radio("焊缝质量等级", ["一级", "二级", "三级"])

# 5. 主页面标题
st.title("👨‍🏭 焊接工艺多模态优化系统")

# 宏观逻辑展示 (使用 LaTeX)
with st.expander("📘 查看宏观专家知识逻辑", expanded=False):
    st.markdown("### 核心推理公式")
    st.latex(r"I = (I_{base} + 12 \cdot h) \cdot \eta \cdot \delta")
    st.latex(r"U = U_{c} + I / k")
    st.write("逻辑：电流补偿厚度热损，电压维持电弧稳定。")

st.markdown("---")

# 6. 计算执行
iv, uv, vv, cv, exp_i, exp_u = get_logic(v_mat, v_thick, v_meth, v_grade)

# 7. 实例具体推导路径 (Traceability)
st.subheader("📝 实例具体计算推导路径")
t1, t2, t3 = st.columns(3)

up_f = st.file_uploader("上传坡口照片 (视觉感知)", type=["jpg", "png", "jpeg"])
v_d = 5.0 if up_f else 0.0
f_i = round(iv + v_d, 1)

with t1:
    st.info("**电流 (I) 推导路径**")
    st.code(f"推演算式: {exp_i}\n视觉补偿: +{v_d}\n最终结果: {f_i} A")

with t2:
    st.info("**电压 (U)
            
