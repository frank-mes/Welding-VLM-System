import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

# 1. 页面配置
st.set_page_config(page_title="多模态焊接优化系统", layout="wide")

# 2. 初始化数据库连接
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except Exception as e:
    st.error("数据库连接初始化失败，请检查 Secrets 配置")

# 3. 核心推理引擎 (逻辑函数化)
def calculate_params(material, thickness, method, grade):
    base_map = {"Q345R": 110, "316L": 95, "S30408": 100}
    method_factor = {"GMAW": 1.0, "GTAW": 0.8, "LBW": 1.5}
    
    # A. 确定基准
    i_base = base_map.get(material, 100)
    # B. 厚度增益 (12A/mm)
    i_thick = thickness * 12
    # C. 工艺系数
    m_factor = method_factor.get(method, 1.0)
    
    # 初步电流计算
    current = (i_base + i_thick) * m_factor
    
    # D. 等级修正
    grade_mod_val = 0.95 if grade == "一级" else 1.0
    current_adj = current * grade_mod_val
    
    # 电压协同
    voltage = (18 + (current_adj / 40)) if grade == "一级" else (16 + (current_adj / 45))
    
    speed = 200 + (thickness * 8)
    grade_risk = {"一级": 0.98, "二级": 0.92, "三级": 0.85}
    
    steps = {
        "i_base": i_base,
        "i_thick": i_thick,
        "m_factor": m_factor,
        "grade_mod": grade_mod_val
    }
    return round(current_adj, 1), round(voltage, 1), round(speed, 1), grade_risk.get(grade, 0.90), steps

# 4. 侧边栏：参数输入层
st.sidebar.header("🛠 工艺特征输入")
material_type = st.sidebar.selectbox("材料牌号", ["Q345R", "316L", "S30408"])
thickness = st.sidebar.slider("材料厚度 (mm)", 2.0, 50.0, 10.0)
method = st.sidebar.selectbox("焊接方法", ["GMAW", "GTAW", "LBW"])
grade = st.sidebar.radio("焊缝等级", ["一级", "二级", "三级"])

# 5. 主页面头部
st.title("👨‍🏭 多模态大模型驱动 - 焊接工艺优化系统")
st.markdown("---")

# 6. 计算详细推演轨迹 (Traceability)
# 预先计算结果
curr_res, volt_res, spd_res, conf_res, steps = calculate_params(material_type, thickness, method, grade)

st.subheader("📝 专家系统推演轨迹 (Inference Trace)")
t_col1, t_col2 = st.columns([1, 1])

# 视觉输入模拟
with t_col1:
    uploaded_file = st.file_uploader("上传坡口实时照片 (激活 VLM 补偿)", type=["jpg", "png", "jpeg"])
    vlm_delta = 5.0 if uploaded_file else 0.0
    final_curr = curr_res + vlm_delta
    if uploaded_file:
        st.image(uploaded_file, caption="视觉采样样本", use_container_width=True)
    else:
        st.info("📢 等待图像输入以触发视觉补偿层 (+5A)")

# 具体的计算步骤展示
with t_col2:
    st.write("**当前实例逻辑拆解：**")
    st.info(f"1. **基准确定**: {material_type} 基准电流 = {steps['i_base']}A")
    st.info(f"2. **板厚补偿**: {thickness}mm × 12 = +{steps['i_thick']}A")
    st.info(f"3. **工艺修正**: {method} 系数 = {steps['m_factor']} | 等级修正 = {steps['grade_mod']}")
    st.success(f"4. **视觉对齐**: 照片对齐补偿 = +{vlm_delta}A")
    
    # 展示核心公式
    formula = f"(({steps['i_base']} + {steps['i_thick']}) × {steps['m_factor']} × {steps['grade_mod']}) + {vlm_delta} = **{final_curr} A**"
    st.code(f"最终预测电流计算式：\n{formula}", language="text")



st.markdown("
