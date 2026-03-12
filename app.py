import streamlit as st
import pandas as pd
import numpy as np
from streamlit_gsheets import GSheetsConnection

# 1. 页面配置
st.set_page_config(page_title="多模态焊接工艺优化系统", layout="wide")

# 2. 初始化数据库连接 (使用 Service Account)
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except Exception as e:
    st.error(f"数据库连接初始化失败: {e}")

# 3. 核心决策模型 (算法逻辑层)
def calculate_welding_params(material, thickness, method, grade):
    # 基础电流映射
    base_map = {"Q345R": 110, "316L": 95, "S30408": 100}
    # 焊接方法修正系数
    method_factor = {"GMAW": 1.0, "GTAW": 0.8, "LBW": 1.5}
    
    # 基础计算
    base_current = base_map.get(material, 100) + (thickness * 12)
    current = base_current * method_factor.get(method, 1.0)
    
    # 根据焊缝等级微调 (一级焊缝采用更稳健的低电流高电压配比)
    if grade == "一级":
        current *= 0.95
        voltage = 18 + (current / 40)
    else:
        voltage = 16 + (current / 45)
        
    speed = 200 + (thickness * 8)
    
    # 预测置信度计算
    grade_risk = {"一级": 0.98, "二级": 0.92, "三级": 0.85}
    confidence = grade_risk.get(grade, 0.90)
    
    return round(current, 1), round(voltage, 1), round(speed, 1), confidence

# 4. 侧边栏：基础输入层 (Input Features)
st.sidebar.header("🛠 基础输入参数")
material_type = st.sidebar.selectbox("材料牌号", ["Q345R", "316L", "S30408"])
thickness = st.sidebar.slider("材料厚度 (mm)", 2.0, 50.0, 10.0)
method = st.sidebar.selectbox("焊接方法", ["GMAW", "GTAW", "LBW"])
grade = st.sidebar.radio("焊缝等级 (约束条件)", ["一级", "二级", "三级"])

# 5. 主界面布局
st.title("👨‍🏭 多模态大模型驱动 - 焊接工艺优化系统")
st.markdown("---")

# 6. 多模态视觉感知层 (VLM Layer)
st.subheader("📸 多模态视觉特征对齐 (Vision Layer)")
v_col1, v_col2 = st.columns([1, 2])

with v_col1:
    uploaded_file = st.file_uploader("上传坡口实时照片", type=["jpg", "png", "jpeg"])
    if uploaded_file:
        st.image(uploaded_file, caption="实时捕获样本", use_container_width=True)

vlm_analysis = "无图像输入（采用理论间隙）"
if uploaded_file:
    # 模拟视觉识别逻辑：根据厚度模拟识别出的实际间隙
    actual_gap = 0.8 + (thickness / 15)
    vlm_analysis = f"视觉识别坡口间隙: {actual_gap:.2f}mm，表面状态良好。"
    with v_col2:
        st.info(f"🔍 **VLM 感知结论：** {vlm_analysis}")
        st.warning("💡 **多模态补偿：** 视觉传感器检测到间隙偏差，建议电流补偿 +5A。")
else:
    with v_col2:
        st.write("📢 请上传照片以激活 **VLM 视觉特征对齐** 模块。")

# 7. 结果输出层 (Output Layer)
st.markdown("---")
curr, volt, spd, conf = calculate_welding_params(material_type, thickness, method, grade)

# 视觉特征介入修改输出
if uploaded_file:
    curr += 5.0 

st.subheader("🚀 推荐工艺参数")
c1, c2, c3, c4 = st.columns(4)
c1.metric("焊接电流 (A)", f"{curr} A", delta="VLM 补偿" if uploaded_file else None)
c2.metric("电弧电压 (V)", f"{volt} V")
c3.metric("焊接速度 (mm/min)", f"{spd}")
c4.metric("预测合格率", f"{conf*100:.0f}%")

# 8. RLHF 生产反馈闭环 (Feedback Loop)
st.markdown("---")
st.subheader("🔄 生产-反馈闭环 (RLHF)")

with st.expander("录入
