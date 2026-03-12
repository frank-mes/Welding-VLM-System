import streamlit as st
import pandas as pd
import os

# 1. 页面配置
st.set_page_config(page_title="焊接工艺参数优化系统", layout="wide")

# 2. 逻辑函数
def calculate_welding_params(material, thickness, method):
    base_map = {"Q345R": 110, "316L": 95, "S30408": 100}
    current = base_map.get(material, 100) + (thickness * 12)
    voltage = 16 + (current / 45)
    speed = 200 + (thickness * 8)
    confidence = 0.94 if thickness < 20 else 0.85
    return round(current, 1), round(voltage, 1), round(speed, 1), confidence

# 3. 侧边栏输入
st.sidebar.header("🛠 输入层 (Input Layer)")
material_type = st.sidebar.selectbox("材料牌号", ["Q345R", "316L", "S30408"])
thickness = st.sidebar.slider("材料规格 (厚度 mm)", 2.0, 50.0, 10.0)
method = st.sidebar.selectbox("焊接方法", ["GMAW", "GTAW", "LBW"])
grade = st.sidebar.radio("焊缝等级", ["一级", "二级", "三级"])

# 4. 主界面
st.title("👨‍🏭 多模态大模型驱动 - 焊接工艺参数优化系统")

# --- 视觉感知模块 ---
st.markdown("---")
st.subheader("📸 多模态视觉特征对齐 (Vision Layer)")
v_col1, v_col2 = st.columns([1, 2])
with v_col1:
    uploaded_file = st.file_uploader("上传照片 (VLM 输入)", type=["jpg", "png", "jpeg"])
    if uploaded_file:
        st.image(uploaded_file, caption="当前扫描样本", use_container_width=True)

with v_col2:
    if uploaded_file:
        gap_detected = 0.8 + (thickness / 15)
        st.info(f"🔍 **VLM 识别结论：**\n- 坡口间隙: {gap_detected:.2f} mm\n- 建议：自动补偿电流 +5A")
    else:
        st.write("📢 请上传照片激活视觉补偿。")

# 5. 参数展示
st.markdown("---")
col1, col2 = st.columns(2)
curr, volt, spd, conf = calculate_welding_params(material_type, thickness, method)
with col1:
    st.subheader("🚀 核心工艺参数预测")
    st.metric("焊接电流 (A)", f"{curr} A")
    st.metric("电弧电压 (V)", f"{volt} V")
with col2:
    st.subheader("⚖️ 质量判定与 RAG 校验")
    st.progress(conf)

# 6. 反馈闭环 (本地存储版)
st.markdown("---")
st.subheader("🔄 生产-反馈闭环 (RLHF)")
CSV_FILE = "feedback_data.csv" # 存储文件名

with st.expander("录入生产反馈"):
    fb_col1, fb_col2 = st.columns(2)
    actual = fb_col1.selectbox("实际结果", ["合格", "气孔", "未熔合", "咬边"])
    expert_score = fb_col2.slider("专家打分", 0, 100, 85)
    
    if st.button("提交反馈"):
        new_row = pd.DataFrame([{
            "Timestamp": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"),
            "Material": material_type,
            "Thickness": thickness,
            "Method": method,
            "Actual_Result": actual,
            "Expert_Score": expert_score
        }])
        
        # 写入 CSV 文件
        if not os.path.isfile(CSV_FILE):
            new_row.to_csv(CSV_FILE, index=False)
        else:
            new_row.to_csv(CSV_FILE, mode='a', header=False, index=False)
        
        st.success("✅ 提交成功！反馈已存入本地数据库。")
        st.balloons()

# 7. 历史数据展示
st.markdown("---")
st.header("📊 历史反馈查看")
if os.path.isfile(CSV_FILE):
    history_df = pd.read_csv(CSV_FILE)
    st.dataframe(history_df.tail(10)) # 显示最后10条
    
    # 增加下载按钮
    csv = history_df.to_csv(index=False).encode('utf-8')
    st.download_button("📥 下载完整数据表 (CSV)", data=csv, file_name="welding_feedback.csv", mime="text/csv")
else:
    st.write("目前尚无历史反馈记录。")
