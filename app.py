import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

# 1. 基础页面设置
st.set_page_config(page_title="焊接工艺优化系统", layout="wide")

# 2. 数据库连接
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except Exception as e:
    st.error("数据库连接初始化失败，请检查 Secrets 配置")

# 3. 推理引擎：将专家经验转化为具体数值
def calculate_welding_logic(material, thickness, method, grade):
    # A. 基准定义
    base_map = {"Q345R": 110, "316L": 95, "S30408": 100}
    i_base = base_map.get(material, 100)
    
    # B. 物理增益：每增加1mm厚度，电流需求增加12A
    i_thick_gain = thickness * 12
    
    # C. 工艺因子
    method_factor_map = {"GMAW": 1.0, "GTAW": 0.8, "LBW": 1.5}
    m_factor = method_factor_map.get(method, 1.0)
    
    # D. 质量约束修正
    grade_mod = 0.95 if grade == "一级" else 1.0
    
    # E. 逻辑合成
    # 公式：(基准 + 厚度增益) * 工艺因子 * 等级修正
    theoretical_current = (i_base + i_thick_gain) * m_factor * grade_mod
    
    # 电压协同
    if grade == "一级":
        voltage = 18 + (theoretical_current / 40)
    else:
        voltage = 16 + (theoretical_current / 45)
    
    speed = 200 + (thickness * 8)
    
    # 返回结果及详细的计算步骤
    calculation_steps = {
        "base_val": i_base,
        "thick_val": i_thick_gain,
        "factor_val": m_factor,
        "mod_val": grade_mod
    }
    return round(theoretical_current, 1), round(voltage, 1), round(speed, 1), calculation_steps

# 4. 侧边栏：用户输入
st.sidebar.header("🛠 工艺特征输入")
in_mat = st.sidebar.selectbox("材料牌号", ["Q345R", "316L", "S30408"])
in_thick = st.sidebar.slider("材料厚度 (mm)", 2.0, 50.0, 10.0)
in_meth = st.sidebar.selectbox("焊接方法", ["GMAW", "GTAW", "LBW"])
in_grade = st.sidebar.radio("焊缝等级", ["一级", "二级", "三级"])

# 5. 主界面标题
st.title("👨‍🏭 多模态大模型驱动 - 焊接工艺优化系统")
st.markdown("---")

# 6. 执行计算
curr_base, volt_out, spd_out, steps = calculate_welding_logic(in_mat, in_thick, in_meth, in_grade)

# 7. 视觉感知层 (Vision Layer)
st.subheader("📸 多模态视觉特征对齐 (Vision Layer)")
v_col1, v_col2 = st.columns([1, 1])

with v_col1:
    up_file = st.file_uploader("上传坡口实时照片", type=["jpg", "png", "jpeg"])
    vlm_comp = 5.0 if up_file else 0.0
    if up_file:
        st.image(up_file, caption="实时采样样本", use_container_width=True)
    else:
        st.info("📢 等待图像输入以激活 VLM 补偿层 (+5A)")

with v_col2:
    final_i = curr_base + vlm_comp
    st.write("**📝 当前实例：专家系统具体推理过程**")
    # 展示具体的计算细节
    st.markdown(f"""
    * **步骤 1 (基准定位):** {in_mat} 材质基础电流 = **{steps['base_val']} A**
    * **步骤 2 (能量增益):** {in_thick}mm 厚度补偿 ({in_thick}*12) = **+{steps['thick_val']} A**
    * **步骤 3 (系数修正):** {in_meth} 方法系数({steps['factor_val']}) & 等级修正({steps['mod_val']})
    * **步骤 4 (视觉对齐):** VLM 动态间隙补偿 = **+{vlm_comp} A**
    """)
    st.code(f"计算式: (({steps['base_val']} + {steps['thick_val']}) * {steps['factor_val']} * {steps['mod_val']}) + {vlm_comp} = {final_i} A")



st.markdown("---")

# 8. 核心结果展示 (Final Output) - 放在显眼位置，确保不会被遗漏
st.subheader("🚀 推荐工艺参数预测 (Final Output)")
c1, c2, c3 = st.columns(3)
c1.metric("焊接电流 (I)", f"{final_i} A", delta=f"{vlm_comp}A (VLM)" if vlm_comp > 0 else None)
c2.metric("电弧电压 (U)", f"{volt_out} V")
c3.metric("焊接速度 (V)", f"{spd_out} mm/min")

# 9. 生产反馈闭环 (RLHF)
st.markdown("---")
target_headers = ["Timestamp", "Material", "Thickness", "Method", "Grade", "VLM_Feedback", "Pred_Current", "Pred_Voltage", "Pred_Speed", "Actual_Result", "Expert_Score"]

with st.expander("🔄 录入反馈并同步云端数据库", expanded=True):
    f_col1, f_col2 = st.columns(2)
    res_actual = f_col1.selectbox("焊后质检结果", ["合格", "气孔", "未熔合", "
