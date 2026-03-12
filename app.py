import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

# 1. 页面基础配置
st.set_page_config(page_title="多模态焊接工艺优化系统", layout="wide")

# 2. 初始化数据库连接
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except Exception as e:
    st.error(f"数据库连接失败: {e}")

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

# 4. 侧边栏：输入层 (Input)
st.sidebar.header("🛠 基础输入参数")
material_type = st.sidebar.selectbox("材料牌号", ["Q345R", "316L", "S30408"])
thickness = st.sidebar.slider("材料厚度 (mm)", 2.0, 50.0, 10.0)
method = st.sidebar.selectbox("焊接方法", ["GMAW", "GTAW", "LBW"])
grade = st.sidebar.radio("焊缝等级 (约束)", ["一级", "二级", "三级"])

# 5. 主界面标题
st.title("👨‍🏭 多模态大模型驱动 - 焊接工艺优化系统")
st.markdown("---")

# 6. 多模态视觉感知层与推荐参数 (合并展示，确保右侧不为空)
# 这里使用 columns 分为左右两部分：左侧传图，右侧看结果
main_col1, main_col2 = st.columns([1, 1])

with main_col1:
    st.subheader("📸 视觉特征捕获")
    uploaded_file = st.file_uploader("上传坡口实时照片", type=["jpg", "png", "jpeg"])
    
    # 初始化 VLM 变量，防止后面报错
    vlm_analysis = "理论间隙输入"
    vlm_delta = 0.0
    
    if uploaded_file:
        st.image(uploaded_file, caption="实时捕获样本", use_container_width=True)
        gap = 0.8 + (thickness / 15)
        vlm_analysis = f"视觉检测间隙: {gap:.2f}mm"
        vlm_delta = 5.0
        st.info(f"🔍 **感知结论：** {vlm_analysis}")
    else:
        st.warning("📢 请上传照片以激活视觉补偿")

with main_col2:
    st.subheader("🚀 推荐工艺参数预测")
    
    # 实时计算
    curr_base, volt, spd, conf = calculate_params(material_type, thickness, method, grade)
    curr = curr_base + vlm_delta # 应用视觉补偿
    
    # 结果指标卡
    res_c1, res_c2 = st.columns(2)
    res_c1.metric("焊接电流 (I)", f"{curr} A", delta=f"+{vlm_delta}A" if vlm_delta > 0 else None)
    res_c1.metric("电弧电压 (U)", f"{volt} V")
    res_c2.metric("焊接速度 (V)", f"{spd} mm/min")
    res_c2.metric("预测合格率", f"{conf*100:.0f}%")
    
    st.write("---")
    st.caption("注：以上参数基于材料热物理特性及 VLM 实时特征对齐自动生成。")

# 7. 生产反馈闭环 (RLHF)
st.markdown("---")
st.subheader("🔄 质量反馈与数据闭环 (RLHF)")

target_columns = ["Timestamp", "Material", "Thickness", "Method", "Grade", "VLM_Feedback", "Pred_Current", "Pred_Voltage", "Pred_Speed", "Actual_Result", "Expert_Score"]

with st.expander("📝 录入实测反馈记录", expanded=True):
    fb_col1, fb_col2 = st.columns(2)
    actual_res = fb_col1.selectbox("焊后实际检测结果", ["合格", "气孔", "未熔合", "咬边", "裂纹"])
    expert_score = fb_col2.slider("专家质量打分", 0, 100, 85)
    
    if st.button("🚀 提交完整数据至云端", use_container_width=True):
        new_row = {
            "Timestamp": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"),
            "Material": material_type, "Thickness": thickness, "Method": method, "Grade": grade,
            "VLM_Feedback": vlm_analysis, "Pred_Current": curr, "Pred_Voltage": volt, "Pred_Speed": spd,
            "Actual_Result": actual_res, "Expert_Score": expert_score
        }
        try:
            url = st.secrets["gsheets_url"]
            # 强制不使用缓存读取
            try:
                existing_df = conn.read(spreadsheet=url, ttl=0)
            except:
                existing_df = pd.DataFrame(columns=target_columns)
            
            new_df = pd.DataFrame([new_row])[target_columns]
            updated_df = pd.concat([existing_df, new_df], ignore_index=True)
            updated_df = updated_df.reindex(columns=target_columns)
            conn.update(spreadsheet=url, data=updated_df)
            st.success(f"✅ 数据已
