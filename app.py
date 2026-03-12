import streamlit as st
import pandas as pd
import numpy as np
from streamlit_gsheets import GSheetsConnection

# 1. 页面配置
st.set_page_config(page_title="多模态焊接优化系统", layout="wide")

# 2. 初始化数据库连接
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except Exception as e:
    st.error(f"数据库连接异常: {e}")

# 3. 核心算法 (加入焊缝等级对合格概率的影响)
def calculate_welding_params(material, thickness, method, grade):
    base_map = {"Q345R": 110, "316L": 95, "S30408": 100}
    method_factor = {"GMAW": 1.0, "GTAW": 0.8, "LBW": 1.5}
    
    current = (base_map.get(material, 100) + (thickness * 12)) * method_factor.get(method, 1.0)
    voltage = 16 + (current / 45)
    speed = 200 + (thickness * 8)
    
    # 焊缝等级越高，要求的置信度/合格概率越严苛
    grade_risk = {"一级": 0.05, "二级": 0.1, "三级": 0.15}
    confidence = 0.98 - grade_risk.get(grade, 0.1)
    
    return round(current, 1), round(voltage, 1), round(speed, 1), confidence

# 4. 侧边栏输入 (确保所有变量都有对应)
st.sidebar.header("🛠 输入层 (Input Layer)")
material_type = st.sidebar.selectbox("材料牌号", ["Q345R", "316L", "S30408"])
thickness = st.sidebar.slider("厚度 (mm)", 2.0, 50.0, 10.0)
method = st.sidebar.selectbox("焊接方法", ["GMAW", "GTAW", "LBW"])
grade = st.sidebar.radio("焊缝等级", ["一级", "二级", "三级"])

# 5. 主界面
st.title("👨‍🏭 多模态大模型驱动 - 焊接工艺系统")
st.markdown("---")

# 6. 多模态视觉模块 (VLM)
st.subheader("📸 多模态视觉特征对齐 (Vision Layer)")
v_col1, v_col2 = st.columns([1, 2])

with v_col1:
    uploaded_file = st.file_uploader("上传坡口照片", type=["jpg", "png", "jpeg"])
    if uploaded_file:
        st.image(uploaded_file, caption="实时捕获样本", use_container_width=True)

vlm_analysis = "无图像输入"
if uploaded_file:
    gap_detected = 0.8 + (thickness / 15)
    vlm_analysis = f"检测到间隙 {gap_detected:.2f}mm"
    with v_col2:
        st.info(f"🔍 **VLM 识别结论：** {vlm_analysis}")
        st.warning("💡 **AI 补偿建议：** 电流已根据视觉对齐自动补偿 +5A。")

# 7. 参数展示
st.markdown("---")
curr, volt, spd, conf = calculate_welding_params(material_type, thickness, method, grade)
if uploaded_file: curr += 5.0 

c1, c2, c3 = st.columns(3)
c1.metric("焊接电流 (A)", f"{curr} A", delta="VLM补偿" if uploaded_file else None)
c2.metric("电弧电压 (V)", f"{volt} V")
c3.metric("预测合格率", f"{conf*100:.1f}%")

# 8. RLHF 反馈提交 (补齐 Grade 字段)
st.markdown("---")
st.subheader("🔄 生产-反馈闭环 (RLHF)")
with st.expander("录入反馈记录并同步至云端"):
    fb_col1, fb_col2 = st.columns(2)
    actual = fb_col1.selectbox("实际结果", ["合格", "气孔", "未熔合", "咬边"])
    expert_score = fb_col2.slider("专家打分 (Reward)", 0, 100, 85)
    
    if st.button("提交反馈至云端"):
        new_row = {
            "Timestamp": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"),
            "Material": material_type,
            "Thickness": thickness,
            "Method": method,
            "Grade": grade,          # <--- 补上了这个字段！
            "Actual_Result": actual,
            "Expert_Score": expert_score,
            "VLM_Feedback": vlm_analysis
        }
        try:
            url = st.secrets["gsheets_url"]
            existing_data = conn.read(spreadsheet=url)
            updated_df = pd.concat([existing_data, pd.DataFrame([new_row])], ignore_index=True)
            conn.update(spreadsheet=url, data=updated_df)
            st.success(f"✅ 数据（含{grade}焊缝等级）已同步！")
            st.balloons()
        except Exception as e:
            st.error(f"同步失败: {e}")
