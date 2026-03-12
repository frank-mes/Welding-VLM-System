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

# 3. 核心推理引擎 (四维度全变量颗粒度化)
def get_logic(mat, thick, meth, grade):
    # --- 专家经验库 (Logic Assets) ---
    bm_lib = {
        "Q345R": {"i_mat": 110, "u_bias": 0.5, "v_f": 1.0, "r_mat": 0.2},
        "316L": {"i_mat": 95, "u_bias": -1.0, "v_f": 0.85, "r_mat": 0.8},
        "S30408": {"i_mat": 100, "u_bias": 0.0, "v_f": 0.92, "r_mat": 0.5}
    }
    mf_lib = {"GMAW": 1.0, "GTAW": 0.8, "LBW": 1.5}
    
    sel_bm = bm_lib.get(mat, {"i_mat": 100, "u_bias": 0, "v_f": 1.0, "r_mat": 0.5})
    
    # --- A. 电流 (I) 逻辑：热平衡模型 ---
    i_mat_base = sel_bm["i_mat"]           # 固定值 (基于材料)
    alpha = 12                             # 固定系数 (热损耗常数)
    i_thick_comp = thick * alpha           # 变量 (关联:板厚)
    eta = mf_lib.get(meth, 1.0)            # 固定值 (基于方法)
    delta = 0.95 if grade == "一级" else 1.0  # 逻辑值 (关联:等级)
    i_res = (i_mat_base + i_thick_comp) * eta * delta

    # --- B. 电压 (U) 逻辑：电弧协同模型 ---
    u_base = 18 if grade == "一级" else 16  # 逻辑值 (关联:等级)
    u_mat_adj = sel_bm["u_bias"]           # 固定值 (基于材料电离能)
    k_slope = 40 if grade == "一级" else 45  # 固定系数 (电弧特性斜率)
    u_res = u_base + u_mat_adj + (i_res / k_slope)

    # --- C. 速度 (V) 逻辑：熔敷动力学模型 ---
    v_base = 450                           # 固定基准 (物理线速上限)
    v_drag = 5.5                           # 固定系数 (厚度填充阻力因子)
    f_meth = eta                           # 变量 (由方法能量密度决定)
    f_mat = sel_bm["v_f"]                  # 固定值 (基于材料流体特性)
    v_res = (v_base - (v_drag * thick)) * f_meth * f_mat

    # --- D. 合格率 (P) 逻辑：多因子风险模型 ---
    p_base = 99.8                          # 固定值 (理想状态基准)
    r_thick_val = thick * 0.15             # 变量 (关联:板厚热敏风险)
    r_meth_val = 1.5 if meth == "LBW" else 0.4 # 逻辑值 (关联:方法稳定性风险)
    r_mat_val = sel_bm["r_mat"]            # 固定值 (基于材料冶金敏感度)
    p_res = p_base - r_thick_val - r_meth_val - r_mat_val
    
    return {
        "i_res": round(i_res, 1), "u_res": round(u_res, 1), 
        "v_res": round(v_res, 1), "c_res": round(p_res, 1),
        "i_mat": i_mat_base, "alpha": alpha, "i_t": i_thick_comp, "eta": eta, "delta": delta,
        "u_b": u_base, "u_a": u_mat_adj, "k": k_slope,
        "v_b": v_base, "v_d": v_drag, "f_met": f_meth, "f_mat": f_mat,
        "p_b": p_base, "r_t": r_thick_val, "r_met": r_meth_val, "r_mat": r_mat_val
    }

# 4. 侧边栏输入
st.sidebar.header("🛠 工艺特征输入")
v_mat = st.sidebar.selectbox("材料牌号", ["Q345R", "316L", "S30408"])
v_thick = st.sidebar.slider("材料厚度(mm)", 2.0, 50.0, 10.0)
v_meth = st.sidebar.selectbox("焊接方法", ["GMAW", "GTAW", "LBW"])
v_grade = st.sidebar.radio("质量等级", ["一级", "二级", "三级"])

# 5. 主页面标题
st.title("👨‍🏭 焊接工艺多模态专家系统")

# 6. 全变量白盒定义辞典 (合并并补全电流、电压、速度、合格率)
with st.expander("📘 全参数推导体系 - 变量逻辑定义字典", expanded=True):
    # 获取实时计算值
    res = get_logic(v_mat, v_thick, v_meth, v_grade)
    
    # 1. 电流与电压字典
    st.markdown("#### (1) 电流/电压变量控制表")
    dict_iu = {
        "符号": ["I_mat", "α (alpha)", "η (eta)", "U_base", "U_adj", "k"],
        "变量属性": ["内置固定值", "内置固定值", "内置固定值", "逻辑判定值", "内置固定值", "内置固定值"],
        "工程意义与关联说明": [
            f"材料基础起步电流 (当前: {res['i_mat']}A)",
            "板厚散热补偿系数 (12A/mm)",
            f"方法热效率 (当前: {res['eta']})",
            f"等级基准电压 (当前: {res['u_b']}V)",
            f"材料电离能修正 (当前: {res['u_a']}V)",
            "协同电弧硬度斜率 (固定常数)"
        ]
    }
    st.table(pd.DataFrame(dict_iu))
    

    # 2. 速度与合格率字典
    st.markdown("#### (2) 速度/合格率风险控制表")
    dict_vp = {
        "符号": ["V_base", "V_drag", "f_mat", "P_base", "R_thick", "R_meth"],
        "变量属性": ["内置固定值", "内置固定值", "内置固定值", "内置固定值", "变量(输入相关)", "逻辑判定值"],
        "工程意义与关联说明": [
            "物理极限线速度基准 (450mm/min)",
            "厚度填充阻力因子 (5.5)",
            f"材料流体特性修正 (当前: {res['f_mat']})",
            "理想工艺起始合格率 (99.8%)",
            f"厚度热敏风险扣减 (当前: -{round(res['r_t'], 2)}%)",
            f"方法稳定性风险 (当前: -{res['r_met']}%)"
        ]
    }
    st.table(pd.DataFrame(dict_vp))
    

st.markdown("---")

# 7. 实例推理路径追踪 (四维度全显)
st.subheader("📝 实例具体计算推导路径 (变量实时追踪)")
c1, c2, c3 = st.columns(3)

up_f = st.file_uploader("上传坡口图片 (多模态视觉)", type=["jpg", "png", "jpeg"])
v_delta = 8.0 if up_f else 0.0
final_i = round(res['i_res'] + v_delta, 1)

with c1:
    st.info("**1. 电流 (I) 推导路径**")
    st.write(f"- 基准电流: `{res['i_mat']}A` + 补偿: `{res['i_t']}A`")
    st.write(f"- 修正: `x{res['eta']} (方法) | x{res['delta']} (等级)`")
    if v_delta > 0: st.write(f"- **视觉感知增益**: `+{v_delta}A`")
    st.code(f"最终推荐 I = {final_i} A")

with c2:
    st.info("**2. 电压 (U) 推导路径**")
    st.write(f"- 等级基准 $U_b$: `{res['u_b']}V`")
    st.write(f"- 材料修正 $U_a$: `{res['u_a']}V`")
    st.write(f"- 电弧协同 $I/k$: `{final_i}/{res['k']}`")
    st.code(f"最终推荐 U = {res['u_res']} V")
    

with c3:
    st.info("**3. 速度 (V) 与 质量 (P)**")
    st.write(f"- 速度基准: `({res['v_b']} - {res['v_d']} * {v_thick})`")
    st.write(f"- 速度修正: `x{res['f_met']} (方法) | x{res['f_mat']} (材料)`")
    st.write(f"- 合格率风险: `-{res['r_t']}%(厚) | -{res['r_met']}%(法) | -{res['r_mat']}%(材)`")
    st.code(f"推荐 V = {res['v_res']} mm/min\n预测 P = {res['c_res']} %")

# 8. 核心看板
st.markdown("---")
r1, r2, r3, r4 = st.columns(4)
r1.metric("推荐电流", f"{final_i} A", delta=f"{v_delta}A" if v_delta > 0 else None)
r2.metric("推荐电压", f"{res['u_res']} V")
r3.metric("推荐速度", f"{res['v_res']} mm/min")
r4.metric("预测合格率", f"{res['c_res']}%")

# 9. 云端同步与历史记录
st.markdown("---")
h_list = ["Timestamp", "Material", "Thickness", "Method", "Grade", "VLM_Feedback", "Pred_Current", "Pred_Voltage", "Pred_Speed", "Actual_Result", "Expert_Score"]

with st.expander("🔄 生产反馈与数据闭环", expanded=True):
    f_c1, f_c2 = st.columns(2)
    a_res = f_c1.selectbox("质检实际结果", ["合格", "气孔", "未熔合", "咬边", "裂纹"])
    score = f_c2.slider("专家评分 (RLHF)", 0, 100, 85)
    
    if st.button("🚀 提交并同步", use_container_width=True):
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
            st.success("✅ 数据已同步")
            st.balloons()
        except Exception as e:
            st.error(f"同步异常: {e}")

if st.checkbox("查看历史同步数据"):
    try:
        hist = conn.read(spreadsheet=st.secrets["gsheets_url"], ttl=0)
        st.dataframe(hist[h_list].tail(10), use_container_width=True)
    except: st.info("当前无数据")
        
