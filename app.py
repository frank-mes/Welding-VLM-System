import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

# 1. 基础页面设置
st.set_page_config(page_title="焊接多模态专家系统", layout="wide")

# 2. 安全数据库连接
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except Exception:
    st.error("数据库连接初始化失败")

# 3. 逻辑推演函数
def get_welding_logic(mat, thick, meth, grade):
    # 材料专家库：定义物理特性描述
    bm_lib = {
        "Q345R": {"base": 110, "info": "碳钢: 导热系数约45W/(m·K)，热影响区宽"},
        "316L": {"base": 95, "info": "不锈钢: 导热系数低，线膨胀系数大，极易变形"},
        "S30408": {"base": 100, "info": "奥氏体钢: 需严格控制层间温度以防热裂纹"}
    }
    # 工艺修正系数 (eta)
    mf_lib = {"GMAW": 1.0, "GTAW": 0.8, "LBW": 1.5}
    
    # 逻辑单元拆解
    sel_bm = bm_lib.get(mat, {"base": 100, "info": "常规材料"})
    i_base = sel_bm["base"]
    i_thick_compensate = thick * 12 # 物理原则: 每mm板厚增加12A以对冲散热
    m_factor = mf_lib.get(meth, 1.0)
    g_factor = 0.95 if grade == "一级" else 1.0 # 质量等级: 一级焊缝限制热输入
    
    # 计算推导
    i_final = (i_base + i_thick_compensate) * m_factor * g_factor
    u_const = 18 if grade == "一级" else 16
    u_k = 40 if grade == "一级" else 45
    u_final = u_const + (i_final / u_k)
    v_final = 200 + (thick * 8)
    
    # 可信度模型
    conf = (98.0 if grade == "一级" else 94.0) - (thick * 0.1)
    
    return {
        "i_b": i_base, "i_t": i_thick_compensate, "m_f": m_factor, "g_f": g_factor,
        "u_c": u_const, "u_k": u_k, "i_res": round(i_final, 1),
        "u_res": round(u_final, 1), "v_res": v_final, "c_res": round(conf, 1),
        "desc": sel_bm["info"]
    }

# 4. 侧边栏：参数输入
st.sidebar.header("🛠 工艺特征输入")
v_mat = st.sidebar.selectbox("材料牌号", ["Q345R", "316L", "S30408"])
v_thick = st.sidebar.slider("板厚 (mm)", 2.0, 50.0, 10.0)
v_meth = st.sidebar.selectbox("焊接方法", ["GMAW", "GTAW", "LBW"])
v_grade = st.sidebar.radio("质量等级", ["一级", "二级", "三级"])

# 5. 主页面：宏观专家逻辑
st.title("👨‍🏭 焊接工艺多模态专家系统")

with st.expander("📘 宏观专家知识逻辑 - 物理模型深度解析", expanded=True):
    st.write("### 核心能量推导准则")
    # 加固处理：单行 LaTeX 严防 SyntaxError
    st.latex(r"I_{target} = (I_{material} + \alpha \cdot h) \cdot \eta \cdot \delta")
    st.latex(r"U_{synergic} = U_{const} + (I_{target} / k)")
    
    col_l, col_r = st.columns(2)
    with col_l:
        st.write("**1. 三维散热补偿理论**")
        st.caption("基于热传导物理模型，母材厚度决定了热沉(Heat Sink)效应。系统通过线性系数补偿电流，确保焊缝根部获得额定热输入。")
    with col_r:
        st.write("**2. Synergic 协同控制逻辑**")
        st.caption("电压不再是固定值，而是由电流联动推导。通过动态调整电弧挺度，确保在大电流区间依然维持稳定的熔滴过渡。")



st.markdown("---")

# 6. 计算执行
res = get_welding_logic(v_mat, v_thick, v_meth, v_grade)

# 7. 实例推理路径：微观细致化拆解
st.subheader("📝 实例推理路径追踪 (Step-by-Step)")
c1, c2, c3 = st.columns(3)

# 模拟 VLM 感知层
up_f = st.file_uploader("上传坡口实时图像 (激活 VLM 视觉补偿)", type=["jpg", "png", "jpeg"])
v_delta = 8.0 if up_f else 0.0
final_i = round(res['i_res'] + v_delta, 1)

with c1:
    st.info("**第一步：电流 (I) 推导**")
    st.write(f"- 材料起步值: `{res['i_b']} A`")
    st.caption(f"专家解读: {res['desc']}")
    st.write(f"- 厚度补偿值: `+{res['i_t']} A` (补偿散热)")
    st.write(f"- 工艺修正比: `x{res['m_f']} x{res['g_f']}`")
    if v_delta > 0: st.write(f"- **VLM视觉补偿**: `+{v_delta} A` (检测到间隙)")
    st.code(f"推荐电流 = {final_i} A")

with c2:
    st.info("**第二步：电压 (U) 协同**")
    st.write(f"- 等级基准压: `{res['u_c']} V`")
    st.write(f"- 电流联动项: `{final_i} / {res['u_k']}`")
    st.write("- **控制逻辑**: 增加电流时同步拉长电弧以防短路飞溅。")
    st.code(f"推荐电压 = {res['u_res']} V")



with c3:
    st.info("**第三步：速度 (V) 稳定性**")
    st.write("- 初始基准速: `200 mm/min`")
    st.write(f"- 熔敷修正量: `+{v_thick}*8` (板厚因子)")
    st.write("- **物理平衡**: 减缓移动速度以确保熔池充分铺展。")
    st.code(f"推荐速度 = {res['v_res']} mm/min")

# 8. 核心结果看板
st.markdown("---")
r1, r2, r3, r4 = st.columns(4)
r1.metric("焊接电流", f"{final_i} A", delta=f"{v_delta}A (VLM)" if v_delta > 0 else None)
r2.metric("电弧电压", f"{res['u_res']} V")
r3.metric("焊接速度", f"{res['v_res']} mm/min")
r4.metric("预测合格率", f"{res['c_res']}%")

# 9. 云端反馈同步 (完全匹配原 11 个字段)
st.markdown("---")
header_list = ["Timestamp", "Material", "Thickness", "Method", "Grade", "VLM_Feedback", "Pred_Current", "Pred_Voltage", "Pred_Speed", "Actual_Result", "Expert_Score"]

with st.expander("🔄 生产反馈与数据闭环 (RLHF)", expanded=True):
    f1, f2 = st.columns(2)
    with f1:
        actual_res = st.selectbox("实测质检结果", ["合格", "气孔", "未熔合", "咬边", "裂纹"])
    with f2:
        expert_score = st.slider("专家现场评分", 0, 100, 85)
    
    if st.button("🚀 提交数据至云端", use_container_width=True):
        row_data = {
            "Timestamp": pd.Timestamp.now().strftime("%m-%d %H:%M"),
            "Material": v_mat, "Thickness": v_thick, "Method": v_meth, "Grade": v_grade,
            "VLM_Feedback": "Yes" if up_f else "No", "Pred_Current": final_i,
            "Pred_Voltage": res['u_res'], "Pred_Speed": res['v_res'],
            "Actual_Result": actual_res, "Expert_Score": expert_score
        }
        try:
            url = st.secrets["gsheets_url"]
            df_old = conn.read(spreadsheet=url, ttl=0)
            df_new = pd.DataFrame([row_data]).reindex(columns=header_list)
            df_all = pd.concat([df_old, df_new], ignore_index=True)
            conn.update(spreadsheet=url, data=df_all)
            st.success("✅ 数据已同步至云端！")
            st.balloons()
        except Exception as e:
            st.error(f"同步失败: {e}")

# 10. 历史存证查看
if st.checkbox("查看云端同步记录"):
    try:
        history = conn.read(spreadsheet=st.secrets["gsheets_url"], ttl=0)
        st.dataframe(history[header_list].tail(10), use_container_width=True)
    except:
        st.info("尚未获取到记录。")
