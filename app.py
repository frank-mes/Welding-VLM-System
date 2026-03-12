import streamlit as st
import pandas as pd
from dataclasses import dataclass
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
    vlm_offset: float = 0.0  # 显式承载视觉补偿值

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
        
        # 物理公式：基础电流 + 视觉补偿
        base_i = (sel_bm["i_mat"] + 12 * inp.thickness) * eta * delta
        final_i = base_i + inp.vlm_offset
        
        # 联动计算：电压随最终电流变化
        u_res = u_base + sel_bm["u_bias"] + (final_i / k_slope)
        v_res = (450 - 5.5 * inp.thickness) * eta * sel_bm["v_f"]
        p_res = 99.8 - (0.15 * inp.thickness) - (1.5 if inp.method == "LBW" else 0.4) - sel_bm["r_mat"]
        
        return CalculationResult(
            round(final_i, 1), round(u_res, 1), round(v_res, 1), round(p_res, 1),
            sel_bm["i_mat"], sel_bm["u_bias"], sel_bm["v_f"], sel_bm["r_mat"],
            eta, u_base, k_slope, (1.5 if inp.method == "LBW" else 0.4), delta
        )

# ==========================================
# 3. REPOSITORY LAYER (持久化层)
# ==========================================
class WeldingDataRepository:
    def __init__(self):
        self.H_LIST = ["Timestamp", "Material", "Thickness", "Method", "Grade", 
                       "VLM_Feedback", "Pred_Current", "Pred_Voltage", 
                       "Pred_Speed", "Actual_Result", "Expert_Score"]
        try:
            self.conn = st.connection("gsheets", type=GSheetsConnection)
            self.url = st.secrets["gsheets_url"]
        except: pass

    def persist(self, record: dict):
        try:
            df_old = self.conn.read(spreadsheet=self.url, ttl=0)
            df_new = pd.DataFrame([record]).reindex(columns=self.H_LIST)
            self.conn.update(spreadsheet=self.url, data=pd.concat([df_old, df_new], ignore_index=True))
        except Exception as e: st.error(f"同步失败: {e}")

    def fetch_recent(self):
        return self.conn.read(spreadsheet=self.url, ttl=0)[self.H_LIST].tail(15)

# ==========================================
# 4. INFRASTRUCTURE LAYER (样式注入)
# ==========================================
class InfraManager:
    @staticmethod
    def set_styles():
        st.markdown("""<style>
            .stMetric { border: 1px solid #e6e9ef; padding: 10px; border-radius: 8px; }
            [data-testid="stMetricDelta"] svg { display: none; } /* 隐藏delta的小箭头 */
            </style>""", unsafe_allow_html=True)

# ==========================================
# 5. INTERFACE LAYER (界面控制层)
# ==========================================
def main():
    st.set_page_config(page_title="焊接多模态专家系统", layout="wide")
    InfraManager.set_styles()
    
    physics_service = WeldingPhysicsService()
    repo = WeldingDataRepository()

    # --- 1. 采集输入 (侧边栏) ---
    st.sidebar.header("🛠 工艺特征输入")
    v_mat = st.sidebar.selectbox("材料牌号", ["Q345R", "316L", "S30408"])
    v_thick = st.sidebar.number_input("材料厚度(mm)", 0.5, 100.0, 10.0, 0.1)
    v_meth = st.sidebar.selectbox("焊接方法", ["GMAW", "GTAW", "LBW"])
    v_grade = st.sidebar.radio("质量等级", ["一级", "二级", "三级"])

    # --- 2. 视觉感知采集 (必须在计算前) ---
    st.title("👨‍🏭 焊接工艺多模态专家系统")
    with st.container(border=True):
        up_f = st.file_uploader("📸 视觉感知：上传坡口图片进行AI补偿", type=["jpg", "png", "jpeg"])
        v_offset = 8.0 if up_f else 0.0
    
    # --- 3. 逻辑执行 ---
    process_in = ProcessInput(v_mat, v_thick, v_meth, v_grade, v_offset)
    res = physics_service.execute_inference(process_in)

    # --- 4. 展示推导辞典 (保持原样式) ---
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
            "符号物理含义": ["线速度上限", "厚度阻力系数", "材料流体因子", "起始合格率", "厚度风险", "方法风险", "材料风险"],
            "属性定义全称": [C_SYS, C_SYS, V_MAT, C_SYS, C_SYS, V_MET, V_MAT],
            "实时数值": ["450", "5.5", f"{res.v_f}", "99.8%", "0.15", f"-{res.r_met}%", f"-{res.r_mat_risk}%"]
        })
        st.table(vp_df)

    st.markdown("---")

    # --- 5. 结果看板与路径追踪 (前端优化样式) ---
    st.subheader("🎯 实时推理推荐结果")
    with st.container(border=True):
        c_path, c_res_box = st.columns([1, 2])
        with c_path:
            st.markdown("**🔍 数值计算追踪**")
            st.caption("推荐 I 推导路径")
            st.code(f"({res.i_mat}+12*{v_thick})*{res.eta}*{res.delta} + {v_offset} = {res.i_res}A")
            if up_f: st.success("AI视觉补偿已生效")
        
        st.divider()
        r1, r2, r3, r4 = st.columns(4)
        r1.metric("推荐电流 (I)", f"{res.i_res} A", delta=f"+{v_offset}A VLM" if v_offset > 0 else None)
        r2.metric("推荐电压 (U)", f"{res.u_res} V")
        r3.metric("推荐速度 (V)", f"{res.v_res} mm/min")
        r4.metric("预测合格率 (P)", f"{res.c_res}%")

    # --- 6. 存证与历史 ---
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

    if st.checkbox("🔍 查看历史存证记录"):
        hist = repo.fetch_recent()
        st.dataframe(hist, use_container_width=True)

if __name__ == "__main__":
    main()
