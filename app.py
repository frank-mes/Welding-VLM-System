import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

# 1. 页面配置
st.set_page_config(page_title="焊接工艺优化系统", layout="wide")

# 2. 初始化数据库连接
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except Exception as e:
    st.error("数据库连接初始化失败，请检查 Secrets 配置")

# 3. 核心推理逻辑
def calculate_params(material, thickness, method, grade):
    # 专家规则库
    base_map = {"Q345R": 110, "316L": 95, "S30408": 100}
    method_factor = {"GMAW": 1.0, "GTAW": 0.8, "LBW": 1.5}
    
    i_base = base_map.get(material, 100)
    i_thick = thickness * 12
    m_factor = method_factor.get(method, 1.0)
    
    # 电流合成与等级修正
    current = (i_base + i_thick) * m_factor
    grade_mod_val = 0.95 if grade == "一级" else 1.0
    current_adj = current * grade_mod_val
    
    # 电压与速度
    if grade == "一级":
        voltage = 18 + (current_adj / 40)
    else:
        voltage = 16 + (current_adj / 45)
    
    speed = 200 + (thickness * 8)
    grade_risk = {"一级": 0.98, "二级": 0.92, "三级": 0.85}
    
    # 导出推理中间步骤
    trace = {
        "base": i_base,
        "thick_add": i_thick,
        "factor": m_factor,
        "mod": grade_mod_val
    }
    return round(current_adj, 1), round(voltage, 1), round(speed, 1), grade_risk.get(grade, 0.90), trace

# 4. 侧边栏：输入特征
st.sidebar.header("🛠 工艺特征输入")
material_type = st.sidebar.selectbox("材料牌号", ["Q345R", "316L", "S30408"])
thickness = st.sidebar.slider("材料厚度 (mm)", 2.0, 50.0, 10.0)
method = st.sidebar.selectbox("焊接方法", ["GMAW", "GTAW", "LBW"])
grade = st.sidebar.radio("焊缝等级", ["一级", "二级", "三级"])

# 5. 主页面布局
st.title("👨‍🏭 多模态大模型驱动 - 焊接工艺优化系统")
st.markdown("---")

# 预执行推理
curr_res, volt_res, spd_res, conf_res, trace = calculate_params(material_type, thickness, method, grade)

# 6. 视觉感知与推理轨迹 (Traceability)
st.subheader("📝 专家系统推演轨迹 (Inference Trace)")
t_col1, t_col2 = st.columns([1, 1])

with t_col1:
    uploaded_file = st.file_uploader("上传坡口实时照片 (激活 VLM 补偿)", type=["jpg", "png", "jpeg"])
    vlm_delta = 5.0 if uploaded_file else 0.0
    final_curr = curr_res + vlm_delta
    if uploaded_file:
        st.image(uploaded_file, caption="视觉采样样本", use_container_width=True)
    else:
        st.info("📢 等待图像输入以触发视觉补偿层 (+5A)")

with t_col2:
    st.write("**当前实例逻辑拆解：**")
    st.info(f"1. 基准确定: {material_type} 基准电流 = {trace['base']}A")
    st.info(f"2. 板厚补偿: {thickness}mm × 12 = +{trace['thick_add']}A")
