# 焊接多模态专家系统 (Welding Expert System)

基于物理模型与视觉感知的焊接工艺参数推理平台。

## 🚀 核心功能
- **物理推理**：集成 I/U/V 核心路径算法。
- **视觉补偿**：支持 VLM 视觉反馈介入。
- **数据存证**：对接 Google Sheets 实现生产数据云端同步。

## 🛠️ 环境配置
- Python 3.11
- 主要依赖：`streamlit`, `pandas`, `st-gsheets-connection`

## 📊 数据连接
部署时需在 Secrets 中配置 `gsheets_url`。
