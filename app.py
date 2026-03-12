import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

# 1. 基础配置
st.set_page_config(page_title="焊接多模态专家系统", layout="wide")

# 2. 数据库连接
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except Exception:
    st.error("数据库链接异常")

# 3. 核心计算引擎 (包含预测逻辑)
def get_full_logic(mat, thick, meth, grade):
    # 专家参数
    base_i_map = {"Q345R": 110, "316L": 95, "S30408": 100}
    meth_f_map = {"GMAW": 1.0, "GTAW": 0.8, "LBW": 1.5}
    
    # --- I 推导 ---
    i_b = base_i_map.get(mat, 100)
    i_t = thick * 12
    m_f = meth_f_map.get(meth, 1.0)
    g_m = 0.95 if grade == "一级" else 1.0
    i_res = (i_b + i_t) * m_f * g_m
    
    # --- U 推导 ---
    v_c = 18 if grade == "一级" else 16
    v_r = 40 if grade == "一级" else 45
    u_res = v_c + (i_res / v_r)
    
    # --- V 推导 ---
    v_res = 200 + (thick * 8)
    
    # --- 合格率预测 (基于等级与厚度的经验模型) ---
    # 厚度越大、等级越高，预测风险略微提升
    base_conf = {"一级": 0.98, "二级": 0.95, "三级": 0.92}
    conf = base_conf.get(grade, 0.90) - (thick * 0.001)
    
    # 构造算式展示
    calc_steps = {
        "i_exp": f"({i_b} + {i_t}) * {m_f} * {g_m}",
        "u_exp": f"{v_c} + ({round(i_res,1)} / {v_r})",
        "v_exp": f"200 + ({thick} * 8)",
        "i_final": round(i_res, 1),
        "u_final": round(u_res, 1),
        "v_final": round(v_res, 1),
        "conf": round(conf * 100, 1)
    }
    return calc_steps

# 4. 侧边栏
st.sidebar.header("🛠 工艺输入")
v_mat = st.sidebar.selectbox("材料牌号", ["Q345R", "316L", "S30408"])
v_thick = st.sidebar.slider("材料厚度(mm)", 2.0, 50.0, 10.0)
v_meth = st.sidebar.selectbox("焊接方法", ["GMAW", "GTAW", "LBW"])
v_grade = st.sidebar.radio("质量等级", ["一级", "二级", "三级"])

# 5. 主页面标题
st.title("👨‍🏭 焊接工艺多模态优化系统")

# 补全：宏观逻辑公式说明
with st.expander("📘 查看宏观算法推理逻辑 (Macro Logic)", expanded=False):
    st.markdown("### 核心推理算式")
    st.latex(r"I_{base} = (I_{material} + 12 \cdot h) \cdot \eta_{method} \cdot \delta_{grade}")
    st.latex(r"U_{synergic} = U_{const} + \frac{I_{base}}{k_{synergic}}")
    st.latex(r"V_{travel} = 200 + 8 \cdot h")
    st.markdown("""
    **变量说明：**
    - $h$: 板材厚度 |
