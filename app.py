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

# 3. 核心推理引擎
def get_logic(mat, thick, meth, grade):
    bm_lib = {
        "Q345R": {"i_mat": 110, "u_bias": 0.5, "v_f": 1.0, "r_mat": 0.2},
        "316L": {"i_mat": 95, "u_bias": -1.0, "v_f": 0.85, "r_mat": 0.8},
        "S30408": {"i_mat": 100, "u_bias": 0.0, "v_f": 0.92, "r_mat": 0.5}
    }
    mf_lib = {"GMAW": 1.0, "GTAW": 0.8, "LBW": 1.5}
    sel_bm = bm_lib.get(mat, {"i_mat": 100, "u_bias": 0, "v_f": 1.0, "r_mat": 0.5})
    
    # 1. 电流 I 推导
    i_mat_val = sel_bm["i_mat"]
    alpha = 12
    h = thick
    eta = mf_lib.get(meth, 1.0)
    delta = 0.95 if grade == "一级" else 1.0
    i_res = (i_mat_val + alpha * h) * eta * delta

    # 2. 电压 U 推导
    u_base = 18 if grade == "一级" else 16
    u_adj = sel_bm["u_bias"]
    k_slope = 40 if grade == "一级" else 45
    u_res = u_base + u_adj + (i_res / k_slope)

    # 3. 速度 V 推导
    v_base = 450
    v_drag = 5.5
    f_eta = eta
    f_mat = sel_bm["v_f"]
    v_res = (v_base - v_drag * h) * f_eta * f_mat

    # 4. 合格率 P 推导
    p_base = 99.8
    r_thick_coef = 0.15
    r_meth_val = 1.5 if meth == "LBW" else 0.4
    r_mat_val = sel_bm["r_mat"]
    p_res = p_base - (r_thick_coef * h) - r_meth_val - r_mat_val
    
    return {
        "i_res": round(i_res, 1), "u_res": round(u_res, 1), 
        "v_res": round(v_res, 1), "c_res": round(p_res, 1),
        "i_mat": i_mat_val, "alpha": alpha, "eta": eta, "delta": delta,
        "u_base": u_base, "u_adj": u_adj, "k": k_slope,
        "v_base": v_base, "v_drag": v_drag, "f_eta": f_eta, "f_mat": f_mat,
        "p_base": p_base, "r_t": round(r_thick_coef * h, 2), "r_m": r_meth_val, "r_mat": r_mat_val
    }

# 4. 侧边栏
st.sidebar.header("🛠 工艺特征输入")
v_mat = st.sidebar.selectbox("材料牌号", ["Q345R", "316L", "S30408"])
v_thick = st.sidebar.slider("材料厚度(mm)", 2.0, 50.0, 10.0)
v_meth = st.sidebar.selectbox("焊接方法", ["GMAW", "GTAW", "LBW"])
v_grade = st.sidebar.radio("质量等级", ["一级", "二级", "三级"])

# 5. 主页面
st.title("👨‍🏭 焊接工艺多模态专家系统")

with st.expander("📘 全参数物理模型推导辞典 (参数颜色与全称定义)", expanded=True):
    res = get_logic(v_mat, v_thick, v_meth, v_grade)
    
    # 定义带颜色的属性说明逻辑
    FIX_SYS = "$\\color{blue}{固定值(系统内置常数)}$"
    FIX_MAT = "$\\color{blue}{固定值(材料属性基准)}$"
    FIX_MET = "$\\color{blue}{固定值(工艺方法特征)}$"
    VAR_INP = "$\\color{orange}{物理维度变量(用户输入关联)}$"
    VAR_LOG = "$\\color{orange}{逻辑判定值(质量等级关联)}$"

    st.markdown("#### (1) 能量场模型 (I & U)")
    st.latex(r"I = (I_{mat} + \alpha \cdot h) \cdot \eta \cdot \delta \quad | \quad U = U_{base} + U_{adj} + I / k")
    
    iu_params = {
        "参数符号": ["I_mat", "α (alpha)", "h (板厚)", "η (eta)", "delta (δ)", "U_base", "U_adj", "k"],
        "属性定义全称": [FIX_MAT, FIX_SYS, VAR_INP, FIX_MET, VAR_LOG, VAR_LOG, FIX_MAT, FIX_SYS],
        "实时数值/来源说明": [f"{res['i_mat']}A", "12 A/mm", f"{v_thick}mm", f"{res['eta']}", f"{res['delta']}", f"{res['u_base']}V", f"{res['u_adj']}V", f"{res['k']}"]
    }
    st.table(pd.DataFrame(iu_params))

    st.markdown("#### (2) 动力学与风险模型 (V & P)")
    st.latex(r"v = (V_{base} - V_{drag} \cdot h) \cdot f_{\eta} \cdot f_{mat} \quad | \quad P = P_{base} - (R_{thick} \cdot h) - R_{meth} - R_{mat}")
    
    vp_params = {
        "参数符号": ["V_base", "V_drag", "f_mat", "P_base", "R_thick*h", "R_meth", "R_mat"],
        "属性定义全称": [FIX_SYS, FIX_SYS, FIX_MAT, FIX_SYS, VAR_INP, VAR_LOG, FIX_MAT],
        "实时数值/来源说明": [f"{res['v_base']}mm/min", "5.5", f"{res['f_mat']}", "99.8%", f"-{res['r_t']}%", f"-{res['r_m']}%", f"-{res['r_mat']}%"]
    }
    st.table(pd.DataFrame(vp_params))

st.markdown("---")

# 6. 实例推理路径与结果看板 (核心逻辑不改)
res = get_logic(v_mat, v_thick, v_meth, v_grade)
up_f = st.file_uploader("上传坡口图片 (视觉感知)", type=["jpg", "png", "jpeg"])
v_delta = 8.0 if up_f else 0.0
final_i = round(res['i_res'] + v_delta, 1)

r1, r2, r3, r4 = st.columns(4)
r1.metric("推荐电流", f"{final_i} A", delta=f"{v_delta}A" if v_delta > 0 else None)
r2.metric("推荐电压", f"{res['u_res']} V")
r3.metric("推荐速度", f"{res['v_res']} mm/min")
r4.metric("预测合格率", f"{res['c_res']}%")

# 7. 云端数据闭环
st.markdown("---")
h_list = ["Timestamp", "Material", "Thickness", "Method", "Grade", "VLM_Feedback", "Pred_Current", "Pred_Voltage", "Pred_Speed", "Actual_Result", "Expert_Score"]

with st.expander("🔄 生产反馈与数据同步", expanded=True):
    f_c1, f_c2 = st.columns(2)
    a_res = f_c1.selectbox("质检实际结果", ["合格", "气孔", "未熔合", "咬边", "裂纹"])
    score = f_c2.slider("专家评分", 0, 100, 85)
    if st.button("🚀 提交反馈并同步", use_container_width=True):
        row = {"Timestamp": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M"), "Material": v_mat, "Thickness": v_thick, "Method": v_meth, "Grade": v_grade, "VLM_Feedback": "Yes" if up_f else "No", "Pred_Current": final_i, "Pred_Voltage": res['u_res'], "Pred_Speed": res['v_res'], "Actual_Result": a_res, "Expert_Score": score}
        try:
            url = st.secrets["gsheets_url"]
            df_o = conn.read(spreadsheet=url, ttl=0)
            df_n = pd.DataFrame([row]).reindex(columns=h_list)
            conn.update(spreadsheet=url, data=pd.concat([df_o, df_n], ignore_index=True))
            st.success("✅ 同步成功"); st.balloons()
        except Exception as e: st.error(f"失败: {e}")

# 8. 历史数据存证查看模块 (绝对保留)
st.markdown("---")
if st.checkbox("🔍 查看云端历史同步记录"):
    try:
        hist_data = conn.read(spreadsheet=st.secrets["gsheets_url"], ttl=0)
        st.dataframe(hist_data[h_list].tail(15), use_container_width=True)
    except: st.info("暂无历史记录或数据库连接异常")
