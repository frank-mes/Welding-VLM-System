import streamlit as st
import pandas as pd
import numpy as np

# 页面配置
st.set_page_config(page_title="多模态焊接工艺优化系统", layout="wide")

## --- 模拟 RAG 知识库与模型逻辑 ---
def mock_vlm_predict(material, thickness, method):
    # 这里模拟 VLM 模型对 PQR/WPS 数据的推理
    base_current = 120 if material == "Q345R" else 100
    current = base_current + (thickness * 15)
    voltage = 18 + (current / 40)
    speed = 250 + (thickness * 10)
    confidence = 0.92
    return round(current, 1), round(voltage, 1), round(speed, 1), confidence

## --- 侧边栏：输入层 ---
st.sidebar.header("🛠 输入层 (Input Layer)")
material_type = st.sidebar.selectbox("材料牌号", ["Q345R", "316L", "S30408"])
thickness = st.sidebar.slider("材料规格 (厚度 mm)", 2.0, 50.0, 10.0)
method = st.sidebar.selectbox("焊接方法", ["GMAW (熔化极气体保护焊)", "GTAW (钨极氩弧焊)", "LBW (激光焊)"])
grade = st.sidebar.radio("焊缝等级", ["一级", "二级", "三级"])

# 进阶预留：图像上传
uploaded_file = st.sidebar.file_uploader("上传坡口/熔池图像 (进阶预留)", type=['png', 'jpg'])

## --- 主界面：输出与交互 ---
st.title("👨‍焊 多模态大模型驱动 - 焊接工艺参数优化系统")
st.info(f"当前策略：基于 LoRA 微调的 VLM 架构 + GB/T 规范 RAG 检索")

col1, col2 = st.columns(2)

with col1:
    st.subheader("🚀 核心工艺参数预测")
    curr, volt, spd, conf = mock_vlm_predict(material_type, thickness, method)
    
    st.metric("焊接电流 (A)", f"{curr} A")
    st.metric("电弧电压 (V)", f"{volt} V")
    st.metric("焊接速度 (mm/min)", f"{spd} mm/min")

with col2:
    st.subheader("⚖️ 质量判定与 RAG 校验")
    st.progress(conf)
    st.write(f"合格预测概率: **{conf*100}%**")
    
    # 模拟 RAG 检索行业标准
    st.warning(f"📌 **RAG 规范提醒 (GB/T 3375):** \n针对 {material_type} {thickness}mm 坡口，建议层间温度控制在 150°C 以下。")

---

### 3. 闭环反馈窗口 (反馈与迭代)
st.divider()
st.subheader("🔄 生产-反馈闭环 (RLHF 接口)")
with st.expander("录入实际焊接反馈以优化模型"):
    fb_col1, fb_col2 = st.columns(2)
    actual_res = fb_col1.selectbox("探伤结果 (RT/UT)", ["合格", "未熔合", "气孔", "裂纹"])
    expert_score = fb_col2.slider("专家打分 (Reward Model)", 0, 100, 85)
    if st.button("提交反馈数据"):
        st.success("数据已加入增量训练队列，Loss 已更新。")
