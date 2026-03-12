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

# 3. 增强型推理引擎 (参数全变量说明)
def get_logic(mat, thick, meth, grade):
    # --- A. 电流 (I) 逻辑变量源 ---
    # I_mat: 起始基准电流 (内置固定值，由材料决定)
    bm_lib = {
        "Q345R": {"base": 110, "u_bias": 0.5, "v_fac": 1.0},
        "316L": {"base": 95, "u_bias": -1.0, "v_fac": 0.9},
        "S30408": {"base": 100, "u_bias": 0.0, "v_fac": 0.95}
    }
    # eta (η): 焊接方法热效率系数 (内置固定值，由方法决定)
    mf_lib = {"GMAW": 1.0, "GTAW": 0.8, "LBW": 1.5}
    
    sel_bm = bm_lib.get(mat, {"base": 100, "u_bias": 0, "v_fac": 1.0})
    
    # [计算电流变量]
    i_mat = sel_bm["base"]                 # 固定常数 (基于材料)
    alpha = 12                             # 固定系数 (热损耗经验常数)
    i_thick = thick * alpha                # 变量 (与“板厚”输入正相关)
    eta = mf_lib.get(meth, 1.0)            # 固定常数 (基于方法)
    delta = 0.95 if grade == "一级" else 1.0  # 逻辑因子 (与“等级”输入相关)
    i_res = (i_mat + i_thick) * eta * delta

    # --- B. 电压 (U) 逻辑变量源 ---
    # [计算电压变量]
    u_base = 18 if grade == "一级" else 16  # 逻辑基准 (与“等级”输入相关)
    u_adj = sel_bm["u_bias"]               # 修正因子 (基于材料的电离能)
    k_slope = 40 if grade == "一级" else 45  # 电弧特性斜率 (固定常数)
    u_res = u_base + u_adj + (i_res / k_slope)

    # --- C. 速度 (V) 逻辑变量源 ---
    # [计算速度变量]
    v_base = 200                           # 固定基准 (基础线速)
    v_thick_gain = thick * 8               # 补偿变量 (与“板厚”输入正相关)
    f_mat = sel_bm["v_fac"]                # 修正因子 (基于材料流体特性)
    v_res = (v_base + v_thick_gain) * f_mat

    # --- D. 合格率 (P) 逻辑变量源 ---
    # [计算合格率变量]
    p_start = 99.0 if grade == "一级" else 96.0 # 等级起始分 (与“等级”输入相关)
    r_thick = thick * 0.12                      # 风险扣减 (与“板厚”负相关)
    r_meth = 2.0 if meth == "LBW" else 0.5      # 风险扣减 (基于方法稳定性)
    c_res = p_start - r_thick - r_meth
    
    return {
        "i_mat": i_mat, "alpha": alpha, "i_thick": i_thick, "eta": eta, "delta": delta,
        "u_base": u_base, "u_adj": u_adj, "k": k_slope,
        "v_base": v_base, "v_gain": v_thick_gain, "f_mat": f_mat,
        "p_s": p_start, "r_t": r_thick, "r_m": r_meth,
        "i_res": round(i_res, 1), "u_res": round(u_res, 1), 
        "v_res": round(v_res, 1), "c_res": round(c_res, 1)
    }

# 4. 侧边栏
st.sidebar.header("🛠 工艺特征输入面板")
v_mat = st.sidebar.selectbox("材料牌号 (Material)", ["Q345R", "316L", "S30408"])
v_thick = st.sidebar.slider("材料厚度 (Thickness/mm)", 2.0, 50.0, 10.0)
v_meth = st.sidebar.selectbox("焊接方法 (Method)", ["GMAW", "GTAW", "LBW"])
v_grade = st.sidebar.radio("质量等级 (Grade)", ["一级", "二级", "三级"])

# 5. 主页面标题
st.title("👨‍🏭 焊接工艺多模态专家系统")

# 迭代：宏观逻辑与变量字典说明
with st.expander("📘 全参数推导体系 - 变量逻辑定义字典", expanded=True):
    st.markdown("### 1. 电流推导公式: $I = (I_{mat} + \\alpha \\cdot h) \\cdot \\eta \\cdot \\delta$")
    param_i = {
        "变量符号": ["I_mat", "α (alpha)", "h", "η (eta)", "δ (delta)"],
        "变量属性": ["内置固定值", "内置固定值", "输入变量", "内置固定值", "逻辑判定值"],
        "关联条件": [f"取决于材料 ({v_mat})", "经验常数 (12A/mm)", f"取决于板厚 ({v_thick}mm)", f"取决于方法 ({v_meth})", f"取决于等级 ({v_grade})"]
    }
    st.table(pd.DataFrame(param_i))

    st.markdown("### 2. 电压推导公式: $U = U_{base} + U_{adj} + I / k$")
    param_u = {
        "变量符号": ["U_base", "U_adj", "I", "k"],
        "变量属性": ["逻辑判定值", "内置固定值", "中间推导变量", "内置固定值"],
        "关联条件": [f"取决于等级 ({v_grade})", f"取决于材料 ({v_mat})电离能", "实时推算的 I 值", "固定协同特性斜率"]
    }
    st.table(pd.DataFrame(param_u))
    

    st.markdown("### 3. 速度与合格率逻辑")
    st.caption("速度 v 受板厚产生的熔敷量需求 (h) 与材料流动因子 (f_mat) 共同控制。")
    st.caption("合格率 P 采用扣减模型：基于等级起始分，减去厚度热敏风险 (R_thick) 和方法稳定性风险 (R_meth)。")

st.markdown("---")

# 6. 计算
res = get_logic(v_mat, v_thick, v_meth, v_grade)

# 7. 实例推理路径：全变量追踪
st.subheader("📝 实例具体计算推导路径 (变量实时追踪)")
c1, c2, c3 = st.columns(3)

up_f = st.file_uploader("上传坡口图片 (多模态感知)", type=["jpg", "png", "jpeg"])
v_delta = 8.0 if up_f else 0.0
f_i = round(res['i_res'] + v_delta, 1)

with c1:
    st.info("**电流 (I) 计算流**")
    st.write(f"- 材料起步 $I_{{mat}}$: `{res['i_mat']}A`")
    st.write(f"- 厚度补偿 $\\alpha \\cdot h$: `+{res['i_thick']}A`")
    st.write(f"- 效率因子 $\\eta$: `{res['eta']}`")
    st.write(f"- 质量修正 $\\delta$: `{res['delta']}`")
    if v_delta > 0: st.write(f"- **视觉感知增益**: `+{v_delta}A`")
    st.code(f"最终推荐 I = {f_i} A")

with c2:
    st.info("**电压 (U) 计算流**")
    st.write(f"- 等级基准 $U_{{base}}$: `{res['u_base']}V`")
    st.write(f"- 材料电离修正 $U_{{adj}}$: `{res['u_adj']}V`")
    st.write(f"- 协同联动项 $I/k$: `{f_i}/{res['k']}`")
    st.code(f"最终推荐 U = {res['u_res']} V")
    

with c3:
    st.info("**速度 & 质量推演**")
    st.write(f"- 速度基准 $V_{{base}}$: `200` | 补偿: `+{res['v_gain']}`")
    st.write(f"- 材料流动修正 $f_{{mat}}$: `{res['f_mat']}`")
    st.write(f"- **质量扣减点**: 厚度`-{res['r_t']}%` | 方法`-{res['r_m']}%`")
    st.code(f"推荐 V = {res['v_res']} mm/min\n预测 P = {res['c_res']} %")

# 8. 看板展示
st.markdown("---")
r1, r2, r3, r4 = st.columns(4)
r1.metric("推荐电流", f"{f_i} A", delta=f"{v_delta}A" if v_delta > 0 else None)
r2.metric("推荐电压", f"{res['u_res']} V")
r3.metric("推荐速度", f"{res['v_res']} mm/min")
r4.metric("预测合格率", f"{res['c_res']}%")

# 9. 云端同步 (字段完全对齐)
st.markdown("---")
h_list = ["Timestamp", "Material", "Thickness", "Method", "Grade", "VLM_Feedback", "Pred_Current", "Pred_Voltage", "Pred_Speed", "Actual_Result", "Expert_Score"]

with st.expander("🔄 质量反馈录入", expanded=True):
    f_c1, f_c2 = st.columns(2)
    a_res = f_c1.selectbox("质检实际结果", ["合格", "气孔", "未熔合", "咬边", "裂纹"])
    score = f_c2.slider("专家评分 (RLHF)", 0, 100, 85)
    
    if st.button("🚀 提交反馈并更新云端", use_container_width=True):
        row = {
            "Timestamp": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M"),
            "Material": v_mat, "Thickness": v_thick, "Method": v_meth, "Grade": v_grade,
            "VLM_Feedback": "Yes" if up_f else "No", "Pred_Current": f_i,
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

if st.checkbox("查看云端历史数据"):
    try:
        hist = conn.read(spreadsheet=st.secrets["gsheets_url"], ttl=0)
        st.dataframe(hist[h_list].tail(10), use_container_width=True)
    except: st.info("数据表当前为空")
        
