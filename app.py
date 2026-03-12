import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

# 1. 配置
st.set_page_config(page_title="焊接优化系统", layout="wide")

# 2. 数据库连接
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except Exception:
    st.error("数据库连接异常")

# 3. 计算引擎
def get_welding_logic(mat, thick, meth, grade):
    # 专家规则库
    base_m = {"Q345R": 110, "316L": 95, "S30408": 100}
    meth_f = {"GMAW": 1.0, "GTAW": 0.8, "LBW": 1.5}
    
    i_base = base_m.get(mat, 100)
    i_thick = thick * 12
    m_factor = meth_f.get(meth, 1.0)
    g_mod = 0.95 if grade == "一级" else 1.0
    
    # 核心公式计算
    curr_base = (i_base + i_thick) * m_factor * g_mod
    volt = (18 + curr_base/40) if grade == "一级" else (16 + curr_base/45)
    speed = 200 + (thick * 8)
    
    steps = {"base": i_base, "thick": i_thick, "f": m_factor, "mod": g_mod}
    return round(curr_base, 1), round(volt, 1), round(speed, 1), steps

# 4. 侧边栏输入
st.sidebar.header("🛠 输入参数")
in_mat = st.sidebar.selectbox("材料", ["Q345R", "316L", "S30408"])
in_thick = st.sidebar.slider("厚度(mm)", 2.0, 50.0, 10.0)
in_meth = st.sidebar.selectbox("方法", ["GMAW", "GTAW", "LBW"])
in_grade = st.sidebar.radio("等级", ["一级", "二级", "三级"])

# 5. 主页面
st.title("👨‍🏭 焊接工艺多模态优化系统")
st.markdown("---")

# 执行逻辑
curr, volt, spd, stp = get_welding_logic(in_mat, in_thick, in_meth, in_grade)

# 6. 视觉感知与计算推演
st.subheader("📝 推演过程与视觉对齐")
v_c1, v_c2 = st.columns([1, 1])

with v_c1:
    up_f = st.file_uploader("上传照片", type=["jpg", "png", "jpeg"])
    v_comp = 5.0 if up_f else 0.0
    if up_f:
        st.image(up_f, caption="采样样本", use_container_width=True)
    else:
        st.info("📢 等待图片上传激活补偿")

with v_c2:
    final_i = curr + v_comp
    st.write("**当前实例具体计算路径：**")
    st.markdown(f"- 1.基准电流: `{stp['base']}A`")
    st.markdown(f"- 2.厚度增益: `+{stp['thick']}A`")
    st.markdown(f"- 3.工艺修正: `x{stp['f']} (方法) | x{stp['mod']} (等级)`")
    st.markdown(f"- 4.视觉补偿: `+{v_comp}A`")
    st.code(f"计算: ({stp['base']}+{stp['thick']})*{stp['f']}*{stp['mod']}+{v_comp} = {final_i}A")



# 7. 推荐结果
st.markdown("---")
st.subheader("🚀 推荐工艺参数 (Final Output)")
c1, c2, c3 = st.columns(3)
c1.metric("电流 (I)", f"{final_i} A", delta=f"{v_comp}A" if v_comp > 0 else None)
c2.metric("电压 (U)", f"{volt} V")
c3.metric("速度 (V)", f"{spd} mm/min")

# 8. 反馈存证
st.markdown("---")
cols = ["Timestamp", "Mat", "Thick", "Meth", "Grade", "VLM", "I", "U", "V", "Result", "Score"]

with st.expander("🔄 质量反馈同步", expanded=True):
    f1, f2 = st.columns(2)
    # 缩短选项内容防止断行报错
    res_act = f1.selectbox("质检结果", ["合格", "气孔", "未熔合", "咬边", "裂纹"])
    score = f2.slider("专家打分", 0, 100, 85)
    
    if st.button("🚀 提交数据", use_container_width=True):
        new_d = {
            "Timestamp": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M"),
            "Mat": in_mat, "Thick": in_thick, "Meth": in_meth, "Grade": in_grade,
            "VLM": "Yes" if up_f else "No", "I": final_i, "U": volt, "V": spd,
            "Result": res_act, "Score": score
        }
        try:
            u = st.secrets["gsheets_url"]
            df_o = conn.read(spreadsheet=u, ttl=0)
            df_n = pd.DataFrame([new_d])[cols]
            df_f = pd.concat([df_o, df_n], ignore_index=True)
            conn.update(spreadsheet=u, data=df_f)
            st.success("✅ 同步成功")
            st.balloons()
        except Exception as e:
            st.error(f"异常: {e}")

# 9. 数据预览
if st.checkbox("查看云端记录"):
    try:
        data = conn.read(spreadsheet=st.secrets["gsheets_url"], ttl=0)
        st.dataframe(data.tail(5), use_container_width=True)
    except:
        st.write("无记录")
        
