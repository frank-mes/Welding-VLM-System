import streamlit as st
import pandas as pd
import numpy as np

# 1. 页面配置
st.set_page_config(page_title="焊接工艺参数优化系统", layout="wide")

# 2. 模拟 VLM 模型推理逻辑 (后续可接入真实 API)
def calculate_welding_params(material, thickness, method):
    # 基础物理逻辑模拟
    base_map = {"Q345R": 110, "316L": 95, "S30408": 100}
    current = base_map.get(material, 100) + (thickness * 12)
    voltage = 16 + (current / 45)
    speed = 200 + (thickness * 8)
    confidence = 0.94 if thickness < 20 else 0.85
    return round(current, 1), round(voltage, 1), round(speed, 1), confidence

# 3. 侧边栏：输入层
st.sidebar.header("🛠 输入层 (Input Layer)")
material_type = st.sidebar.selectbox("材料牌号", ["Q345R", "316L", "S30408"])
thickness = st.sidebar.slider("材料规格 (厚度 mm)", 2.0, 50.0, 10.0)
method = st.sidebar.selectbox("焊接方法", ["GMAW", "GTAW", "LBW"])
grade = st.sidebar.radio("焊缝等级", ["一级", "二级", "三级"])

# 4. 主界面
st.title("👨‍🏭 多模态大模型驱动 - 焊接工艺参数优化系统")
st.markdown("---") # 这是 Streamlit 的正确分割线写法

col1, col2 = st.columns(2)

with col1:
    st.subheader("🚀 核心工艺参数预测")
    curr, volt, spd, conf = calculate_welding_params(material_type, thickness, method)
    
    st.metric("焊接电流 (A)", f"{curr} A")
    st.metric("电弧电压 (V)", f"{volt} V")
    st.metric("焊接速度 (mm/min)", f"{spd} mm/min")

with col2:
    st.subheader("⚖️ 质量判定与 RAG 校验")
    st.progress(conf)
    st.write(f"预测合格概率: **{conf*100}%**")
    st.info(f"📌 **RAG 检索建议:** 针对 {material_type}，请确保层间温度 < 150°C。")

# 5. 反馈环
st.markdown("---")
st.subheader("🔄 生产-反馈闭环 (RLHF)")
with st.expander("录入生产反馈"):
    fb_col1, fb_col2 = st.columns(2)
    actual = fb_col1.selectbox("实际结果", ["合格", "气孔", "未熔合"])
    if st.button("提交反馈"):
        st.success("数据已同步至增量微调队列！")
