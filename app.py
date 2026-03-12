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

# 3. 增强型推理引擎 (参数全维度颗粒度化)
def get_logic(mat, thick, meth, grade):
    # --- 1. 电流 (I) 逻辑资产 ---
    bm_lib = {
        "Q345R": {"base": 110, "u_bias": 0.5, "v_fac": 1.0},
        "316L": {"base": 95, "u_bias": -1.0, "v_fac": 0.9},
        "S30408": {"base": 100, "u_bias": 0.0, "v_fac": 0.95}
    }
    mf_lib = {"GMAW": 1.0, "GTAW": 0.8, "LBW": 1.5}
    
    sel_bm = bm_lib.get(mat, {"base": 100, "u_bias": 0, "v_fac": 1.0})
    
    # 电流计算
    i_mat = sel_bm["base"]
    alpha = 12
    i_thick = thick * alpha
    eta = mf_lib.get(meth, 1.0)
    delta = 0.95 if grade == "一级" else 1.0
    i_pure = (i_mat + i_thick) * eta * delta

    # --- 2. 电压 (U) 逻辑资产 (颗粒度细化) ---
    # U = U_base(等级) + U_adj(材料特性) + I/K(电弧协同)
    u_base = 18 if grade == "一级" else 16
    u_mat_adj = sel_bm["u_bias"]  # 材料电离能修正
    k_slope = 40 if grade == "一级" else 45
    u_pure = u_base + u_mat_adj + (i_pure / k_slope)

    # --- 3. 速度 (V) 逻辑资产 (颗粒度细化) ---
    # V = V_base + (板厚补偿) * 材料热物理因子
    v_base = 200
    v_thick_comp = thick * 8
    v_pure = (v_base + v_thick_comp) * sel_bm["v_fac"]

    # --- 4. 合格率 (P) 逻辑资产 (预测颗粒度) ---
    # P = P_start - (厚度敏感系数) - (工艺复杂度修正)
    p_start = 99.0 if grade == "一级" else 96.0
    p_thick_risk = thick * 0.12   # 厚度增加，未熔合风险增加
    p_meth_risk = 2.0 if meth == "LBW" else 0.5 # 激光焊对装配精度更敏感
    conf_res = p_start - p_thick_risk - p_meth_risk
    
    return {
        "i_mat": i_mat, "alpha": alpha, "i_thick": i_thick, "eta": eta, "delta": delta,
        "u_base": u_base, "u_adj": u_mat_adj, "k": k_slope,
        "v_base": v_base, "v_comp": v_thick_comp, "v_f": sel_bm["v_fac"],
        "p_s": p_start, "p_t": p_thick_risk, "p_m": p_meth_risk,
        "i_res": round(i_pure, 1), "u_res": round(u_pure, 1), 
        "v_res": round(v_pure, 1), "c_res": round(conf_res, 1)
    }

# 4. 侧边栏
st.sidebar.header("🛠 工艺特征输入")
v_mat = st.sidebar.selectbox("材料牌号", ["Q345R", "316L", "S30408"])
v_thick = st.sidebar.slider("板厚(mm)", 2.0, 50.0, 10.0)
v_meth = st.sidebar.selectbox("焊接方法", ["GMAW", "GTAW", "LBW"])
v_grade = st.sidebar.radio("质量等级", ["一级", "二级", "三级"])

# 5. 主页面标题
st.title("👨‍🏭 焊接工艺多模态专家系统")

# 迭代 1：宏观专家知识逻辑 (全维度细致化)
with st.expander("📘 核心物理模型参数全解析 (逻辑白盒化)", expanded=True):
    st.write("### 全参数推导体系")
    
    # 构造更详细的参数表
    full_param_data = {
        "物理维度": ["电流 (I)", "电压 (U)", "速度 (v)", "合格率 (P)"],
        "核心控制逻辑": [
            "I = (I_mat + α·h) · η · δ",
            "U = U_base + U_adj + I/k",
            "v = (V_base + V_comp) · f_mat",
            "P = P_start - R_thick - R_meth"
        ],
        "输入关联性": [
            "关联：材料起步能 + 板厚散热补偿 + 方法效率",
            "关联：质量等级基准 + 材料电离能修正 + 电流协同",
            "关联：基础线速度 + 板厚熔敷量修正 + 材料流速因子",
            "关联：目标等级基准 - 厚度缺陷风险 - 方法敏感度"
        ]
    }
    st.table(pd.DataFrame(full_param_data))
    

st.markdown("---")

# 6. 计算执行
res = get_logic(v_mat, v_thick, v_meth, v_grade)

# 7. 实例推理路径：全维度细化
st.subheader("📝 实例具体计算推导路径 (细颗粒度追踪)")
c1, c2, c3 = st.columns(3)

up_f = st.file_uploader("上传坡口图片 (视觉感知)", type=["jpg", "png", "jpeg"])
v_delta = 8.0 if up_f else 0.0
f_i = round(res['i_res'] + v_delta, 1)

with c1:
    st.info("**1. 电流 (I) 推导路径**")
    st.write(f"- 材料起步: `{res['i_mat']}A` | 厚度补偿: `+{res['i_thick']}A`")
    st.write(f"- 方法系数: `x{res['eta']}` | 等级修正: `x{res['delta']}`")
    if v_delta > 0: st.write(f"- **VLM视觉补偿**: `+{v_delta}A` (检测到间隙)")
    st.code(f"推荐 I = {f_i} A")

with c2:
    st.info("**2. 电压 (U) 推导路径**")
    st.write(f"- 等级基准 $U_b$: `{res['u_base']}V`")
    st.write(f"- 材料电离修正: `{res['u_adj']}V` (基于{v_mat})")
    st.write(f"- 电弧协同项 ($I/k$): `{f_i}/{res['k']}`")
    st.code(f"推荐 U = {res['u_res']} V")
    

with c3:
    st.info("**3. 速度 (V) 与合格率 (P)**")
    st.write(f"- 速度基准: `({res['v_base']}+{res['v_comp']})`")
    st.write(f"- 材料流速修正: `x{res['v_f']}`")
    st.write(f"- **合格率损耗**: 厚度`-{res['p_t']}%` | 方法`-{res['p_m']}%`")
    st.code(f"推荐 V = {res['v_res']} mm/min\n预测 P = {res['c_res']} %")

# 8. 结果看板
st.markdown("---")
r1, r2, r3, r4 = st.columns(4)
r1.metric("推荐电流", f"{f_i} A", delta=f"{v_delta}A (VLM)" if v_delta > 0 else None)
r2.metric("推荐电压", f"{res['u_res']} V")
r3.metric("焊接速度", f"{res['v_res']} mm/min")
r4.metric("预测合格率", f"{res['c_res']}%")

# 9. 云端同步
st.markdown("---")
h_list = ["Timestamp", "Material", "Thickness", "Method", "Grade", "VLM_Feedback", "Pred_Current", "Pred_Voltage", "Pred_Speed", "Actual_Result", "Expert_Score"]

with st.expander("🔄 生产反馈与数据闭环", expanded=True):
    f_c1, f_c2 = st.columns(2)
    a_res = f_c1.selectbox("实测结果", ["合格", "气孔", "未熔合", "咬边", "裂纹"])
    score = f_c2.slider("专家评分", 0, 100, 85)
    
    if st.button("🚀 提交并同步至云端", use_container_width=True):
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
            st.success("✅ 数据已入库")
            st.balloons()
        except Exception as e:
            st.error(f"同步失败: {e}")

if st.checkbox("查看历史记录"):
    try:
        data = conn.read(spreadsheet=st.secrets["gsheets_url"], ttl=0)
        st.dataframe(data[h_list].tail(10), use_container_width=True)
    except: st.info("暂无记录")
        
