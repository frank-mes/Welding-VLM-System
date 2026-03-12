import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

# 1. 页面配置
st.set_page_config(page_title="多模态焊接优化系统", layout="wide")

# 2. 初始化数据库连接
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except Exception as e:
    st.error("数据库连接初始化失败")

# 3. 核心计算函数 (包含中间步骤导出)
def calculate_params(material, thickness, method, grade):
    base_map = {"Q345R": 110, "316L": 95, "S30408": 100}
    method_factor = {"GMAW": 1.0, "GTAW": 0.8, "LBW": 1.5}
    
    # 步骤 A: 确定基准
    i_base = base_map.get(material, 100)
    # 步骤 B: 厚度增益
    i_thick = thickness * 12
    # 步骤 C: 工艺系数
    m_factor = method_factor.get(method, 1.0)
    
    # 初始电流合成
    current = (i_base + i_thick) * m_factor
    
    # 等级修正逻辑
    if grade == "一级":
        current_adj = current * 0.95
        voltage = 18 + (current_adj / 40)
    else:
        current_adj = current
        voltage = 16 + (current_adj / 45)
        
    speed = 200 + (thickness * 8)
    grade_risk = {"一级": 0.98, "二级": 0.92, "三级": 0.85}
    
    # 记录推演步骤
    steps = {
        "i_base": i_base,
        "i_thick": i_thick,
        "m_factor": m_factor,
        "grade_mod": "x0.95" if grade == "一级" else "x1.0"
    }
    return round(current_adj, 1), round(voltage, 1), round(speed, 1), grade_risk.get(grade, 0.90), steps

# 4. 侧边栏控制
st.sidebar.header("🛠 参数输入")
material_type = st.sidebar.selectbox("材料牌号", ["Q345R", "316L", "S30408"])
thickness = st.sidebar.slider("材料厚度 (mm)", 2.0, 50.0, 10.0)
method = st.sidebar.selectbox("焊接方法", ["GMAW", "GTAW", "LBW"])
grade = st.sidebar.radio("焊缝等级", ["一级", "二级", "三级"])

# 5. 主页面标题
st.title("👨‍🏭 多模态大模型驱动 - 焊接工艺优化系统")
st.markdown("---")
