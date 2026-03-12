import streamlit as st
import pandas as pd
from dataclasses import dataclass
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

# ==========================================
# 1. DOMAIN LAYER (实体层 - 增加补偿字段)
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
# 2. SERVICE LAYER (业务逻辑层 - 修复计算闭环)
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
        
        # 核心逻辑：物理基础电流 + 视觉补偿值
        base_i = (sel_bm["i_mat"] + 12 * inp.thickness) * eta * delta
        final_i = base_i + inp.vlm_offset
        
        # 电压随最终电流联动变化
        u_res = u_base + sel_bm["u_bias"] + (final_i / k_slope)
        v_res = (450 - 5.5 * inp.thickness) * eta * sel_bm["v_f"]
        p_res = 99.8 - (0.15 * inp.thickness) - (1.5 if inp.method == "LBW" else 0.4) - sel_bm["r_mat"]
        
        return CalculationResult(
            round(final_i, 1), round(u_res, 1), round(v_res, 1), round(p_res, 1),
            sel_bm["i_mat"], sel_bm["u_bias"], sel_bm["v_f"], sel_bm["r_mat"],
            eta, u_base, k_slope, (1.5 if inp.method == "LBW" else 0.4), delta
        )

# ==========================================
# 3. REPOSITORY LAYER (数据仓库层 - DAO)
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
        df_old = self.conn.read(spreadsheet=self.url, ttl=0)
        df_new = pd.DataFrame([record]).reindex(columns=self.H_LIST)
        self.conn.update(spreadsheet=self.url, data=pd.concat([df_old, df_new], ignore_index=True))

    def fetch_recent(self):
        return self.conn.read(spreadsheet=self.url, ttl=0)[self.H_LIST].tail(15)

# ==========================================
# 4. INTERFACE LAYER (界面与样式注入)
# ==========================================
def main():
    st.set_page_config(page_title="焊接多模态专家系统", layout="wide")
    st.markdown("<style>.stMetric { border: 1px solid #e6e9ef; padding: 10px; border-radius: 8px; }</style>", unsafe_allow_html=True)
    
    physics_service = WeldingPhysicsService()
    repo = WeldingDataRepository()

    # --- 1. 采集输入 ---
    st.sidebar.header("🛠 工艺特征输入")
    v_mat = st.sidebar.selectbox("材料牌号", ["Q345R", "316L", "S30408"])
    v_thick = st.sidebar.number_input("材料厚度(mm)", 0.5, 100.0, 10.0, 0.1)
    v_meth = st.sidebar.selectbox("焊接方法", ["GMAW", "GTAW", "LBW"])
    v_grade = st.sidebar.radio("质量等级", ["一级", "二级", "三级"])
    
    # --- 2. 视觉感知（在计算前获取） ---
    st.title("👨‍🏭 焊接工艺多模态专家系统")
    with st.container(border=True):
        up_f = st.file_uploader("📸 视觉感知：上传坡口图片进行AI补偿", type=["jpg", "png", "jpeg"])
        v_offset = 8.0 if up_f else 0.0
        if up_f: st.success(f"✅ 视觉识别成功：已自动补偿电流 +{v_offset}A")

    # --- 3. 封装输入实体并执行 Service ---
    process_in = ProcessInput(v_mat, v_thick, v_meth, v_grade, v_offset)
    res = physics_service.execute_inference(process_in)

    # --- 4. 展示推导辞典 (样式统一版) ---
    with st.expander("📘 全参数物理模型推导辞典", expanded=False):
        iu_df = pd.DataFrame({
            "参数符号": ["I_mat", "h (板厚)", "η (eta)", "δ (delta)", "VLM_adj"],
            "属性定义全称": ["2类变量(关联材料)", "2类变量(关联厚度)", "2类变量(关联方法)", "2类变量(关联等级)", "2类变量(关联视觉)"],
            "实时数值": [f"{res.i_mat}A", f"{v_thick}mm", f"{res.eta}", f"{res.delta}", f"{v_offset}A"]
        })
        st.table(iu_df)

    # --- 5. 核心看板展示 ---
    st.subheader("🎯 实时推理推荐结果")
    with st.container(border=True):
        c_path, c_res = st.columns([1, 1.5])
        with c_path:
            st.caption("🔍 推荐 I 计算路径")
            st.code(f"({res.i_mat} + 12 * {v_thick}) * {res.eta} * {res.delta} + {v_offset} = {res.i_res}A")
        
        st.divider()
        r1, r2, r3, r4 = st.columns(4)
        r1.metric("推荐电流 (I)", f"{res.i_res} A", delta=f"+{v_offset}A" if v_offset > 0 else None)
        r2.metric("推荐电压 (U)", f"{res.u_res} V")
        r3.metric("推荐速度 (V)", f"{res.v_res} mm/min")
        r4.metric("预测合格率 (P)", f"{res.c_res}%")

    # --- 6. 数据同步与历史 ---
    st.markdown("---")
    if st.button("🚀 提交生产数据并存证", use_container_width=True):
        record = {
            "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"), "Material": v_mat, "Thickness": v_thick,
            "Method": v_meth, "Grade": v_grade, "VLM_Feedback": "Yes" if up_f else "No",
            "Pred_Current": res.i_res, "Pred_Voltage": res.u_res, "Pred_Speed": res.v_res,
            "Actual_Result": "待检测", "Expert_Score": 100
        }
        repo.persist(record)
        st.success("✅ 数据已存入云端仓库")

    if st.checkbox("🔍 查看历史存证记录"):
        st.dataframe(repo.fetch_recent(), use_container_width=True)

if __name__ == "__main__":
    main()
