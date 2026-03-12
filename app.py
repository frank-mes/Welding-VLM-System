import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

# ==========================================
# 1. STYLE 层：CSS 样式定义
# ==========================================
def inject_custom_styles():
    st.markdown("""
        <style>
            .stMetric { background-color: #f0f2f6; padding: 10px; border-radius: 10px; }
            .stTable { font-size: 14px !important; }
            /* 确保字体与系统高度统一 */
            html, body, [class*="css"] { font-family: 'Segoe UI', sans-serif; }
        </style>
    """, unsafe_allow_html=True)

# ==========================================
# 2. DAO 层：数据持久化 (Data Access Object)
# ==========================================
class WeldingDAO:
    def __init__(self):
        self.h_list = ["Timestamp", "Material", "Thickness", "Method", "Grade", 
                       "VLM_Feedback", "Pred_Current", "Pred_Voltage", 
                       "Pred_Speed", "Actual_Result", "Expert_Score"]
        try:
            self.conn = st.connection("gsheets", type=GSheetsConnection)
            self.url = st.secrets["gsheets_url"]
        except:
            st.error("数据库连接初始化失败，请检查 Secrets 配置")

    def save_record(self, data_dict):
        df_o = self.conn.read(spreadsheet=self.url, ttl=0)
        df_n = pd.DataFrame([data_dict]).reindex(columns=self.h_list)
        self.conn.update(spreadsheet=self.url, data=pd.concat([df_o, df_n], ignore_index=True))

    def get_history(self, limit=15):
        df = self.conn.read(spreadsheet=self.url, ttl=0)
        return df[self.h_list].tail(limit)

# ==========================================
# 3. SERVICE 层：业务逻辑 (Business Logic)
# ==========================================
class WeldingService:
    @staticmethod
    def calculate_logic(mat, thick, meth, grade):
        # 核心物理专家库
        bm_lib = {
            "Q345R": {"i_mat": 110, "u_bias": 0.5, "v_f": 1.0, "r_mat": 0.2},
            "316L": {"i_mat": 95, "u_bias": -1.0, "v_f": 0.85, "r_mat": 0.8},
            "S30408": {"i_mat": 100, "u_bias": 0.0, "v_f": 0.92, "r_mat": 0.5}
        }
        mf_lib = {"GMAW": 1.0, "GTAW": 0.8, "LBW": 1.5}
        sel_bm = bm_lib.get(mat, {"i_mat": 100, "u_bias": 0, "v_f": 1.0, "r_mat": 0.5})
        
        # 物理公式计算
        eta = mf_lib.get(meth, 1.0)
        delta = 0.95 if grade == "一级" else 1.0
        u_base = 18 if grade == "一级" else 16
        k_slope = 40 if grade == "一级" else 45
        
        i_res = (sel_bm["i_mat"] + 12 * thick) * eta * delta
        u_res = u_base + sel_bm["u_bias"] + (i_res / k_slope)
        v_res = (450 - 5.5 * thick) * eta * sel_bm["v_f"]
        p_res = 99.8 - (0.15 * thick) - (1.5 if meth == "LBW" else 0.4) - sel_bm["r_mat"]
        
        return {
            "i_res": round(i_res, 1), "u_res": round(u_res, 1), 
            "v_res": round(v_res, 1), "c_res": round(p_res, 1),
            "i_mat": sel_bm["i_mat"], "u_adj": sel_bm["u_bias"], "v_f": sel_bm["v_f"], 
            "r_mat_risk": sel_bm["r_mat"], "eta": eta, "u_b": u_base, 
            "k": k_slope, "r_met": (1.5 if meth == "LBW" else 0.4), "delta": delta
        }

# ==========================================
# 4. CONTROLLER 层：主控展现 (Main Presentation)
# ==========================================
def main():
    st.set_page_config(page_title="焊接多模态专家系统", layout="wide")
    inject_custom_styles()
    
    # 实例化 DAO 和 Service
    dao = WeldingDAO()
    service = WeldingService()

    # --- 侧边栏输入 ---
    st.sidebar.header("🛠 工艺特征输入")
    v_mat = st.sidebar.selectbox("材料牌号", ["Q345R", "316L", "S30408"])
    v_thick = st.sidebar.number_input("材料厚度(mm)", min_value=0.5, max_value=100.0, value=10.0, step=0.1)
    v_meth = st.sidebar.selectbox("焊接方法", ["GMAW", "GTAW", "LBW"])
    v_grade = st.sidebar.radio("质量等级", ["一级", "二级", "三级"])

    # --- 主页面推导字典 ---
    st.title("👨‍🏭 焊接工艺多模态专家系统")
    res = service.calculate_logic(v_mat, v_thick, v_meth, v_grade)
    
    with st.expander("📘 全参数物理模型推导辞典 (1类常量 vs 2类变量)", expanded=True):
        C_SYS, V_MAT = "1类常量：固定值(系统内置常数)", "2类变量：随输入改变的变量(提示：与材料牌号输入有关)"
        V_THI, V_MET, V_GRA = "2类变量：随输入改变的变量(提示：与材料厚度输入有关)", "2类变量：随输入改变的变量(提示：与焊接方法输入有关)", "2类变量：随输入改变的变量(提示：与质量等级输入有关)"
        
        st.markdown("#### (1) 能量场模型 (I & U)")
        st.latex(r"I = (I_{mat} + 12 \cdot h) \cdot \eta \cdot \delta")
        iu_df = pd.DataFrame({
            "参数符号": ["I_mat", "12 (alpha)", "h (板厚)", "η (eta)", "δ (delta)", "U_base", "U_adj", "k"],
            "符号物理含义": ["材料起步电流基准", "单位厚度热补偿常数", "工件物理厚度值", "焊接方法热转换效率", "质量等级修正系数", "基准电压起始点", "材料电离能电压偏移", "电弧控制斜率"],
            "属性定义全称": [V_MAT, C_SYS, V_THI, V_MET, V_GRA, V_GRA, V_MAT, V_GRA],
            "实时数值": [f"{res['i_mat']}A", "12 A/mm", f"{v_thick}mm", f"{res['eta']}", f"{res['delta']}", f"{res['u_b']}V", f"{res['u_adj']}V", f"{res['k']}"]
        })
        st.table(iu_df)
        

        st.markdown("#### (2) 动力学与风险模型 (V & P)")
        st.latex(r"v = (450 - 5.5 \cdot h) \cdot \eta \cdot f_{mat}")
        vp_df = pd.DataFrame({
            "参数符号": ["450 (V_base)", "5.5 (V_drag)", "f_mat", "99.8 (P_base)", "0.15 (R_thick)", "R_meth", "R_mat"],
            "符号物理含义": ["线速度上限基准", "厚度填充阻力系数", "材料熔池流体因子", "理想起始合格率", "厚度风险常数", "方法稳定性风险", "材料冶金风险"],
            "属性定义全称": [C_SYS, C_SYS, V_MAT, C_SYS, C_SYS, V_MET, V_MAT],
            "实时数值": ["450mm/min", "5.5", f"{res['v_f']}", "99.8%", "0.15", f"-{res['r_met']}%", f"-{res['r_mat_risk']}%"]
        })
        st.table(vp_df)

    st.markdown("---")
    
    # --- 推荐参数与结果展示 (前端区域优化) ---
    st.subheader("🎯 实时推理推荐结果")
    with st.container(border=True):
        c_up1, c_up2 = st.columns([1, 2])
        with c_up1:
            up_f = st.file_uploader("视觉感知输入", type=["jpg", "png", "jpeg"])
            v_delta = 8.0 if up_f else 0.0
            final_i = round(res['i_res'] + v_delta, 1)
        with c_up2:
            st.markdown("**🔍 实例具体计算推导路径 (数值追踪)**")
            cp1, cp2, cp3 = st.columns(3)
            cp1.caption("电流 I 路径"); cp1.write(f"`({res['i_mat']}+12*{v_thick})*{res['eta']}*{res['delta']}`")
            cp2.caption("电压 U 路径"); cp2.write(f"`{res['u_b']}+{res['u_adj']}+({final_i}/{res['k']})`")
            cp3.caption("速度 V 路径"); cp3.write(f"`(450-5.5*{v_thick})*{res['eta']}*{res['v_f']}`")
        
        st.divider()
        r1, r2, r3, r4 = st.columns(4)
        r1.metric("推荐电流 (Current)", f"{final_i} A", delta=f"+{v_delta}A VLM" if v_delta > 0 else None)
        r2.metric("推荐电压 (Voltage)", f"{res['u_res']} V")
        r3.metric("推荐速度 (Speed)", f"{res['v_res']} mm/min")
        r4.metric("预测合格率 (Yield)", f"{res['c_res']}%", delta_color="inverse")

    # --- 反馈与历史记录 ---
    st.markdown("---")
    with st.expander("🔄 生产反馈与数据同步", expanded=True):
        f_c1, f_c2 = st.columns(2)
        a_res = f_c1.selectbox("质检实际结果", ["合格", "气孔", "未熔合", "咬边", "裂纹"])
        score = f_c2.slider("专家评分", 0, 100, 85)
        if st.button("🚀 提交并同步", use_container_width=True):
            record = {"Timestamp": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M"), "Material": v_mat, "Thickness": v_thick, "Method": v_meth, "Grade": v_grade, "VLM_Feedback": "Yes" if up_f else "No", "Pred_Current": final_i, "Pred_Voltage": res['u_res'], "Pred_Speed": res['v_res'], "Actual_Result": a_res, "Expert_Score": score}
            dao.save_record(record)
            st.success("✅ 数据已同步至云端 DAO 层"); st.balloons()

    st.markdown("---")
    c_link1, c_link2 = st.columns([1, 4])
    show_hist = c_link1.checkbox("🔍 查看历史记录")
    try: c_link2.link_button("🌐 打开云端原始数据页面", dao.url)
    except: pass

    if show_hist:
        latest_data = dao.get_history(15)
        event = st.dataframe(latest_data, use_container_width=True, on_select="rerun", selection_mode="single-row")
        if len(event.selection.rows) > 0:
            row_data = latest_data.iloc[event.selection.rows[0]]
            with st.container(border=True):
                st.subheader(f"📄 历史记录详情 - {row_data['Timestamp']}")
                d1, d2, d3 = st.columns(3)
                d1.write(f"**材料**: {row_data['Material']} | {row_data['Thickness']}mm")
                d2.write(f"**方法**: {row_data['Method']} | {row_data['Grade']}")
                d3.write(f"**质检**: {row_data['Actual_Result']} | 评分:{row_data['Expert_Score']}")
                if st.button("关闭详情"): st.rerun()

if __name__ == "__main__":
    main()
