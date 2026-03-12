import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

# 1. 基础配置
st.set_page_config(page_title="焊接专家系统", layout="wide")

# 2. 数据库连接
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except Exception:
    st.error("数据库链接异常")

# 3. 核心推演引擎
def get_logic(mat, thick, meth, grade):
    # 专家参数库
    base_i_map = {"Q345R": 110, "316L": 95, "S30408": 100}
    meth_f_map = {"GMAW": 1.0, "GTAW": 0.8, "LBW": 1.5}
    
    # A. 电流推演
    i_b = base_i_map.get(mat, 100)
    i_t = thick * 12
    m_f = meth_f_map.get(meth, 1.0)
    g_m = 0.95 if grade == "一级" else 1.0
    i_res = (i_b + i_t) * m_f * g_m
    
    # B. 电压推演
    v_c = 18 if grade == "一级" else 16
    v_r = 40 if grade == "一级" else 45
    u_res = v_c + (i_res / v_r)
    
    # C. 速度推演
    v_res = 200 + (thick * 8)
    
    # 生成算式文本
    txt_i = f"({i_b} + {i_t}) * {m_f} * {g_m}"
    txt_u = f"{v_c} + ({round(i_res,1)} / {v_r})"
    txt_v = f"200 + ({thick} * 8)"
    
    return i_res, u_res, v_res, txt_i, txt_u, txt_v

# 4. 侧边栏特征输入
st.sidebar.header("🛠 参数输入")
val_mat = st.sidebar.selectbox("材料牌号", ["Q345R", "316L", "S30408"])
val_thick = st.sidebar.slider("材料厚度(mm)", 2.0, 50.0, 10.0)
val_meth = st.sidebar.selectbox("焊接方法", ["GMAW", "GTAW", "LBW"])
val_grade = st.sidebar.radio("质量等级", ["一级", "二级", "三级"])

# 5. 主页面布局
st.title("👨‍🏭 焊接工艺多模态优化系统")

# 宏观逻辑展示
with st.expander("📘 查看宏观专家知识逻辑", expanded=False):
    st.write("1. 热平衡模型：根据厚度补偿热损。")
    st.write("2. 协同控制：电压随电流反馈。")
    st.write("3. 能量修正：LBW/GTAW 系数补偿。")

st.markdown("---")

# 6. 执行计算
i, u, v, exp_i, exp_u, exp_v = get_logic(val_mat, val_thick, val_meth, val_grade)

# 7. 实例推理路径追踪
st.subheader("📝 实例具体计算推导路径")
c1, c2, c3 = st.columns(3)

up_f = st.file_uploader("上传照片(视觉对齐)", type=["jpg", "png", "jpeg"])
v_comp = 5.0 if up_f else 0.0
f_i = round(i + v_comp, 1)

with c1:
    st.info("**电流 (I) 推导**")
    st.code(f"算式: {exp_i}\n视觉: +{v_comp}\n最终: {f_i} A")

with c2:
    st.info("**电压 (U) 推导**")
    st.code(f"算式: {exp_u}\n最终: {round(u, 1)} V")

with c3:
    st.info("**速度 (V) 推导**")
    st.code(f"算式: {exp_v}\n最终: {v} mm/min")



# 8. 核心看板
st.markdown("---")
st.subheader("🚀 推荐结果")
r1, r2, r3 = st.columns(3)
r1.metric("电流", f"{f_i} A", delta=f"{v_comp}A" if v_comp > 0 else None)
r2.metric("电压", f"{round(u, 1)} V")
r3.metric("速度", f"{v} mm/min")

# 9. 云端反馈同步
st.markdown("---")
h = ["Time", "Mat", "Thick", "Meth", "Grade", "VLM", "I", "U", "V", "Res", "Score"]

with st.expander("🔄 反馈录入", expanded=True):
    f_c1, f_c2 = st.columns(2)
    res_a = f_c1.selectbox("质检结果", ["合格", "气孔", "未熔合", "咬边", "裂纹"])
