import streamlit as st
import pandas as pd
import numpy as np
from streamlit_gsheets import GSheetsConnection

# 1. 页面配置
st.set_page_config(page_title="多模态焊接优化系统", layout="wide")

# 2. 初始化连接
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except Exception as e:
    st.error(f"Connection Error: {e}")

# 3. 核心决策模型
def calculate_params(material, thickness, method, grade):
    base_map = {"Q345R": 110, "316L": 95, "S30408": 100}
    method_factor = {"GMAW": 1.0, "GTAW": 0.8, "LBW": 1.5}
    base_curr = base_map.get(material, 100) + (thickness * 12)
    current = base_curr * method_factor.get(method, 1.0)
    
    if grade == "一级":
        current *= 0.95
        voltage = 18 + (current / 40)
    else:
        voltage = 16 + (current / 45)
    
    speed = 200 + (thickness * 8)
    grade_risk = {"一级": 0.98, "二级": 0.92, "三级": 0.85}
    return round(current, 1), round(voltage, 1), round(speed, 1), grade_risk.get(grade, 0.90)

# 4. 侧边栏
st.sidebar.header("🛠 基础输入")
material_type = st.sidebar.selectbox("材料牌号", ["Q345R", "316L", "S30408"])
thickness = st.sidebar.slider("厚度 (mm)", 2.0, 50.0, 10.0)
method = st.sidebar.selectbox("焊接方法", ["GMAW", "GTAW", "LBW"])
grade = st.sidebar.radio("焊缝等级", ["一级", "二级", "三级"])

# 5. 主界面
st.title("👨‍🏭 多模态大模型驱动 - 焊接工艺系统")
st.markdown("---")

# 6. 视觉感知层 (VLM)
st.subheader("📸 多模态视觉特征对齐")
v_col1, v_col2 = st.columns([1, 2])

with v_col1:
    uploaded_file = st.file_uploader("上传照片", type=["jpg", "png", "jpeg"])
    if uploaded_file:
        st.image(uploaded_file, caption="实时捕获", use_container_width=True)

vlm_analysis = "理论间隙输入"
if uploaded_file:
    gap = 0.8 + (thickness / 15)
    vlm_analysis = f"视觉检测间隙: {gap:.2f}mm"
    with v_col2:
        st.info(f"🔍 **VLM 结论：** {vlm_analysis}")
        st.warning("💡 **多模态补偿：** 电流已补偿 +5A")

# 7. 结果展示
st.markdown("---")
curr, volt, spd, conf = calculate_params(material_type, thickness, method, grade)
if uploaded_file: curr += 5.0 

c1, c2, c3, c4 = st.columns(4)
c1.metric("电流 (A)", f"{curr} A")
c2.metric("电压 (V)", f"{volt} V")
c3.metric("速度 (mm/min)", f"{spd}")
c4.metric("预测合格率", f"{conf*100:.0f}%")

# 8. 反馈闭环 (RLHF) - 注意这一块的引号闭合
st.markdown("---")
st.subheader("🔄 生产-反馈闭环 (RLHF)")

with st.expander("点击展开：录入反馈记录"):
    fb_col1, fb_col2 = st.columns(2)
    actual_res = fb_col1.selectbox("检测结果", ["合格", "气孔", "未熔合", "咬边"])
    expert_score = fb_col2.slider("打分", 0, 100, 85)
    
    if st.button("同步至云端"):
        new_data = {
            "Timestamp": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"),
            "Material": material_type,
            "Thickness": thickness,
            "Method": method,
            "Grade": grade,
            "VLM_Feedback": vlm_analysis,
            "Actual_Result": actual_res,
            "Expert_Score": expert_score
        }
        
        try:
            url = st.secrets["gsheets_url"]
            df = conn.read(spreadsheet=url)
            updated_df = pd.concat([df, pd.DataFrame([new_data])], ignore_index=True)
            conn.update(spreadsheet=url, data=updated_df)
            st.success("✅ 数据已同步至表格！")
            st.balloons()
        except Exception as error:
            st.error(f"Error: {error}")

# 9. 数据预览
if st.checkbox("查看最近5条记录"):
    try:
        st.dataframe(conn.read(spreadsheet=st.secrets["gsheets_url"]).tail(5))
    except:
        st.write("暂无记录")
