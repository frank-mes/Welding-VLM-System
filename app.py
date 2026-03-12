import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

# 1. 基础配置
st.set_page_config(page_title="焊接多模态专家系统", layout="wide")

# 2. 数据库连接
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except Exception:
    st.error("数据库连接异常，请检查 Secrets 配置")

# 3. 核心推理引擎 (严格保留已有逻辑并增强参数颗粒度说明)
def get_logic(mat, thick, meth, grade):
    # --- 专家库数据 ---
    bm_lib = {
        "Q345R": {"i_mat": 110, "u_bias": 0.5, "v_f": 1.0, "r_mat": 0.2},
        "316L": {"i_mat": 95, "u_bias": -1.0, "v_f": 0.85, "r_mat": 0.8},
        "S30408": {"i_mat": 100, "u_bias": 0.0, "v_f": 0.92, "r_mat": 0.5}
    }
    mf_lib = {"GMAW": 1.0, "GTAW": 0.8, "LBW": 1.5}
    sel_bm = bm_lib.get(mat, {"i_mat": 100, "u_bias": 0, "v_f": 1.0, "r_mat": 0.5})
    
    # --- 1. 电流 I 推导 (I = (I_mat + α * h) * η * δ) ---
    i_mat_val = sel_bm["i_mat"]            # 固定值 (取决于材料选择)
    alpha = 12                             # 固定值 (系统内置常数)
    h = thick                              # 输入变量 (关联: 板厚)
    eta = mf_lib.get(meth, 1.0)            # 固定值 (取决于方法选择)
    delta = 0.95 if grade == "一级" else 1.0  # 逻辑值 (关联: 质量等级)
    i_res = (i_mat_val + alpha * h) * eta * delta

    # --- 2. 电压 U 推导 (U = U_base + U_adj + I / k) ---
    u_base = 18 if grade == "一级" else 16  # 逻辑值 (关联: 质量等级)
    u_adj = sel_bm["u_bias"]               # 固定值 (取决于材料电离能)
    k_slope = 40 if grade == "一级" else 45  # 固定值 (系统内置常数)
    u_res = u_base + u_adj + (i_res / k_slope)

    # --- 3. 速度 V 推导 (v = (V_base - V_drag * h) * f_η * f_mat) ---
    v_base = 450                           # 固定值 (线速上限基准)
    v_drag = 5.5                           # 固定值 (厚度填充阻力常数)
    f_eta = eta                            # 固定值 (关联: 焊接方法热效率)
    f_mat = sel_bm["v_f"]                  # 固定值 (取决于材料流体特性)
    v_res = (v_base - v_drag * h) * f_eta * f_mat

    # --- 4. 合格率 P 推导 (P = P_base - (R_thick * h) - R_meth - R_mat) ---
    p_base = 99.8                          # 固定值 (理想状态起始分)
    r_thick_coef = 0.15                    # 固定值 (厚度风险斜率)
    r_meth_val = 1.5 if meth == "LBW" else 0.4 # 逻辑值 (关联: 方法稳定性)
    r_mat_val = sel_bm["r_mat"]            # 固定值 (取决于材料冶金敏感度)
    p_res = p_base - (r_thick_coef * h) - r_meth_val - r_mat_val
    
    return {
        "i_res": round(i_res, 1), "u_res": round(u_res, 1), 
        "v_res": round(v_res, 1), "c_res": round(p_res, 1),
        "i_mat": i_mat_val, "alpha": alpha, "eta": eta, "delta": delta,
        "u_base": u_base, "u_adj": u_adj, "k": k_slope,
        "v_base": v_base, "v_drag": v_drag, "f_eta": f_eta, "f_mat": f_mat,
        "p_base": p_base, "r_t": round(r_thick_coef * h, 2), "r_m": r_meth_val, "r_mat": r_mat_val
    }

# 4. 侧边栏：输入面板
st.sidebar.header("🛠 工艺特征输入")
v_mat = st.sidebar.selectbox("材料牌号", ["Q345R", "316L", "S30408"])
v_thick = st.sidebar.slider("材料厚度(mm)", 2.0, 50.0, 10.0)
v_meth = st.sidebar.selectbox("焊接方法", ["GMAW", "GTAW", "LBW"])
v_grade = st.sidebar.radio("质量等级", ["一级", "二级", "三级"])

# 5. 主页面：推导字典 (白盒化展示)
st.title("👨‍🏭 焊接工艺多模态专家系统")

with st.expander("📘 全参数物理模型推导辞典 (参数来源透明化)", expanded=True):
    res = get_logic(v_mat, v_thick, v_meth, v_grade)
    
    st.markdown("#### (1) 能量场模型 (I & U)")
    st.latex(r"I = (I_{mat} + \alpha \cdot h) \cdot \eta \cdot \delta")
    st.latex(r"U = U_{base} + U_{adj} + I / k")
    
    iu_params = {
        "参数符号": ["I_mat", "α (alpha)", "h (厚度)", "η (eta)", "δ (delta)", "U_base", "U_adj", "k"],
        "属性定义": ["固定值(材)", "固定值(内置)", "输入变量", "固定值(方)", "逻辑值(等)", "逻辑值(等)", "固定值(材)", "固定值(内置)"],
        "当前值/来源说明": [f"{res['i_mat']}A", "12 A/mm", f"{v_thick}mm", f"{res['eta']}", f"{res['delta']}", f"{res['u_base']}V", f"{res['u_adj']}V", f"{res['k']}"]
    }
    st.table(pd.DataFrame(iu_params))
    

    st.markdown("#### (2) 动力学与风险模型 (V & P)")
    st.latex(r"v = (V_{base} - V_{drag} \cdot h) \cdot f_{\eta} \cdot f_{mat}")
    st.latex(r"P = P_{base} - (R_{thick} \cdot h) - R_{meth} - R_{mat}")
    
    vp_params = {
        "参数符号": ["V_base", "V_drag", "f_mat", "P_base", "R_thick*h", "R_meth", "R_mat"],
        "属性定义": ["固定值(内置)", "固定值(内置)", "固定值(材)", "固定值(内置)", "变量(输入关)", "逻辑值(方)", "固定值(材)"],
        "当前值/来源说明": [f"{res['v_base']}mm/min", "5.5", f"{res['f_mat']}", "99.8%", f"-{res['r_t']}%", f"-{res['r_m']}%", f"-{res['r_mat']}%"]
    }
    st.table(pd.DataFrame(vp_params))

st.markdown("---")

# 6. 实例推理路径追踪
st.subheader("📝 实例具体计算推导路径 (变量实时追踪)")
c1, c2, c3 = st.columns(3)

up_f = st.file_uploader("上传坡口图片 (视觉感知)", type=["jpg", "png", "jpeg"])
v_delta = 8.0 if up_f else 0.0
final_i = round(res['i_res'] + v_delta, 1)

with c1:
    st.info("**电流 I 演变**")
    st.write(f"- 材料基准+补偿: `{res['i_mat']} + 12 * {v_thick}`")
    st.write(f"- 工艺修正: `x{res['eta']} x{res['delta']}`")
    if v_delta > 0: st.write(f"- VLM视觉补偿: `+{v_delta}A`")
    st.code(f"推荐 I = {final_i} A")

with c2:
    st.info("**电压 U 协同**")
    st.write(f"- 等级基准 $U_b$: `{res['u_base']}V`")
    st.write(f"- 材料修正 $U_a$: `{res['u_adj']}V`")
    st.write(f"- 电位项 $I/k$: `{final_i}/{res['k']}`")
    st.code(f"推荐 U = {res['u_res']} V")
    

with c3:
    st.info("**速度 V 与 质量 P**")
    st.write(f"- 有效速度: `({res['v_base']} - 5.5 * {v_thick}) * {res['f_eta']} * {res['f_mat']}`")
    st.write(f"- 风险总扣减: `-{res['r_t']} - {res['r_m']} - {res['r_mat']}`")
    st.code(f"推荐 V = {res['v_res']} mm/min\n预测 P = {res['c_res']} %")

# 7. 看板与数据闭环
st.markdown("---")
r1, r2, r3, r4 = st.columns(4)
r1.metric("推荐电流", f"{final_i} A", delta=f"{v_delta}A" if v_delta > 0 else None)
r2.metric("推荐电压", f"{res['u_res']} V")
r3.metric("推荐速度", f"{res['v_res']} mm/min")
r4.metric("预测合格率", f"{res['c_res']}%")

# 8. 云端数据闭环 (保持 11 个标准字段)
st.markdown("---")
h_list = ["Timestamp", "Material", "Thickness", "Method", "Grade", "VLM_Feedback", "Pred_Current", "Pred_Voltage", "Pred_Speed", "Actual_Result", "Expert_Score"]

with st.expander("🔄 生产反馈与数据同步 (RLHF)", expanded=True):
    f_c1, f_c2 = st.columns(2)
    a_res = f_c1.selectbox("质检实际结果", ["合格", "气孔", "未熔合", "咬边", "裂纹"])
    score = f_c2.slider("专家现场评分", 0, 100, 85)
    
    if st.button("🚀 提交数据并同步至云端", use_container_width=True):
        row = {
            "Timestamp": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M"),
            "Material": v_mat, "Thickness": v_thick, "Method": v_meth, "Grade": v_grade,
            "VLM_Feedback": "Yes" if up_f else "No", "Pred_Current": final_i,
            "Pred_Voltage": res['u_res'], "Pred_Speed": res['v_res'],
            "Actual_Result": a_res, "Expert_Score": score
        }
        try:
            url = st.secrets["gsheets_url"]
            df_o = conn.read(spreadsheet=url, ttl=0)
            df_n = pd.DataFrame([row]).reindex(columns=h_list)
            df_f = pd.concat([df_o, df_n], ignore_index=True)
            conn.update(spreadsheet=url, data=df_f)
            st.success("✅ 数据已安全同步至 Google Sheets")
            st.balloons()
        except Exception as e:
            st.error(f"同步失败: {e}")

# 9. 历史数据存证查看 (修复：历史数据查看模块)
st.markdown("---")
if st.checkbox("🔍 查看云端历史同步记录"):
    try:
        hist_data = conn.read(spreadsheet=st.secrets["gsheets_url"], ttl=0)
        st.dataframe(hist_data[h_list].tail(15), use_container_width=True)
    except Exception as e:
        st.info("无法读取历史记录或工作表为空。")
        
