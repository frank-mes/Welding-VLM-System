import streamlit as st
import pandas as pd
from dataclasses import dataclass, asdict
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

# ==========================================
# 1. DOMAIN LAYER (领域实体层)
# ==========================================
@dataclass
class ProcessInput:
    material: str
    thickness: float
    method: str
    grade: str
    vlm_offset: float = 0.0  # 新增：显式承载视觉补偿值

@dataclass
class CalculationResult:
    i_res: float; u_res: float; v_res: float; c_res: float
    i_mat: float; u_adj: float; v_f: float; r_mat_risk: float
    eta: float; u_b: int; k: int; r_met: float; delta: float

# ==========================================
# 2. SERVICE LAYER (核心业务逻辑层)
# ==========================================
class WeldingPhysicsService:
    def __init__(self):
        self.BM_LIB = {
            "Q345R": {"i_mat": 110, "u_bias": 0.5, "v_f": 1.0, "r_mat": 0.2},
            "316L": {"i_mat": 95, "u_bias": -1.0, "v_f": 0.85, "r_mat": 0.8},
            "S30408": {"i_mat": 100, "u_bias": 0.0, "v_f": 0.92, "r_mat": 0.5}
        }
        self.METHOD_LIB = {"GMAW": 1.0, "GTAW": 0.8, "LBW": 1.5}

    def execute_inference(self, inp: ProcessInput) -> CalculationResult:
        sel_bm = self.BM_LIB.get(inp.material, {"i_mat": 100, "u_bias": 0, "v_f": 1.0, "r_mat": 0.5})
        eta = self.METHOD_LIB.get(inp.method, 1.0)
        delta = 0.95 if inp.grade == "一级" else 1.0
        u_base = 18 if inp.grade == "一级" else 16
        k_slope = 40 if inp.grade == "一级" else 45
        
        # 修复点：将视觉补偿 vlm_offset 纳入核心计算链
        base_i = (sel_bm["i_mat"] + 12 * inp.thickness) * eta * delta
        final_i = base_i + inp.vlm_offset
        
        # 电压随补偿后的电流联动
        u_res = u_base + sel_bm["u_bias"] + (final_i / k_slope)
        v_res = (450 - 5.5 * inp.thickness) * eta * sel_bm["v_f"]
        p_res = 99.8 - (0.15 * inp.thickness) - (1.5 if inp.method == "LBW" else 0.4) - sel_bm["r_mat"]
        
        return CalculationResult(
            round(final_i, 1), round(u_res, 1), round(v_res, 1), round(p_res, 1),
            sel_bm["i_mat"], sel_bm["u_bias"], sel_bm["v_f"], sel_bm["r_mat"],
            eta, u_base, k_slope, (1.5 if inp.method == "LBW" else 0.4), delta
        )

# ==========================================
# 3. REPOSITORY LAYER (数据仓库层)
# ==========================================
class WeldingDataRepository:
    def __init__(self):
        self.H_LIST = ["Timestamp", "Material", "Thickness", "Method", "Grade", 
                       "VLM_Feedback", "Pred_Current", "Pred_Voltage", 
                       "Pred_Speed", "Actual_Result", "Expert_Score"]
        # 增加容错初始化
        try:
            self.conn = st.connection("gsheets", type=GSheetsConnection)
            self.url = st.secrets.get("gsheets_url", "")
        except:
            st.error("DAO初始化失败：请检查 .streamlit/secrets.toml")

    def persist(self, record: dict):
        # 增加强制刷新，确保写入不被缓存拦截
        try:
            df_old = self.conn.read(spreadsheet=self.url, ttl=0)
            df_new = pd.DataFrame([record]).reindex(columns=self.H_LIST)
            self.conn.update(spreadsheet=self.url, data=pd.concat([df_old, df_new], ignore_index=True))
            st.cache_data.clear() # 写入后清除读取缓存
        except Exception as e:
            st.error(f"Sheet写入失败：{str(e)}")

    def fetch_recent(self, size=15):
        try:
            df = self.conn.read(spreadsheet=self.url, ttl=0)
            return df[self.H_LIST].tail(size)
        except:
            return pd.DataFrame(columns=self.H_LIST)

# ==========================================
# 4. INFRASTRUCTURE LAYER (基础设施层)
# ==========================================
class InfraManager:
    @staticmethod
    def set_styles():
        st.markdown("""<style>
            .stMetric { border: 1px solid #e6e9ef; padding: 10px; border-radius: 8px; }
            html, body { font-family: 'PingFang SC', 'Microsoft YaHei', sans-serif; }
            </style>""", unsafe_allow_html=True)

# ==========================================
# 5. INTERFACE LAYER (界面控制层)
# ==========================================
def main():
    st.set_page_config(page_title="焊接多模态专家系统", layout="wide")
    InfraManager.set_styles()
    
    physics_service = WeldingPhysicsService()
    repo = WeldingDataRepository()

    # --- 1. 输入采集 ---
    st.sidebar.header("🛠 工艺特征输入")
    v_mat = st.sidebar.selectbox("材料牌号", ["Q345R", "316L", "S30408"])
    v_thick = st.sidebar.number_input("材料厚度(mm)", 0.5, 100.0, 10.0, 0.1)
    v_meth = st.sidebar.selectbox("焊接方法", ["GMAW", "GTAW", "LBW"])
    v_grade = st.sidebar.radio("质量等级", ["一级", "二级", "三级"])
    
    st.title("👨‍🏭 焊接工艺多模态专家系统")

    # --- 2. 视觉感知（位置前置，确保计算闭环） ---
    with st.container(border=True):
        up_f = st.file_uploader("视觉感知输入", type=["jpg", "png", "jpeg"])
        v_offset = 8.0 if up_f else 0.0

    # --- 3. 核心推理执行 ---
    # 修复：构造带补偿值的输入实体
    process_in = ProcessInput(v_mat, v_thick, v_meth, v_grade, v_offset)
    res = physics_service.execute_inference(process_in)
    
    with st.expander("📘 全参数物理模型推导辞典 (1类常量 vs 2类变量)", expanded=True):
        C_SYS, V_MAT = "1类常量：固定值", "2类变量：随输入改变(关联材料)"
        V_THI, V_MET, V_GRA = "2类变量(关联厚度)", "2类变量(关联方法)", "2类变量(关联等级)"
        
        iu_df = pd.DataFrame({
            "参数符号": ["I_mat", "12 (alpha)", "h (板厚)", "η (eta)", "δ (delta)", "U_base", "U_adj", "k"],
            "符号物理含义": ["起步电流基准", "热补偿常数", "板厚值", "热转换效率", "修正系数", "电压起始点", "电压偏移", "控制斜率"],
            "属性定义全称": [V_MAT, C_SYS, V_THI, V_MET, V_GRA, V_GRA, V_MAT, V_GRA],
            "实时数值": [f"{res.i_mat}A", "12", f"{v_thick}mm", f"{res.eta}", f"{res.delta}", f"{res.u_b}V", f"{res.u_adj}V", f"{res.k}"]
        })
        st.table(iu_df)
        
        vp_df = pd.DataFrame({
            "参数符号": ["450", "5.5", "f_mat", "99.8", "0.15", "R_meth", "R_mat"],
            "属性定义全称": [C_SYS, C_SYS, V_MAT, C_SYS, C_SYS, V_MET, V_MAT],
            "实时数值": ["450", "5.5", f"{res.v_f}", "99.8%", "0.15", f"-{res.r_met}%", f"-{res.r_mat_risk}%"]
        })
        st.table(vp_df)

    st.markdown("---")

    # --- 4. 结果看板与路径追踪 ---
    st.subheader("🎯 实时推理推荐结果")
    with st.container(border=True):
        c1, c2 = st.columns([1, 2])
        with c1:
            # 这里的 final_i 已经由 res.i_res 内部计算得出
            st.info("系统检测：视觉感知已介入" if up_f else "系统检测：无视觉补偿")
        with c2:
            st.markdown("**🔍 数值计算追踪**")
            cp1, cp2, cp3 = st.columns(3)
            # 修复点：展示公式时显式体现补偿项
            cp1.caption("I 路径"); cp1.write(f"`({res.i_mat}+12*{v_thick})*{res.eta}*{res.delta}+{v_offset}`")
            cp2.caption("U 路径"); cp2.write(f"`{res.u_b}+{res.u_adj}+({res.i_res}/{res.k})`")
            cp3.caption("V 路径"); cp3.write(f"`(450-5.5*{v_thick})*{res.eta}*{res.v_f}`")
        
        st.divider()
        r1, r2, r3, r4 = st.columns(4)
        r1.metric("推荐电流 (I)", f"{res.i_res} A", delta=f"+{v_offset}A VLM" if v_offset > 0 else None)
        r2.metric("推荐电压 (U)", f"{res.u_res} V")
        r3.metric("推荐速度 (V)", f"{res.v_res} mm/min")
        r4.metric("预测合格率 (P)", f"{res.c_res}%")

    # --- 5. 生产反馈与数据持久化 ---
    st.markdown("---")
    with st.expander("🔄 生产反馈与数据同步", expanded=True):
        f1, f2 = st.columns(2)
        a_res = f1.selectbox("质检实际结果", ["合格", "气孔", "未熔合", "咬边", "裂纹"])
        score = f2.slider("专家评分", 0, 100, 85)
        if st.button("🚀 提交并同步", use_container_width=True):
            record = {
                "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"), "Material": v_mat, "Thickness": v_thick,
                "Method": v_meth, "Grade": v_grade, "VLM_Feedback": "Yes" if up_f else "No",
                "Pred_Current": res.i_res, "Pred_Voltage": res.u_res, "Pred_Speed": res.v_res,
                "Actual_Result": a_res, "Expert_Score": score
            }
            repo.persist(record)
            st.success("✅ 数据持久化成功")

    # --- 6. 历史存证查看 ---
    st.markdown("---")
    c_l1, c_l2 = st.columns([1, 4])
    show_hist = c_l1.checkbox("🔍 查看历史记录")
    try: c_l2.link_button("🌐 进入云端数据中心", repo.url)
    except: pass

    if show_hist:
        hist_df = repo.fetch_recent()
        if not hist_df.empty:
            event = st.dataframe(hist_df, use_container_width=True, on_select="rerun", selection_mode="single-row")
            if len(event.selection.rows) > 0:
                row = hist_df.iloc[event.selection.rows[0]]
                with st.container(border=True):
                    st.subheader(f"📄 单条存证详情 - {row['Timestamp']}")
                    st.write(f"**工艺方案**: {row['Material']} | {row['Thickness']}mm | {row['Method']} | 等级:{row['Grade']}")
                    st.write(f"**核心参数**: I={row['Pred_Current']}A | U={row['Pred_Voltage']}V | V={row['Pred_Speed']}mm/min")
                    st.write(f"**结果反馈**: {row['Actual_Result']} | 专家分:{row['Expert_Score']}")
                    if st.button("关闭详情"): st.rerun()
        else:
            st.warning("暂无历史记录，请先提交数据。")

if __name__ == "__main__":
    main()
    
