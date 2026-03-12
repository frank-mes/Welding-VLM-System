if st.button("🚀 提交反馈并同步云端", use_container_width=True):
        # 1. 强制列顺序定义（这就是你的表头）
        target_columns = [
            "Timestamp", "Material", "Thickness", "Method", 
            "Grade", "VLM_Feedback", "Actual_Result", "Expert_Score"
        ]
        
        new_row = {
            "Timestamp": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"),
            "Material": material_type,
            "Thickness": thickness,
            "Method": method,
            "Grade": grade,
            "VLM_Feedback": vlm_analysis,
            "Actual_Result": actual_res,
            "Expert_Score": expert_score
        }
        
        try:
            url = st.secrets["gsheets_url"]
            
            # 读取现有数据
            try:
                existing_df = conn.read(spreadsheet=url)
            except:
                # 如果表格全空，创建一个带表头的空表
                existing_df = pd.DataFrame(columns=target_columns)
            
            # 创建新行 DataFrame 并锁定列顺序
            new_df = pd.DataFrame([new_row])[target_columns]
            
            # 合并数据：强制所有数据遵循 target_columns 的顺序
            # .reindex 确保万无一失
            updated_df = pd.concat([existing_df, new_df], ignore_index=True)
            updated_df = updated_df.reindex(columns=target_columns)
            
            # 执行更新
            conn.update(spreadsheet=url, data=updated_df)
            
            st.success("✅ 顺序已锁定并成功同步！")
            st.balloons()
        except Exception as err:
            st.error(f"同步失败: {err}")
