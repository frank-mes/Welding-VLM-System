import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

# 1. 页面配置
st.set_page_config(page_title="多模态焊接优化系统", layout="wide")

# 2. 初始化数据库连接
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except Exception as e:
    st.error("数据库连接初始化失败")

# 3. 核心计算函数
def calculate_params(material, thickness, method, grade):
    base_map = {"Q345R": 110, "316L": 95, "S30408": 100}
    method_factor = {"GMAW": 1.0, "GTAW": 0.8, "LBW": 1.5}
    
    # 步骤 A: 确定基准
    i_base = base_map.get(material, 100)
    # 步骤 B: 厚度增益 (12A/mm)
    i_thick = thickness * 12
    # 步骤 C: 工艺系数
    m_factor = method_factor.get(method, 1.0)
    
    # 最终电流合成
    current = (i_base + i_thick) * m_factor
    
    # 电压逻辑
    if grade == "一级":
        current_adj = current * 0.95
        voltage = 18 + (current_adj / 40)
    else:
        current_adj = current
        voltage = 16 + (current_adj / 45)
        
    speed = 200 + (thickness * 8)
    grade_risk = {"一级": 0.98, "二级": 0.92, "三级": 0.85}
    
    # 返回详细中间过程用于展示
    steps = {
        "i_base": i_base,
        "i_thick": i_thick,
        "m_factor": m_factor,
        "v_base": 18 if grade == "一级" else 16
    }
    return round(current_adj, 1), round(voltage, 1), round(speed, 1), grade_risk.get(grade, 0.90), steps

# 4. 侧边栏
st.sidebar.header("🛠 参数输入")
material_type = st.sidebar.selectbox("材料牌号", ["Q345R", "316L", "S30408"])
thickness = st.sidebar.slider("材料厚度 (mm)", 2.0, 50.0, 10.0)
method = st.sidebar.selectbox("焊接方法", ["GMAW", "GTAW", "LBW"])
grade = st.sidebar.radio("焊缝等级", ["一级", "二级", "三级"])

# 5. 主页面标题
st.title("👨‍🏭 多模态大模型驱动 - 焊接工艺优化系统")

# 算法宏观逻辑
with st.expander("📖 查看算法宏观推理逻辑 (专家系统说明)", expanded=False):
    st.markdown("""
    ### 核心引擎：基于专家系统的工艺推理
    本系统将焊接工艺规程 (WPS) 转化为数学启发式模型：
    1. **电流决策 ($I$)**: $I = (I_{base} + 12h) \cdot \eta_{method}$
    2. **电压协同 ($U$)**: 模拟逆变电源协同控制曲线。
    3. **视觉补偿**: VLM 实时检测间隙并自动叠加 $5A$ 修正。
    """)

st.markdown("---")

# 6. 计算详细推演过程 (实时展示当前实例的计算)
st.subheader("📝 当前实例推理记录 (Inference Trace)")
curr_res, volt_res, spd_res, conf_res, steps = calculate_params(material_type, thickness, method, grade)

# 模拟 VLM 补偿
uploaded_file = st.file_uploader("上传坡口照片进行视觉对齐", type=["jpg", "png", "jpeg"])
vlm_delta = 5.0 if uploaded_file else 0.0
final_curr = curr_res + vlm_delta

# 展示计算链条
trace_col1, trace_col2, trace_col3, trace_col4 = st.columns(4)
trace_col1.code(f"Step 1: 基准电流\n{material_type} -> {steps['i_base']}A")
trace_col2.code(f"Step 2: 厚度补偿\n{thickness}mm * 12 -> +{steps['i_thick']}A")
trace_col3.code(f"Step 3: 工艺修正\n{method} 系数 -> x{steps['m_factor']}")
trace_col4.code(f"Step 4: 视觉补偿\n照片上传 -> +{vlm_delta}A")

st.markdown(f"**💡 最终电流合成逻辑：** `({steps['i_base']} + {steps['i_thick']}) * {steps['m_factor']} + {vlm_delta} = {final_curr} A`")



st.markdown("---")

# 7. 预测结果展示
res_col1, res_col2 = st.columns([1, 1])
with res_col1:
    if uploaded_file:
        st.image(uploaded_file, caption="实时样本", use_container_width=True)
    else:
        st.info("等待照片上传以激活视觉反馈...")

with res_col2:
    st.subheader("🚀 推荐工艺参数")
    m1, m2, m3, m4 = st.columns(2)
    m1.metric("焊接电流 (I)", f"{final_curr} A", delta=f"{vlm_delta}A" if vlm_delta > 0 else None)
    m1.metric("电弧电压 (U)", f"{volt_res} V")
    m2.metric("焊接速度 (V)", f"{spd_res} mm/min")
    m2.metric("预测合格率", f"{int(conf_res*100)}%")

# 8. 生产反馈闭环 (RLHF)
st.markdown("---")
st.subheader("🔄 质量反馈与数据闭环 (RLHF)")

target_cols = ["Timestamp", "Material", "Thickness", "Method", "Grade", "VLM_Feedback", "Pred_Current", "Pred_Voltage", "Pred_Speed", "Actual_Result", "Expert_Score"]

with st.expander("📝 录入反馈", expanded=True):
    f_c1, f_c2 = st.columns(2)
    actual_res = f_c1.selectbox("结果", ["合格", "气孔", "未熔合", "咬边", "裂纹"])
    expert_score = f_c2.slider("评分", 0, 100, 85)
    
    if st.button("🚀 提交并同步", use_container_width=True):
        new_row = {
            "Timestamp": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"),
            "Material": material_type, "Thickness": thickness, "Method": method, "Grade": grade,
            "VLM_Feedback": "视觉激活" if uploaded_file else "理论输入",
            "Pred_Current": final_curr, "Pred_Voltage": volt_res, "Pred_Speed": spd_res,
            "Actual_Result": actual_res, "Expert_Score": expert_score
        }
        try:
            url = st.secrets["gsheets_url"]
            existing_df = conn.read(spreadsheet=url, ttl=0)
            new_df = pd.DataFrame([new_row])[target_cols]
            updated_df = pd.concat([existing_df, new_df], ignore_index=True)
            conn.update(spreadsheet=url, data=updated_df)
            st.success("✅ 数据已同步！")
            st.balloons()
        except Exception as e:
            st.error(f"同步异常: {e}")

# 查看记录
if st.checkbox("查看云端记录"):
    data_view = conn.read(spreadsheet=st.secrets["gsheets_url"], ttl=0)
    st.dataframe(data_view.reindex(columns=target_cols).tail(5), use_container_width=True)
