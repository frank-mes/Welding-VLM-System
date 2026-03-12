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

# 3. 增强型推理引擎 (逻辑参数透明化)
def get_logic(mat, thick, meth, grade):
    # 【常量库/专家基准】
    # I_material: 不同材料的起始电流密度基准 (固定经验值)
    bm_lib = {
        "Q345R": {"base": 110, "info": "碳钢: 导热系数高，需较高起步能量"},
        "316L": {"base": 95, "info": "不锈钢: 导热差，起步电流需偏低以防过烧"},
        "S30408": {"base": 100, "info": "奥氏体钢: 热敏感性中等"}
    }
    # eta (η): 焊接方法热效率系数 (固定经验值)
    mf_lib = {"GMAW": 1.0, "GTAW": 0.8, "LBW": 1.5}
    
    # --- 逻辑推演过程 ---
    sel_bm = bm_lib.get(mat, {"base": 100, "info": "常规材料"})
    i_mat = sel_bm["base"]             # 来源: 专家库(基于材料选择)
    alpha = 12                         # 来源: 固定补偿常数 (12A/mm)
    i_thick = thick * alpha            # 来源: 输入(板厚) * alpha
    eta = mf_lib.get(meth, 1.0)        # 来源: 专家库(基于方法选择)
    delta = 0.95 if grade == "一级" else 1.0  # 来源: 逻辑判定(基于等级)
    
    # 核心计算 I = (I_mat + alpha * h) * eta * delta
    i_pure = (i_mat + i_thick) * eta * delta
    
    # 电压协同参数
    u_start = 18 if grade == "一级" else 16  # 来源: 等级基准
    k_slope = 40 if grade == "一级" else 45  # 来源: 等级硬度系数
    u_pure = u_start + (i_pure / k_slope)
    
    v_pure = 200 + (thick * 8)
    conf = (98.0 if grade == "一级" else 94.0) - (thick * 0.1)
    
    return {
        "i_mat": i_mat, "alpha": alpha, "i_thick": i_thick, 
        "eta": eta, "delta": delta, "u_start": u_start, "k": k_slope,
        "i_res": round(i_pure, 1), "u_res": round(u_pure, 1), 
        "v_res": v_pure, "c_res": round(conf, 1), "desc": sel_bm["info"]
    }

# 4. 侧边栏
st.sidebar.header("🛠 工艺特征输入")
v_mat = st.sidebar.selectbox("材料牌号 (Material)", ["Q345R", "316L", "S30408"])
v_thick = st.sidebar.slider("板厚 (Thickness/mm)", 2.0, 50.0, 10.0)
v_meth = st.sidebar.selectbox("焊接方法 (Method)", ["GMAW", "GTAW", "LBW"])
v_grade = st.sidebar.radio("质量等级 (Grade)", ["一级", "二级", "三级"])

# 5. 主页面标题
st.title("👨‍🏭 焊接工艺多模态专家系统")

# --- 优化点：详细参数解析表 ---
with st.expander("📘 核心能量推导准则 - 参数详细定义", expanded=True):
    st.write("### 物理模型：$I = (I_{mat} + \\alpha \cdot h) \cdot \eta \cdot \delta$")
    
    # 构造参数来源说明表
    param_data = {
        "符号": ["I_mat", "α (alpha)", "h", "η (eta)", "δ (delta)"],
        "名称": ["材料基准电流", "板厚补偿系数", "工件厚度", "热效率系数", "质量修正因子"],
        "数值来源": [
            f"专家库固定值 (当前: {v_mat}={get_logic(v_mat, v_thick, v_meth, v_grade)['i_mat']}A)",
            "系统内置常量 (固定值: 12A/mm)",
            f"用户实时输入 (当前: {v_thick}mm)",
            f"工艺方法映射 (当前: {v_meth}={get_logic(v_mat, v_thick, v_meth, v_grade)['eta']})",
            f"等级逻辑判定 (当前: {v_grade}={get_logic(v_mat, v_thick, v_meth, v_grade)['delta']})"
        ],
        "工程物理意义": [
            "维持材料单位熔池所需的起步能量",
            "用于对冲母材三维散热产生的热损失",
            "决定了热传导路径的长度",
            "反映焊接方法的能量集中程度 (激光>熔化极>氩弧)",
            "高等级焊缝需通过小电流减小热影响区(HAZ)"
        ]
    }
    st.table(pd.DataFrame(param_data))
    
    st.latex(r"U = U_{start} + I / k")
    st.caption("注：U_start(起始电压) 与 k(电弧斜率) 均根据质量等级自动切换固定基准。")



st.markdown("---")

# 6. 执行计算
res = get_logic(v_mat, v_thick, v_meth, v_grade)

# 7. 实例推理路径：微观细致化
st.subheader("📝 实例推理路径追踪")
c1, c2, c3 = st.columns(3)

up_f = st.file_uploader("上传坡口图片 (视觉感知)", type=["jpg", "png", "jpeg"])
v_delta = 8.0 if up_f else 0.0
f_i = round(res['i_res'] + v_delta, 1)

with c1:
    st.info("**电流 (I) 演变路径**")
    st.write(f"1. **材料基础**: {res['i_mat']} A")
    st.write(f"2. **厚度补偿**: +{res['i_thick']} A ($12 \\times {v_thick}$)")
    st.write(f"3. **效率/等级修正**: $\\times {res['eta']} \\times {res['delta']}$")
    if v_delta > 0: st.write(f"4. **VLM视觉加成**: +{v_delta} A")
    st.code(f"最终推荐 I = {f_i} A")

with c2:
    st.info("**电压 (U) 协同路径**")
    st.write(f"1. **等级基准 $U_s$**: {res['u_start']} V")
    st.write(f"2. **联动系数 $k$**: {res['k']}")
    st.write(f"3. **协同计算**: ${res['u_start']} + ({f_i} / {res['k']})$")
    st.code(f"最终推荐 U = {res['u_res']} V")

with c3:
    st.info("**速度 (V) 稳定性路径**")
    st.write("1. **初始线速**: 200 mm/min")
    st.write(f"2. **厚度熔敷修正**: +{v_thick} * 8")
    st.code(f"最终推荐 V = {res['v_res']} mm/min")



# 8. 看板
st.markdown("---")
r1, r2, r3, r4 = st.columns(4)
r1.metric("焊接电流", f"{f_i} A", delta=f"{v_delta}A (VLM)" if v_delta > 0 else None)
r2.metric("电弧电压", f"{res['u_res']} V")
r3.metric("焊接速度", f"{res['v_res']} mm/min")
r4.metric("预测合格率", f"{res['c_res']}%")

# 9. 云端同步 (字段完全对齐)
st.markdown("---")
h_list = ["Timestamp", "Material", "Thickness", "Method", "Grade", "VLM_Feedback", "Pred_Current", "Pred_Voltage", "Pred_Speed", "Actual_Result", "Expert_Score"]

with st.expander("🔄 生产反馈与数据闭环", expanded=True):
    f_c1, f_c2 = st.columns(2)
    a_res = f_c1.selectbox("实测结果", ["合格", "气孔", "未熔合", "咬边", "裂纹"])
    score = f_c2.slider("专家评分", 0, 100, 85)
    
    if st.button("🚀 提交并同步至云端", use_container_width=True):
        row = {
            "Timestamp": pd.Timestamp.now().strftime("%m-%d %H:%M"),
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

if st.checkbox("查看历史记录"):
    try:
        data = conn.read(spreadsheet=st.secrets["gsheets_url"], ttl=0)
        st.dataframe(data[h_list].tail(10), use_container_width=True)
    except: st.info("暂无记录")
