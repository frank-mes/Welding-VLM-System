import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

# 1. 页面配置
st.set_page_config(page_title="多模态焊接工艺优化系统", layout="wide")

# 2. 初始化数据库连接
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except Exception as e:
    st.error(f"数据库连接失败: {e}")

# 3. 核心决策模型 (专家系统公式)
def calculate_params(material, thickness, method, grade):
    base_map = {"Q345R": 110, "316L": 95, "S30408": 100}
    method_factor = {"GMAW": 1.0, "GTAW": 0.8, "LBW": 1.5}
    
    # 电流 = (基准 + 厚度增益) * 工艺系数
    base_curr = base_map.get(material, 100) + (thickness * 12)
    current = base_curr * method_factor.get(method, 1.0)
    
    # 等级干预电压配比
    if grade == "一级":
        current *= 0.95
        voltage = 18 + (current / 40)
    else:
        voltage = 16 + (current / 45)
    
    speed = 200 + (thickness * 8)
    # 合格率预测
    grade_risk = {"一级": 0.98, "二级": 0.92, "三级": 0.85}
    return round(current, 1), round(voltage, 1), round(speed, 1), grade_risk.get(grade, 0.90)

# 4. 侧边栏输入 (Input Features)
st.sidebar.header("🛠 基础输入参数")
material_type = st.sidebar.selectbox("材料牌号", ["Q345R", "316L", "S30408"])
thickness = st.sidebar.slider("材料厚度 (mm)", 2.0, 50.0, 10.0)
method = st.sidebar.selectbox("焊接方法", ["GMAW", "GTAW", "LBW"])
grade = st.sidebar.radio("焊缝等级 (约束)", ["一级", "二级", "三级"])

# 5. 主界面
st.title("👨‍🏭 多模态大模型驱动 - 焊接工艺优化系统")
st.markdown("---")

# 6. 多模态视觉感知 (Vision Layer)
st.subheader("📸 多模态视觉特征对齐 (Vision Layer)")
v_col1, v_col2 = st.columns([1, 2])

with v_col1:
    uploaded_file = st.file_uploader("上传坡口实时照片", type=["jpg", "png", "jpeg"])
    if
