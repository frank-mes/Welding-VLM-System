import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

# 1. 基础配置
st.set_page_config(page_title="焊接多模态专家系统", layout="wide")

# 2. 数据库连接
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except Exception:
    st.error("数据库链接异常")

# 3. 核心计算引擎 (包含预测逻辑)
def get_full_logic(mat, thick, meth, grade):
    # 专家参数
    base_i_map = {"Q345R": 110, "316L": 95, "S30408": 100}
    meth_f_map = {"GMAW": 1.0, "GTAW": 0.8, "LBW": 1.5}
    
    # --- I 推导 ---
    i_b = base_i_map.get(mat, 100)
    i_t = thick * 12
    m_f = meth_f_map.get(meth, 1.0)
    g_m = 0.95 if grade == "一级" else 1.0
    i_res = (i_b + i_t) * m_f * g_m
    
    # --- U 推导 ---
    v_c = 18 if grade == "一级" else 16
    v_r = 40 if grade == "一级" else 45
    u_res = v_c + (i_res / v_r)
    
    # --- V 推导 ---
    v_res = 200 + (thick * 8)
    
    # --- 合格率预测 (基于等级与厚度的经验模型) ---
    # 厚度越大、等级越高，预测风险略微提升
    base_conf = {"一级": 0.98, "二级": 0.95, "三级": 0.92}
    conf = base_conf.get(grade, 0.90) - (thick * 0.001)
    
    # 构造算式展示
    calc_steps = {
        "i_exp": f"({i_b} + {i_t}) * {m_f} * {g_m}",
        "u_exp": f"{v_c} + ({round(i_res,1)} / {v_r})",
        "v_exp": f"200 + ({thick} * 8)",
        "i_final": round(i_res, 1),
        "u_final": round(u_res, 1),
        "v_final": round(v_res, 1),
        "conf": round(conf * 100, 1)
    }
    return calc_steps

# 4. 侧边栏
st.sidebar.header("🛠 工艺输入")
v_mat = st.sidebar.selectbox("材料牌号", ["Q345R", "316L", "S30408"])
v_thick = st.sidebar.slider("材料厚度(mm)", 2.0, 50.0, 10.0)
v_meth = st.sidebar.selectbox("焊接方法", ["GMAW", "GTAW", "LBW"])
v_grade = st.sidebar.radio("质量等级", ["一级", "二级", "三级"])

# 5. 主页面标题
st.title("👨‍🏭 焊接工艺多模态优化系统")

# 补全：宏观逻辑公式说明
with st.expander("📘 查看宏观算法推理逻辑 (Macro Logic)", expanded=False):
    st.markdown("### 核心推理算式")
    st.latex(r"I_{base} = (I_{material} + 12 \cdot h) \cdot \eta_{method} \cdot \delta_{grade}")
    st.latex(r"U_{synergic} = U_{const} + \frac{I_{base}}{k_{synergic}}")
    st.latex(r"V_{travel} = 200 + 8 \cdot h")
    st.markdown("""
    **变量说明：**
    - $h$: 板材厚度 | $\eta$: 方法修正系数 | $\delta$: 质量等级权重
    - $k$: 协同控制系数 (一级=40, 二三级=45)
    """)

st.markdown("---")

# 6. 计算
res = get_full_logic(v_mat, v_thick, v_meth, v_grade)

# 7. 实例推理路径
st.subheader("📝 实例具体计算推导路径")
tr1, tr2, tr3 = st.columns(3)

up_f = st.file_uploader("上传坡口图片 (视觉感知激活)", type=["jpg", "png", "jpeg"])
v_delta = 5.0 if up_f else 0.0
final_i = round(res['i_final'] + v_delta, 1)

with tr1:
    st.info("**电流 (I) 推导**")
    st.code(f"算式: {res['i_exp']}\n视觉补偿: +{v_delta}\n最终: {final_i} A")

with tr2:
    st.info("**电压 (U) 推导**")
    st.code(f"算式: {res['u_exp']}\n最终: {res['u_final']} V")

with tr3:
    st.info("**速度 (V) 推导**")
    st.code(f"算式: {res['v_exp']}\n最终: {res['v_final']} mm/min")



# 8. 结果看板 (找回合格率预测)
st.markdown("---")
st.subheader("🚀 推荐工艺结果 (Final Output)")
r1, r2, r3, r4 = st.columns(4)
r1.metric("焊接电流", f"{final_i} A", delta=f"{v_delta}A" if v_delta > 0 else None)
r2.metric("电弧电压", f"{res['u_final']} V")
r3.metric("焊接速度", f"{res['v_final']} mm/min")
r4.metric("预测合格率", f"{res['conf']}%")

# 9. 完整的反馈录入 (包含之前的预测指标对照)
st.markdown("---")
header_list = ["Time", "Mat", "Thick", "Meth", "Grade", "VLM", "Pred_I", "Pred_U", "Actual_Res", "Score"]

with st.expander("🔄 质量反馈与数据闭环 (RLHF)", expanded=True):
    f_c1, f_c2, f_c3 = st.columns(3)
    actual_res = f_c1.selectbox("实测质检结果", ["合格", "气孔", "未熔合", "咬边", "裂纹"])
    expert_score = f_c2.slider("专家经验评分", 0, 100, 85)
    process_note = f_c3.text_input("工艺备注", "正常")
    
    if st.button("🚀 提交实例数据至云端", use_container_width=True):
        new_row = {
            "Time": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M"),
            "Mat": v_mat, "Thick": v_thick, "Meth": v_meth, "Grade": v_grade,
            "VLM": "Yes" if up_f else "No", 
            "Pred_I": final_i, "Pred_U": res['u_final'],
            "Actual_Res": actual_res, "Score": expert_score
        }
        try:
            url = st.secrets["gsheets_url"]
            df_old = conn.read(spreadsheet=url, ttl=0)
            df_new = pd.DataFrame([new_row])[header_list]
            df_final = pd.concat([df_old, df_new], ignore_index=True)
            conn.update(spreadsheet=url, data=df_final)
            st.success("✅ 数据已存入云端数据库！")
            st.balloons()
        except Exception as e:
            st.error(f"同步异常: {e}")

# 10. 补全：历史数据展示
st.markdown("---")
st.subheader("📊 云端历史存证记录")
if st.checkbox("展示最近 10 条同步记录"):
    try:
        data_preview = conn.read(spreadsheet=st.secrets["gsheets_url"], ttl=0)
        # 降序排列展示最近记录
        st.dataframe(data_preview.tail(10), use_container_width=True)
    except:
        st.info("当前云端暂无记录或链接未配置。")
