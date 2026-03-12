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

# 3. 增强型推理引擎 (速度与合格率逻辑深度颗粒化)
def get_logic(mat, thick, meth, grade):
    # --- 变量资产定义 ---
    # 专家库：材料流体因子与风险权重
    # v_f: 流动性修正 (不锈钢熔池粘稠，系数低)
    # r_mat: 材料裂纹敏感度风险
    bm_lib = {
        "Q345R": {"base": 110, "u_bias": 0.5, "v_f": 1.0, "r_mat": 0.2},
        "316L": {"base": 95, "u_bias": -1.0, "v_f": 0.85, "r_mat": 0.8},
        "S30408": {"base": 100, "u_bias": 0.0, "v_f": 0.92, "r_mat": 0.5}
    }
    mf_lib = {"GMAW": 1.0, "GTAW": 0.8, "LBW": 1.5}
    
    sel_bm = bm_lib.get(mat, {"base": 100, "u_bias": 0, "v_f": 1.0, "r_mat": 0.5})
    
    # --- A. 电流 (I) 推导 ---
    i_mat = sel_bm["base"]
    i_thick = thick * 12
    eta = mf_lib.get(meth, 1.0)
    delta = 0.95 if grade == "一级" else 1.0
    i_res = (i_mat + i_thick) * eta * delta

    # --- B. 电压 (U) 推导 ---
    u_base = 18 if grade == "一级" else 16
    u_res = u_base + sel_bm["u_bias"] + (i_res / 40)

    # --- C. 速度 (V) 颗粒度化模型 ---
    # 公式：v = (v_base - v_drag * h) * f_method * f_material
    v_base = 450           # 物理上限线速 (固定值)
    v_drag = 5.5           # 厚度阻力因子 (随厚度增加，熔深要求导致速度下降)
    f_meth = eta           # 方法能量密度贡献 (激光焊大幅提升速度)
    f_mat = sel_bm["v_f"]  # 材料流体特性修正 (基于材料输入)
    v_res = (v_base - (v_drag * thick)) * f_meth * f_mat

    # --- D. 合格率 (P) 颗粒度化模型 ---
    # 公式：P = P_base - (R_thick * h) - R_method - R_material
    p_base = 99.8          # 理想状态起始分
    r_thick = 0.15         # 厚度风险系数 (厚度每增1mm，未熔合/夹渣风险提升)
    r_meth = 1.5 if meth == "LBW" else 0.4 # 方法稳定性风险 (激光对装配间隙极其敏感)
    r_mat = sel_bm["r_mat"] # 材料冶金风险 (基于材料输入：裂纹/氧化倾向)
    p_res = p_base - (r_thick * thick) - r_meth - r_mat
    
    return {
        "i_res": round(i_res, 1), "u_res": round(u_res, 1), 
        "v_res": round(v_res, 1), "c_res": round(p_res, 1),
        "i_mat": i_mat, "i_t": i_thick, "eta": eta, "delta": delta,
        "v_b": v_base, "v_d": v_drag, "f_met": f_meth, "f_mat": f_mat,
        "p_b": p_base, "r_t": r_thick, "r_met": r_meth, "r_mat": r_mat
    }

# 4. 侧边栏
st.sidebar.header("🛠 工艺特征输入")
v_mat = st.sidebar.selectbox("材料牌号 (Material)", ["Q345R", "316L", "S30408"])
v_thick = st.sidebar.slider("材料厚度 (Thickness/mm)", 2.0, 50.0, 10.0)
v_meth = st.sidebar.selectbox("焊接方法 (Method)", ["GMAW", "GTAW", "LBW"])
v_grade = st.sidebar.radio("质量等级 (Grade)", ["一级", "二级", "三级"])

# 5. 主页面
st.title("👨‍🏭 焊接工艺多模态专家系统")

# 迭代：全参数逻辑定义字典 (深度细化)
with st.expander("📘 全参数物理模型推导辞典", expanded=True):
    # 电流电压略... (保持原细化程度)
    
    st.markdown("### 3. 速度推导公式: $v = (V_{base} - V_{drag} \\cdot h) \\cdot f_{\\eta} \\cdot f_{mat}$")
    param_v = {
        "符号": ["V_base", "V_drag", "h", "f_η", "f_mat"],
        "变量说明": ["系统基准线速上限", "厚度阻力因子", "工件厚度 (Input)", "方法能量集中度修正", "材料流体特性因子"],
        "当前值/来源": ["450 mm/min (固定)", "5.5 (固定经验值)", f"{v_thick} mm", f"{get_logic(v_mat, v_thick, v_meth, v_grade)['f_met']}", f"{get_logic(v_mat, v_thick, v_meth, v_grade)['f_mat']}"]
    }
    st.table(pd.DataFrame(param_v))
    

    st.markdown("### 4. 合格率风险模型: $P = P_{base} - (R_{thick} \\cdot h) - R_{meth} - R_{mat}$")
    param_p = {
        "符号": ["P_base", "R_thick", "R_meth", "R_mat"],
        "变量说明": ["理想状态基准分", "厚度负相关风险权重", "工艺方法失稳风险", "材料冶金敏感度风险"],
        "当前影响": ["99.8% (起始)", f"-{round(v_thick*0.15, 2)}% (由厚度产生)", f"-{get_logic(v_mat, v_thick, v_meth, v_grade)['r_met']}% (由方法产生)", f"-{get_logic(v_mat, v_thick, v_meth, v_grade)['r_mat']}% (由材料产生)"]
    }
    st.table(pd.DataFrame(param_p))
    

st.markdown("---")

# 6. 计算执行
res = get_logic(v_mat, v_thick, v_meth, v_grade)

# 7. 实例推理路径：全维度追踪
st.subheader("📝 实例具体计算推导路径 (变量实时追踪)")
c1, c2, c3 = st.columns(3)

up_f = st.file_uploader("上传坡口图片 (多模态感知)", type=["jpg", "png", "jpeg"])
v_delta = 8.0 if up_f else 0.0
f_i = round(res['i_res'] + v_delta, 1)

with c1:
    st.info("**电流与电压 (I/U) 联动**")
    st.write(f"- 电流基准: `({res['i_mat']} + {res['i_t']}) * {res['eta']} * {res['delta']}`")
    if v_delta > 0: st.write(f"- 视觉感知补偿: `+{v_delta}A`")
    st.code(f"推荐 I = {f_i} A\n推荐 U = {res['u_res']} V")

with c2:
    st.info("**焊接速度 (V) 推导**")
    st.write(f"- 基准有效速度: `({res['v_b']} - {res['v_d']} * {v_thick})`")
    st.write(f"- 耦合修正因子: `x{res['f_met']} (方法) | x{res['f_mat']} (材料)`")
    st.write("- **物理逻辑**: 板厚增加导致所需熔池填充时间变长，强制降低上限速度。")
    st.code(f"推荐 V = {res['v_res']} mm/min")

with c3:
    st.info("**预测合格率 (P) 推演**")
    st.write(f"- 初始概率基准: `{res['p_b']}%`")
    st.write(f"- 厚度风险扣减: `-{res['r_t'] * v_thick}%`")
    st.write(f"- 复合风险修正: `-{res['r_met']} (方法) | -{res['r_mat']} (材料)`")
    st.code(f"预测 P = {res['c_res']} %")

# 8. 结果看板
st.markdown("---")
r1, r2, r3, r4 = st.columns(4)
r1.metric("推荐电流", f"{f_i} A", delta=f"{v_delta}A" if v_delta > 0 else None)
r2.metric("推荐电压", f"{res['u_res']} V")
r3.metric("推荐速度", f"{res['v_res']} mm/min")
r4.metric("预测合格率", f"{res['c_res']}%")

# 9. 云端同步 (字段完全对齐)
st.markdown("---")
h_list = ["Timestamp", "Material", "Thickness", "Method", "Grade", "VLM_Feedback", "Pred_Current", "Pred_Voltage", "Pred_Speed", "Actual_Result", "Expert_Score"]

with st.expander("🔄 生产反馈与数据闭环", expanded=True):
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
            st.success("✅ 数据同步成功")
            st.balloons()
        except Exception as e:
            st.error(f"同步失败: {e}")

if st.checkbox("查看云端历史数据"):
    try:
        hist = conn.read(spreadsheet=st.secrets["gsheets_url"], ttl=0)
        st.dataframe(hist[h_list].tail(10), use_container_width=True)
    except: st.info("数据表当前为空")
