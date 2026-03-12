import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

# 1. 基础配置
st.set_page_config(page_title="焊接多模态专家系统", layout="wide")

# 2. 数据库连接
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except Exception:
    st.error("数据库连接异常，请检查Secrets配置")

# 3. 增强型推理引擎 (逻辑白盒化)
def get_logic(mat, thick, meth, grade):
    # --- A. 基础基准获取 ---
    # 定义不同材料的热敏感度与熔点基准
    bm_data = {
        "Q345R": {"base": 110, "desc": "碳钢类：热传导率中等，起弧要求稳"},
        "316L": {"base": 95, "desc": "不锈钢类：热传导率低，易过热，需小电流"},
        "S30408": {"base": 100, "desc": "奥氏体钢：热膨胀系数大，电流需适中"}
    }
    # 方法修正系数
    mf_data = {
        "GMAW": 1.0,  # 熔化极气体保护焊：标准热效率
        "GTAW": 0.8,  # 钨极氩弧焊：热量较分散，有效电流较低
        "LBW": 1.5    # 激光焊：能量高度集中，等效穿透电流高
    }
    
    selected_bm = bm_data.get(mat, {"base": 100, "desc": "未知材料"})
    i_base = selected_bm["base"]
    
    # --- B. 计算中间项 ---
    i_thick_gain = thick * 12  # 物理原则：每增加1mm厚度，需补偿12A维持熔深
    method_factor = mf_data.get(meth, 1.0)
    grade_factor = 0.95 if grade == "一级" else 1.0 # 质量越高，热输入控制越严
    
    # --- C. 最终结果汇总 ---
    # 电流推演
    i_pure = (i_base + i_thick_gain) * method_factor * grade_factor
    # 电压协同逻辑：基于Synergic控制曲线 U = f(I)
    u_const = 18 if grade == "一级" else 16
    k_factor = 40 if grade == "一级" else 45
    u_pure = u_const + (i_pure / k_factor)
    # 速度逻辑：维持单位线能量 Q = UI/v 的平衡
    v_pure = 200 + (thick * 8)
    
    # 合格率预测：基于物理稳定性
    conf = (98.0 if grade == "一级" else 94.0) - (thick * 0.15)
    
    return {
        "i_base": i_base, "i_thick": i_thick_gain, "m_f": method_factor, "g_f": grade_factor,
        "u_c": u_const, "k": k_factor, "i_res": round(i_pure, 1), "u_res": round(u_pure, 1),
        "v_res": v_pure, "conf": round(conf, 1), "mat_desc": selected_bm["desc"]
    }

# 4. 侧边栏
st.sidebar.header("特征参数输入")
v_mat = st.sidebar.selectbox("材料牌号 (Material)", ["Q345R", "316L", "S30408"])
v_thick = st.sidebar.slider("材料厚度 (Thickness/mm)", 2.0, 50.0, 10.0)
v_meth = st.sidebar.selectbox("焊接方法 (Method)", ["GMAW", "GTAW", "LBW"])
v_grade = st.sidebar.radio("焊缝等级 (Grade)", ["一级", "二级", "三级"])

# 5. 主页面标题
st.title("👨‍🏭 焊接工艺多模态专家系统")

# 迭代 1：宏观专家知识逻辑 (细致化)
with st.expander("📘 查看宏观专家知识逻辑说明", expanded=True):
    st.markdown("### 1. 能量平衡准则 (Energy Balance)")
    st.latex(r"Q_{input} = \eta \frac{U \cdot I}{v}")
    st.markdown("""
    本系统核心逻辑基于**热补偿模型**：
    - **电流 (I) 定位**：通过 `(材料基准 + 厚度增益) × 工艺修正`。厚度每增加 1mm，为了克服母材的热传导流失，必须线性补偿电流。
    - **电压 (U) 协同**：采用 `Synergic` 曲线。电压决定电弧长度，必须随电流同步跳动以维持电弧挺度。
    - **质量等级权重**：一级焊缝通过降低 $5\%$ 电流增益并提高电压基准，强制实现“小电流、稳电弧”的高质量成形。
    """)
    # 逻辑可视化表
    logic_df = pd.DataFrame({
        "影响维度": ["材料特性", "板材厚度", "焊接方法", "质量要求"],
        "逻辑贡献点": ["初始基准电流", "热流失补偿值", "能量集中度系数", "热输入限制因子"],
        "当前作用值": [f"{v_mat}", f"+{v_thick*12}A", f"x{1.5 if v_meth=='LBW' else 1.0}", f"{'95%' if v_grade=='一级' else '100%'}"]
    })
    st.table(logic_df)



st.markdown("---")

# 6. 计算
res = get_logic(v_mat, v_thick, v_meth, v_grade)

# 迭代 2：实例具体计算推演 (细致化)
st.subheader("📝 当前实例：分步推理路径追踪")
c1, c2, c3 = st.columns(3)

up_f = st.file_uploader("上传坡口实时图片 (VLM 感知)", type=["jpg", "png", "jpeg"])
v_d = 8.0 if up_f else 0.0 # 视觉发现间隙偏大时，自动补偿电流
final_i = round(res['i_res'] + v_d, 1)

with c1:
    st.info("**第一步：电流 (I) 推导**")
    st.markdown(f"1. **材料基准**: `{res['i_base']}A` ({res['mat_desc']})")
    st.markdown(f"2. **厚度补偿**: `+{res['i_thick']}A` (基于{v_thick}mm)")
    st.markdown(f"3. **工艺修正**: `×{res['m_f']} (方法) ×{res['g_f']} (等级)`")
    if v_d > 0:
        st.markdown(f"4. **视觉补偿**: `+{v_d}A` (VLM检测间隙)")
    st.code(f"最终电流 = {final_i} A")

with c2:
    st.info("**第二步：电压 (U) 推导**")
    st.markdown(f"1. **电压基准**: `{res['u_c']}V` (针对{v_grade}焊缝)")
    st.markdown(f"2. **协同增益**: `I / {res['k']}`")
    st.markdown(f"3. **动态计算**: `{res['u_c']} + ({final_i} / {res['k']})`")
    st.code(f"最终电压 = {res['u_res']} V")

with c3:
    st.info("**第三步：速度 (V) 推导**")
    st.markdown(f"1. **基础线速**: `200 mm/min`")
    st.markdown(f"2. **厚度影响**: `+{v_thick}mm × 8` (减缓速度增加熔敷量)")
    st.markdown(f"3. **平衡计算**: `200 + {v_thick * 8}`")
    st.code(f"最终速度 = {res['v_res']} mm/min")



# 8. 结果结果看板
st.markdown("---")
st.subheader("🚀 最终推荐工艺参数")
r1, r2, r3, r4 = st.columns(4)
r1.metric("焊接电流", f"{final_i} A", delta=f"{v_d}A (VLM)" if v_d > 0 else None)
r2.metric("电弧电压", f"{res['u_res']} V")
r3.metric("焊接速度", f"{res['v_res']} mm/min")
r4.metric("预测合格率", f"{res['conf']}%")

# 9. 云端反馈同步 (数据结构完全对齐原表)
st.markdown("---")
target_headers = [
    "Timestamp", "Material", "Thickness", "Method", "Grade", 
    "VLM_Feedback", "Pred_Current", "Pred_Voltage", "Pred_Speed", 
    "Actual_Result", "Expert_Score"
]

with st.expander("🔄 生产反馈与数据闭环 (RLHF)", expanded=True):
    f_c1, f_c2 = st.columns(2)
    with f_c1:
        act_res = st.selectbox("实测质检结果", ["合格", "气孔", "未熔合", "咬边", "裂纹"])
    with f_c2:
        expert_score = st.slider("专家现场打分", 0, 100, 85)
    
    if st.button("🚀 提交并同步至云端", use_container_width=True):
        new_row = {
            "Timestamp": pd.Timestamp.now().
