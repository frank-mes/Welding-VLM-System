import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

# 1. 基础配置
st.set_page_config(page_title="焊接多模态系统", layout="wide")

# 2. 数据库连接
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except Exception:
    st.error("数据库连接失败")

# 3. 专家推理引擎
def get_logic(mat, thick, meth, grade):
    # 专家规则
    bm = {"Q345R": 110, "316L": 95, "S30408": 100}
    mf = {"GMAW": 1.0, "GTAW": 0.8, "LBW": 1.5}
    
    ib = bm.get(mat, 100)
    it = thick * 12
    fac = mf.get(meth, 1.0)
    mod = 0.95 if grade == "一级" else 1.0
    
    # 执行推演
    ires = (ib + it) * fac * mod
    ures = (18 + ires/40) if grade == "一级" else (16 + ires/45)
    vres = 200 + (thick * 8)
    
    # 成功率预测
    conf = (98.0 if grade == "一级" else 94.0) - (thick * 0.1)
    
    return round(ires,1), round(ures,1), vres, round(conf,1), ib, it, fac, mod

# 4. 侧边栏
st.sidebar.header("参数输入")
v_mat = st.sidebar.selectbox("材料牌号", ["Q345R", "316L", "S30408"])
v_thick = st.sidebar.slider("板厚(mm)", 2.0, 50.0, 10.0)
v_meth = st.sidebar.selectbox("焊接方法", ["GMAW", "GTAW", "LBW"])
v_grade = st.sidebar.radio("质量等级", ["一级", "二级", "三级"])

# 5. 主页面标题与宏观逻辑
st.title("焊接工艺多模态优化系统")

with st.expander("📘 查看宏观专家知识逻辑", expanded=False):
    st.markdown("### 物理推导模型")
    st.latex(r"I = (I_{base} + 12h) \cdot \eta \cdot \delta")
    st.latex(r"U = U_{c} + I/k")
    st.write("注：电流补偿热损，电压维持电弧稳定。")

st.markdown("---")

# 6. 计算
iv, uv, vv, cv, b, t, f, m = get_logic(v_mat, v_thick, v_meth, v_grade)

# 7. 实例推理路径 (修复 75 行附近的语法风险)
st.subheader("📝 实例具体计算推导路径")
c1, c2, c3 = st.columns(3)

up_f = st.file_uploader("上传坡口图片", type=["jpg", "png", "jpeg"])
v_d = 5.0 if up_f else 0.0
final_i = round(iv + v_d, 1)

with c1:
    st.info("电流推导路径")
    st.code(f"计算: ({b} + {t}) * {f} * {m}\n视觉: +{v_d}\n结果: {final_i} A")

with c2:
    # 彻底隔离中文字符串，防止 SyntaxError
    st.info("电压推导路径")
    u_base = 18 if v_grade == "一级" else 16
    st.code(f"计算: {u_base} + ({final_i} / K)\n结果: {uv} V")

with c3:
    st.info("速度推导路径")
    st.code(f"计算: 200 + ({v_thick} * 8)\n结果: {vv} mm/min")



# 8. 核心看板
st.markdown("---")
st.subheader("🚀 推荐工艺结果")
r1, r2, r3, r4 = st.columns(4)
r1.metric("焊接电流", f"{final_i} A", delta=f"{v_d}A" if v_d > 0 else None)
r2.metric("电弧电压", f"{uv} V")
r3.metric("焊接速度", f"{vv}")
r4.metric("预测合格率", f"{cv}%")

# 9. 云端同步
st.markdown("---")
target_headers = [
    "Timestamp", "Material", "Thickness", "Method", "Grade", 
    "VLM_Feedback", "Pred_Current", "Pred_Voltage", "Pred_Speed", 
    "Actual_Result", "Expert_Score"
]

with st.expander("🔄 质量反馈录入", expanded=True):
    f_c1, f_c2 = st.columns(2)
    with f_c1:
        act_res = st.selectbox("实测质检结果", ["合格", "气孔", "未熔合", "咬边", "裂纹"])
    with f_c2:
        expert_score = st.slider("专家评分", 0, 100, 85)
    
    if st.button("🚀 提交数据", use_container_width=True):
        new_row = {
            "Timestamp": pd.Timestamp.now().strftime("%m-%d %H:%M"),
            "Material": v_mat, "Thickness": v_thick, "Method": v_meth,
            "Grade": v_grade, "VLM_Feedback": "Yes" if up_f else "No",
            "Pred_Current": final_i, "Pred_Voltage": uv,
            "Pred_Speed": vv, "Actual_Result": act_res, "Expert_Score": expert_score
        }
        try:
            url = st.secrets["gsheets_url"]
            df_old = conn.read(spreadsheet=url, ttl=0)
            df_new = pd.DataFrame([new_row]).reindex(columns=target_headers)
            df_final = pd.concat([df_old, df_new], ignore_index=True)
            conn.update(spreadsheet=url, data=df_final)
            st.success("✅ 同步完成")
            st.balloons()
        except Exception as e:
            st.error(f"同步异常: {e}")

# 10. 历史展示
if st.checkbox("查看历史记录"):
    try:
        data = conn.read(spreadsheet=st.secrets["gsheets_url"], ttl=0)
        st.dataframe(data[target_headers].tail(10), use_container_width=True)
    except:
        st.info("暂无记录")
