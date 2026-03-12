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
    
    # 逻辑计算
    i_res = (sel_bm["i_mat"] + 12 * thick) * mf_lib.get(meth, 1.0) * (0.95 if grade == "一级" else 1.0)
    u_res = (18 if grade == "一级" else 16) + sel_bm["u_bias"] + (i_res / (40 if grade == "一级" else 45))
    v_res = (450 - 5.5 * thick) * mf_lib.get(meth, 1.0) * sel_bm["v_f"]
    p_res = 99.8 - (0.15 * thick) - (1.5 if meth == "LBW" else 0.4) - sel_bm["r_mat"]
    
    return {
        "i_res": round(i_res, 1), "u_res": round(u_res, 1), 
        "v_res": round(v_res, 1), "c_res": round(p_res, 1),
        "i_mat": sel_bm["i_mat"], "u_adj": sel_bm["u_bias"], "v_f": sel_bm["v_f"], "r_mat_risk": sel_bm["r_mat"],
        "eta": mf_lib.get(meth, 1.0), "u_b": (18 if grade == "一级" else 16), "k": (40 if grade == "一级" else 45),
        "r_met": (1.5 if meth == "LBW" else 0.4), "delta": (0.95 if grade == "一级" else 1.0)
    }

# 4. 侧边栏：输入面板
st.sidebar.header("🛠 工艺特征输入")
v_mat = st.sidebar.selectbox("材料牌号", ["Q345R", "316L", "S30408"])
v_thick = st.sidebar.number_input("材料厚度(mm)", min_value=0.5, max_value=100.0, value=10.0, step=0.1)
v_meth = st.sidebar.selectbox("焊接方法", ["GMAW", "GTAW", "LBW"])
v_grade = st.sidebar.radio("质量等级", ["一级", "二级", "三级"])

# 5. 主页面：推导字典
st.title("👨‍🏭 焊接工艺多模态专家系统")

with st.expander("📘 全参数物理模型推导辞典 (1类常量 vs 2类变量)", expanded=True):
    res = get_logic(v_mat, v_thick, v_meth, v_grade)
    
    # 属性全称定义
    C_SYS = "1类常量：固定值(系统内置常数)"
    V_MAT = "2类变量：随输入改变的变量(提示：与材料牌号输入有关)"
    V_THI = "2类变量：随输入改变的变量(提示：与材料厚度输入有关)"
    V_MET = "2类变量：随输入改变的变量(提示：与焊接方法输入有关)"
    V_GRA = "2类变量：随输入改变的变量(提示：与质量等级输入有关)"

    st.markdown("#### (1) 能量场模型 (I & U)")
    st.latex(r"I = (I_{mat} + 12 \cdot h) \cdot \eta \cdot \delta \quad | \quad U = U_{base} + U_{adj} + I / k")
    

    iu_data = {
        "参数符号": ["I_mat", "12 (alpha)", "h (板厚)", "η (eta)", "δ (delta)", "U_base", "U_adj", "k"],
        "符号物理含义": ["材料起步电流基准", "单位厚度热补偿常数", "工件物理厚度值", "焊接方法热转换效率", "质量等级电流修正系数", "基准电压起始点", "材料电离能电压偏移量", "电弧特性控制斜率"],
        "属性定义全称": [V_MAT, C_SYS, V_THI, V_MET, V_GRA, V_GRA, V_MAT, V_GRA],
        "实时数值": [f"{res['i_mat']}A", "12 A/mm", f"{v_thick}mm", f"{res['eta']}", f"{res['delta']}", f"{res['u_b']}V", f"{res['u_adj']}V", f"{res['k']}"]
    }
    st.table(pd.DataFrame(iu_data))

    st.markdown("#### (2) 动力学与风险模型 (V & P)")
    st.latex(r"v = (450 - 5.5 \cdot h) \cdot \eta \cdot f_{mat} \quad | \quad P = 99.8 - (0.15 \cdot h) - R_{meth} - R_{mat}")
    

    vp_data = {
        "参数符号": ["450 (V_base)", "5.5 (V_drag)", "f_mat", "99.8 (P_base)", "0.15 (R_thick)", "R_meth", "R_mat"],
        "符号物理含义": ["系统线速度上限基准", "厚度填充阻力系数", "材料熔池流体修正因子", "工艺理想状态起始合格率", "厚度缺陷敏感风险常数", "焊接方法稳定性风险扣减", "材料冶金敏感风险扣减"],
        "属性定义全称": [C_SYS, C_SYS, V_MAT, C_SYS, C_SYS, V_MET, V_MAT],
        "实时数值": ["450mm/min", "5.5", f"{res['v_f']}", "99.8%", "0.15", f"-{res['r_met']}%", f"-{res['r_mat_risk']}%"]
    }
    st.table(pd.DataFrame(vp_data))

st.markdown("---")

# 6. 结果看板
res_calc = get_logic(v_mat, v_thick, v_meth, v_grade)
up_f = st.file_uploader("上传坡口图片 (视觉感知)", type=["jpg", "png", "jpeg"])
v_delta = 8.0 if up_f else 0.0
final_i = round(res_calc['i_res'] + v_delta, 1)

r1, r2, r3, r4 = st.columns(4)
r1.metric("推荐电流", f"{final_i} A", delta=f"{v_delta}A" if v_delta > 0 else None)
r2.metric("推荐电压", f"{res_calc['u_res']} V")
r3.metric("推荐速度", f"{res_calc['v_res']} mm/min")
r4.metric("预测合格率", f"{res_calc['c_res']}%")

# 7. 云端同步
st.markdown("---")
h_list = ["Timestamp", "Material", "Thickness", "Method", "Grade", "VLM_Feedback", "Pred_Current", "Pred_Voltage", "Pred_Speed", "Actual_Result", "Expert_Score"]

with st.expander("🔄 生产反馈与数据同步", expanded=True):
    f_c1, f_c2 = st.columns(2)
    a_res = f_c1.selectbox("质检实际结果", ["合格", "气孔", "未熔合", "咬边", "裂纹"])
    score = f_c2.slider("专家评分", 0, 100, 85)
    if st.button("🚀 提交并同步", use_container_width=True):
        row = {"Timestamp": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M"), "Material": v_mat, "Thickness": v_thick, "Method": v_meth, "Grade": v_grade, "VLM_Feedback": "Yes" if up_f else "No", "Pred_Current": final_i, "Pred_Voltage": res_calc['u_res'], "Pred_Speed": res_calc['v_res'], "Actual_Result": a_res, "Expert_Score": score}
        try:
            url = st.secrets["gsheets_url"]
            df_o = conn.read(spreadsheet=url, ttl=0)
            conn.update(spreadsheet=url, data=pd.concat([df_o, pd.DataFrame([row]).reindex(columns=h_list)], ignore_index=True))
            st.success("✅ 同步成功"); st.balloons()
        except Exception as e: st.error(f"失败: {e}")

# 8. 历史数据查看
st.markdown("---")
if st.checkbox("🔍 查看云端历史同步记录"):
    try:
        hist = conn.read(spreadsheet=st.secrets["gsheets_url"], ttl=0)
        st.dataframe(hist[h_list].tail(15), use_container_width=True)
    except: st.info("数据库连接异常或无记录")
