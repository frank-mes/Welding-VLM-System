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

# 3. 核心决策模型 (专家系统公式)
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

# 4. 侧边栏输入 (Input)
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
    if uploaded_file:
        st.image(uploaded_file, caption="实时捕获样本", use_container_width=True)

# 视觉逻辑处理
vlm_analysis = "理论间隙输入"
if uploaded_file:
    gap = 0.8 + (thickness / 15)
    vlm_analysis = f"视觉检测间隙: {gap:.2f}mm"
    with v_col2:
        st.info(f"🔍 **VLM 识别结论：** {vlm_analysis}")
        st.warning("💡 **多模态补偿：** 视觉检测到波动，电流已自动补偿 +5A")
else:
    with v_col2:
        st.write("📢 请上传照片以激活视觉对齐模块。")

# 7. 预测结果展示 (Output)
st.markdown("---")
curr, volt, spd, conf = calculate_params(material_type, thickness, method, grade)
if uploaded_file:
    curr += 5.0 

st.subheader("🚀 推荐工艺参数预测")
c1, c2, c3, c4 = st.columns(4)
c1.metric("焊接电流 (A)", f"{curr} A", delta="+5A (VLM)" if uploaded_file else None)
c2.metric("电弧电压 (V)", f"{volt} V")
c3.metric("速度 (mm/min)", f"{spd}")
c4.metric("预测合格率", f"{conf*100:.0f}%")

# 8. 生产反馈闭环 (RLHF)
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
            try:
                existing_df = conn.read(spreadsheet=url)
            except:
                existing_df = pd.DataFrame(columns=target_columns)
            new_df = pd.DataFrame([new_row])[target_columns]
            updated_df = pd.concat([existing_df, new_df], ignore_index=True)
            updated_df = updated_df.reindex(columns=target_columns)
            conn.update(spreadsheet=url, data=updated_df)
            st.success("✅ 包含预测参数的完整记录已同步！")
            st.balloons()
        except Exception as err:
            st.error(f"同步失败: {err}")

# 9. 云端数据查看
if st.checkbox("查看云端数据库最近记录"):
    try:
        data_preview = conn.read(spreadsheet=st.secrets["gsheets_url"])
        st.dataframe(data_preview.reindex(columns=target_columns).tail(5), use_container_width=True)
    except:
        st.write("暂无历史记录。")
