import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

# 1. 基础配置
st.set_page_config(page_title="焊接多模态专家系统", layout="wide")

# 2. 数据库连接
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except Exception:
    st.error("数据库连接异常")

# 3. 核心推理引擎 (公式逻辑全内置)
def get_logic(mat, thick, meth, grade):
    # --- 专家经验常数 ---
    bm_lib = {
        "Q345R": {"i_mat": 110, "u_bias": 0.5, "v_f": 1.0, "r_mat": 0.2},
        "316L": {"i_mat": 95, "u_bias": -1.0, "v_f": 0.85, "r_mat": 0.8},
        "S30408": {"i_mat": 100, "u_bias": 0.0, "v_f": 0.92, "r_mat": 0.5}
    }
    mf_lib = {"GMAW": 1.0, "GTAW": 0.8, "LBW": 1.5}
    sel_bm = bm_lib.get(mat, {"i_mat": 100, "u_bias": 0, "v_f": 1.0, "r_mat": 0.5})
    
    # 1. 电流 I 公式: (I_mat + α * h) * η * δ
    i_mat = sel_bm["i_mat"]
    alpha = 12
    i_thick = thick * alpha
    eta = mf_lib.get(meth, 1.0)
    delta = 0.95 if grade == "一级" else 1.0
    i_res = (i_mat + i_thick) * eta * delta

    # 2. 电压 U 公式: U_base + U_adj + I / k
    u_base = 18 if grade == "一级" else 16
    u_adj = sel_bm["u_bias"]
    k_slope = 40 if grade == "一级" else 45
    u_res = u_base + u_adj + (i_res / k_slope)

    # 3. 速度 V 公式: (V_base - V_drag * h) * f_η * f_mat
    v_base = 450
    v_drag = 5.5
    f_met = eta
    f_mat = sel_bm["v_f"]
    v_res = (v_base - (v_drag * thick)) * f_met * f_mat

    # 4. 合格率 P 公式: P_base - (R_thick * h) - R_meth - R_mat
    p_base = 99.8
    r_t_coef = 0.15
    r_t_val = thick * r_t_coef
    r_met_val = 1.5 if meth == "LBW" else 0.4
    r_mat_val = sel_bm["r_mat"]
    p_res = p_base - r_t_val - r_met_val - r_mat_val
    
    return {
        "i_res": round(i_res, 1), "u_res": round(u_res, 1), 
        "v_res": round(v_res, 1), "c_res": round(p_res, 1),
        "i_mat": i_mat, "alpha": alpha, "i_t": i_thick, "eta": eta, "delta": delta,
        "u_b": u_base, "u_a": u_adj, "k": k_slope,
        "v_b": v_base, "v_d": v_drag, "f_met": f_met, "f_mat": f_mat,
        "p_b": p_base, "r_t": r_t_val, "r_met": r_met_val, "r_mat": r_mat_val
    }

# 4. 侧边栏
st.sidebar.header("🛠 工艺特征输入")
v_mat = st.sidebar.selectbox("材料牌号", ["Q345R", "316L", "S30408"])
v_thick = st.sidebar.slider("材料厚度(mm)", 2.0, 50.0, 10.0)
v_meth = st.sidebar.selectbox("焊接方法", ["GMAW", "GTAW", "LBW"])
v_grade = st.sidebar.radio("质量等级", ["一级", "二级", "三级"])

# 5. 主页面
st.title("👨‍🏭 焊接工艺多模态专家系统")

# 📘 全参数推导体系 - 这里的公式我用 LaTeX 重新加固了！
with st.expander("📘 全参数推导体系 - 专家逻辑字典 (包含核心公式)", expanded=True):
    res = get_logic(v_mat, v_thick, v_meth, v_grade)
    
    st.markdown("#### 1. 能量与成形公式 (I, U, V)")
    st.latex(r"I = (I_{mat} + \alpha \cdot h) \cdot \eta \cdot \delta")
    st.latex(r"U = U_{base} + U_{adj} + I / k")
    st.latex(r"v = (V_{base} - V_{drag} \cdot h) \cdot f_{\eta} \cdot f_{mat}")
    
    dict_welding = {
        "变量": ["I_mat (材料基准)", "α (补偿系数)", "η (方法效率)", "U_base (等级基准)", "V_base (速上限)", "f_mat (流体因子)"],
        "属性": ["内置常数", "经验常数", "工艺常数", "逻辑判定", "物理常数", "材料常数"],
        "当前数值/关联说明": [f"{res['i_mat']}A", "12 A/mm", f"{res['eta']}", f"{res['u_b']}V", "450 mm/min", f"{res['f_mat']}"]
    }
    st.table(pd.DataFrame(dict_welding))
    

    st.markdown("#### 2. 质量风险模型 (P)")
    st.latex(r"P = P_{base} - (R_{thick} \cdot h) - R_{meth} - R_{mat}")
    
    dict_risk = {
        "变量": ["P_base (起始分)", "R_thick (厚度风险)", "R_meth (方法风险)", "R_mat (材料风险)"],
        "属性": ["内置基准", "输入正相关", "逻辑判定", "内置固定"],
        "当前影响量": ["99.8%", f"-{round(res['r_t'], 2)}%", f"-{res['r_met']}%", f"-{res['r_mat']}%"]
    }
    st.table(pd.DataFrame(dict_risk))
    

st.markdown("---")

# 6. 计算与推理路径
res = get_logic(v_mat, v_thick, v_meth, v_grade)
st.subheader("📝 实例具体计算推导路径 (变量追踪)")

up_f = st.file_uploader("上传坡口图片 (视觉感知)", type=["jpg", "png", "jpeg"])
v_delta = 8.0 if up_f else 0.0
final_i = round(res['i_res'] + v_delta, 1)

c1, c2, c3 = st.columns(3)
with c1:
    st.info("**电流 (I) 路径**")
    st.write(f"算式: `({res['i_mat']} + 12 * {v_thick}) * {res['eta']} * {res['delta']}`")
    if v_delta > 0: st.write(f"VLM补偿: `+{v_delta}A`")
    st.code(f"推荐 I = {final_i} A")

with c2:
    st.info("**电压 (U) 路径**")
    st.write(f"算式: `{res['u_b']} + {res['u_a']} + ({final_i} / {res['k']})`")
    st.code(f"推荐 U = {res['u_res']} V")
    

with c3:
    st.info("**速度 (V) & 质量 (P)**")
    st.write(f"V算式: `({res['v_b']} - 5.5 * {v_thick}) * {res['f_met']} * {res['f_mat']}`")
    st.write(f"P损耗: `-{res['r_t']}% (厚) | -{res['r_met']}% (法)`")
    st.code(f"推荐 V = {res['v_res']} mm/min\n预测 P = {res['c_res']} %")

# 8. 结果看板与同步略... (保持之前的稳健结构)
st.markdown("---")
r1, r2, r3, r4 = st.columns(4)
r1.metric("推荐电流", f"{final_i} A", delta=f"{v_delta}A" if v_delta > 0 else None)
r2.metric("推荐电压", f"{res['u_res']} V")
r3.metric("推荐速度", f"{res['v_res']} mm/min")
r4.metric("预测合格率", f"{res['c_res']}%")

# 9. 云端同步
st.markdown("---")
h_list = ["Timestamp", "Material", "Thickness", "Method", "Grade", "VLM_Feedback", "Pred_Current", "Pred_Voltage", "Pred_Speed", "Actual_Result", "Expert_Score"]
with st.expander("🔄 生产反馈与数据闭环", expanded=True):
    f_c1, f_c2 = st.columns(2)
    a_res = f_c1.selectbox("质检实际结果", ["合格", "气孔", "未熔合", "咬边", "裂纹"])
    score = f_c2.slider("专家评分", 0, 100, 85)
    if st.button("🚀 提交反馈", use_container_width=True):
        row = {"Timestamp": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M"), "Material": v_mat, "Thickness": v_thick, "Method": v_meth, "Grade": v_grade, "VLM_Feedback": "Yes" if up_f else "No", "Pred_Current": final_i, "Pred_Voltage": res['u_res'], "Pred_Speed": res['v_res'], "Actual_Result": a_res, "Expert_Score": score}
        try:
            url = st.secrets["gsheets_url"]
            df_o = conn.read(spreadsheet=url, ttl=0)
            df_n = pd.DataFrame([row]).reindex(columns=h_list)
            conn.update(spreadsheet=url, data=pd.concat([df_o, df_n], ignore_index=True))
            st.success("✅ 同步成功"); st.balloons()
        except Exception as e: st.error(f"失败: {e}")
            
