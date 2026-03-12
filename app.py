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

# 3. 增强型推理引擎 (深度解释逻辑)
def get_logic(mat, thick, meth, grade):
    # --- 宏观知识库定义 ---
    # 材料热物理常数描述
    bm_lib = {
        "Q345R": {"base": 110, "note": "普通碳钢：热影响区较宽，需适中热输入以平衡熔深与晶粒粗化。"},
        "316L": {"base": 95, "note": "不锈钢：热传导率低且线膨胀系数大，极易过热变形，须严格限制电流。"},
        "S30408": {"base": 100, "note": "奥氏体钢：对热裂纹敏感，推导逻辑侧重于快速凝固控制。"}
    }
    # 焊接方法能量密度系数 (η)
    mf_lib = {"GMAW": 1.0, "GTAW": 0.8, "LBW": 1.5}
    
    # --- 微观推导计算 ---
    sel_bm = bm_lib.get(mat, {"base": 100, "note": "常规材料"})
    i_b = sel_bm["base"]
    i_t = thick * 12 # 能量补偿系数: 每mm板厚增加12A以维持电弧穿透力
    m_f = mf_lib.get(meth, 1.0)
    g_f = 0.95 if grade == "一级" else 1.0 # 优质焊缝采用“小电流、慢速度”策略以优化组织
    
    # 核心结果
    i_r = (i_b + i_t) * m_f * g_f
    u_base = 18 if grade == "一级" else 16 # 协同电压起步值
    u_k = 40 if grade == "一级" else 45    # 协同控制斜率(k)
    u_r = u_base + (i_r / u_k)
    v_r = 200 + (thick * 8)
    conf = (98.0 if grade == "一级" else 94.0) - (thick * 0.1)
    
    return {
        "i_b": i_b, "i_t": i_t, "m_f": m_f, "g_f": g_f,
        "u_b": u_base, "u_k": u_k, "i_res": round(i_r, 1),
        "u_res": round(u_r, 1), "v_res": v_r, "c_res": round(conf, 1),
        "note": sel_bm["note"]
    }

# 4. 侧边栏输入
st.sidebar.header("工艺特征输入")
v_mat = st.sidebar.selectbox("材料牌号", ["Q345R", "316L", "S30408"])
v_thick = st.sidebar.slider("板厚(mm)", 2.0, 50.0, 10.0)
v_meth = st.sidebar.selectbox("焊接方法", ["GMAW", "GTAW", "LBW"])
v_grade = st.sidebar.radio("质量等级", ["一级", "二级", "三级"])

# 5. 主页面
st.title("👨‍🏭 焊接工艺多模态优化系统")

# 迭代 1：宏观专家知识逻辑 (细致化迭代)
with st.expander("📘 宏观专家知识逻辑 - 深度解析", expanded=True):
    st.write("### 核心物理推导模型：能量平衡与协同控制")
    st.latex(r"I_{target} = (I_{material} + \alpha \cdot h) \cdot \eta_{method} \cdot \delta_{grade}")
    st.latex(r"U_{synergic} = U_{start} + \frac{I_{target}}{k}")
    
    c_m1, c_m2 = st.columns(2)
    with c_m1:
        st.write("**1. 能量补偿准则 (Energy Compensation)**")
        st.write("板厚 $h$ 是决定热损失量的关键维度。推导逻辑通过线性补偿系数 $\\alpha=12$ 来对冲热传导损耗，确保熔池底部获得足够的能量输入。")
    with c_m2:
        st.write("**2. 协同控制原理 (Synergic Principle)**")
        st.write("电压 $U$ 不再是独立变量。它基于电弧物理特性，随电流 $I$ 同步波动，以维持最优的电弧长度和熔滴过渡稳定性。")
    
    

st.markdown("---")

# 6. 计算执行
res = get_logic(v_mat, v_thick, v_meth, v_grade)

# 迭代 2：实例具体计算推导 (细致化迭代)
st.subheader("📝 实例具体计算推导路径 (Step-by-Step
