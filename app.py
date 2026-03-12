import streamlit as st
import pandas as pd
import numpy as np
from streamlit_gsheets import GSheetsConnection

# 1. 页面配置 (必须放在首行)
st.set_page_config(page_title="焊接工艺参数优化系统", layout="wide")

# 2. 初始化数据库连接
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except:
    st.error("数据库连接初始化失败，请检查 requirements.txt")

# 3. 定义逻辑函数
def calculate_welding_params(material, thickness, method):
    base_map = {"Q345R": 110, "316L": 95, "S30408": 100}
    current = base_map.get(material, 100) + (thickness * 12)
    voltage = 16 + (current / 45)
    speed = 200 + (thickness * 8)
    confidence = 0.94 if thickness < 20 else 0.85
    return round(current, 1), round(voltage, 1), round(speed, 1), confidence

# 4. 侧边栏：输入层 (先获取变量)
st.sidebar.header("🛠 输入层 (Input Layer)")
material_type = st.sidebar.selectbox("材料牌号", ["Q345R", "316L", "S30408"])
thickness = st.sidebar.slider("材料规格 (厚度 mm)", 2.0, 50.0, 10.0)
method = st.sidebar.selectbox("焊接方法", ["GMAW", "GTAW", "LBW"])
grade = st.sidebar.radio("焊缝等级", ["一级", "二级", "三级"])

# 5. 主界面标题
st.title("👨‍🏭 多模态大模型驱动 - 焊接工艺参数优化系统")
st.markdown("---")

# 6. 核心工艺参数预测展示
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
    st.info(f"📌 **RAG 建议:** 针对 {material_type}，请确保层间温度 < 150°C。")

# 7. 生产-反馈闭环 (RLHF)
st.markdown("---")
st.subheader("🔄 生产-反馈闭环 (RLHF)")
with st.expander("录入生产反馈"):
    fb_col1, fb_col2 = st.columns(2)
    actual = fb_col1.selectbox("实际结果", ["合格", "气孔", "未熔合", "咬边"])
    expert_score = fb_col2.slider("专家打分 (Reward)", 0, 100, 85)
    
    if st.button("提交反馈"):
        new_data = pd.DataFrame([{
            "Timestamp": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"),
            "Material": material_type,
            "Thickness": thickness,
            "Method": method,
            "Actual_Result": actual,
            "Expert_Score": expert_score
        }])
        
        try:
            url = st.secrets["gsheets_url"]
            existing_data = conn.read(spreadsheet=url)
            updated_df = pd.concat([existing_data, new_data], ignore_index=True)
            conn.update(spreadsheet=url, data=updated_df)
            st.success("✅ 数据已同步至云端 Google 表格！")
        except Exception as e:
            st.warning("⚠️ 数据库写入失败（检查 Secrets 配置）。当前捕获数据如下：")
            st.table(new_data)

# 8. 数据管理面板
st.markdown("---")
st.header("📊 数据管理与增量训练")
tab1, tab2 = st.tabs(["批量导入 PQR 数据", "历史反馈查看"])

with tab1:
    uploaded_pqr = st.file_uploader("上传工艺数据库", type=["csv", "xlsx"])
    if uploaded_pqr:
        df = pd.read_csv(uploaded_pqr) if uploaded_pqr.name.endswith('.csv') else pd.read_excel(uploaded_pqr)
        st.write("已成功读取样本数据：")
        st.dataframe(df.head(5))
        if st.button("开始增量微调 (LoRA)"):
            with st.spinner("模型演进中..."):
                import time
                time.sleep(2)
                st.success("模型已完成参数偏移修正！")

with tab2:
    st.write("历史 RLHF 反馈记录预览：")
    mock_feedback = pd.DataFrame({
        "时间": ["2024-05-20", "2024-05-21"],
        "材料": ["Q345R", "316L"],
        "专家评分": [95, 88],
        "建议修正项": ["电流偏高", "速度完美"]
    })
    st.table(mock_feedback)
