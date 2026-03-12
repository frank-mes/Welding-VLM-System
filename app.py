import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

# 1. 基础配置
st.set_page_config(page_title="焊接多模态专家系统", layout="wide")

# 2. 数据库连接
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except Exception:
    st.error("数据库连接失败")

# 3. 专家推理引擎 (逻辑深度白盒化)
def get_logic(mat, thick, meth, grade):
    # 专家知识库：定义不同材料的热物理特性
    bm_lib = {
        "Q345R": {"base": 110, "info": "碳钢: 导热系数约45W/(m·K)，需中等能量密度"},
        "316L": {"base": 95, "info": "不锈钢: 导热差但膨胀大，电流过大会造成烧穿"},
        "S30408": {"base": 100, "info": "奥氏体钢: 需控制层间温度，电流取中间值"}
    }
    # 方法修正系数 (eta)
    mf_lib = {"GMAW": 1.0, "GTAW": 0.8, "LBW": 1.5}
    
    # --- 核心变量提取 ---
    sel_bm = bm_lib.get(mat, {"base": 100, "info": "未知材料"})
    i_b = sel_bm["base"]
    i_t = thick * 12 # 物理补偿：1mm厚度需12A能量抵消侧向散热
    m_f = mf_lib.get(meth, 1.0)
    g_f = 0.95 if grade == "一级" else 1.0 # 质量权重：一级焊缝限制线能量防止晶粒粗大
    
    # --- 逻辑推演结果 ---
    i_r = (i_b + i_t) * m_f * g_f
    # 协同控制斜率：一级焊缝取K=40以获得更硬的电弧
    u_base = 18 if grade == "一级" else 16
    u_k = 40 if grade == "一级" else 45
    u_r = u_base + (i_r / u_k)
    v_r = 200 + (thick * 8)
    # 物理信心度模型
    conf = (98.0 if grade == "一级" else 94.0) - (thick * 0.1)
    
    return {
        "i_b": i_b, "i_t": i_t, "m_f": m_f, "g_f": g_f,
        "u_b": u_base, "u_k": u_k, "i_res": round(i_r, 1),
        "u_res": round(u_r, 1), "v_res": v_raw_val := v_r, "c_res": round(conf, 1),
        "desc": sel_bm["info"]
    }

# 4. 侧边栏输入
st.sidebar.header("工艺特征输入")
v_mat = st.sidebar.selectbox("材料牌号", ["Q345R", "316L", "S30408"])
v_thick = st.sidebar.slider("板厚(mm)", 2.0, 50.0, 10.0)
v_meth = st.sidebar.selectbox("焊接方法", ["GMAW", "GTAW", "LBW"])
v_grade = st.sidebar.radio("质量等级", ["一级", "二级", "三级"])

# 5. 主页面标题
st.title("👨‍🏭 焊接工艺多模态专家系统")

# 迭代 1：宏观专家知识逻辑 (细致化迭代)
with st.expander("📘 宏观专家知识逻辑 - 物理模型解析", expanded=True):
    st.write("### 核心算式：线能量输入控制模型")
    st.latex(r"I_{target} = (I_{material} + \alpha \cdot h) \cdot \eta_{method} \cdot \delta_{grade}")
    st.latex(r"U_{synergic} = U_{start} +
