import streamlit as st
import pandas as pd
import gspread
import os
from datetime import datetime
import io

# ==========================================
# 🛠️ 雲端設定
# ==========================================
SPREADSHEET_ID = "1Y3XJLmzIH2y2l-XWkQfOzhEPBcxSyFFW3RvYpG6JZJ8"
json_files = [f for f in os.listdir('.') if f.endswith('.json')]
JSON_FILE_NAME = json_files[0] if json_files else None

def get_gc():
    return gspread.service_account(filename=JSON_FILE_NAME)

def get_data():
    gc = get_gc()
    sh = gc.open_by_key(SPREADSHEET_ID)
    df_inv = pd.DataFrame(sh.worksheet("inventory").get_all_records())
    df_log = pd.DataFrame(sh.worksheet("logs").get_all_records())
    return sh, df_inv, df_log

if not JSON_FILE_NAME:
    st.error("找不到 JSON 憑證檔！")
    st.stop()

sh, df_inv, df_log = get_data()

# 初始化頁面
st.set_page_config(page_title="CNC", layout="wide")
st.title("CNC 刀具智慧管理系統 (完全穩定版)")

# 低庫存標色邏輯
def c_low(row): 
    return ['background-color: #ffcccc; color: #800000; font-weight: bold;'] * len(row) if int(row['目前庫存']) <= int(row['安全庫存']) else [''] * len(row)

t1, t2, t3 = st.tabs(["現場領用", "⚙️ 管理員後台", "📜 歷史紀錄"])

# ==========================================
# TAB 1: 現場領用 (完全獨立，不干擾後台)
# ==========================================
with t1:
    cats = ["全部"] + df_inv["分類"].unique().tolist()
    cat_sel = st.selectbox("請先選擇大分類", cats, key="cat_sel_t1_main")
    df_f = df_inv if cat_sel == "全部" else df_inv[df_inv["分類"] == cat_sel]
    
    tool_list = df_f["品名規格"].tolist()
    if not tool_list:
        st.warning("此分類下目前無刀具資料")
    else:
        t_name = st.selectbox("請選擇刀具名稱", tool_list, key="t_name_t1_main")
        idx = df_inv[df_inv["品名規格"] == t_name].index[0]
        t_sel = df_inv.loc[idx, "刀具編號"]
        
        current_stock_val = int(df_inv.loc[idx, "目前庫存"])
        st.info(f"📍 規格: {t_name} | 編號: {t_sel} | 儲位: {df_inv.loc[idx, '儲位']} | 目前庫存: {current_stock_val}")
        
        # 💡 最簡單且絕不當機的數量欄位
        qty = st.number_input("領用數量", min_value=1, step=1, value=1, key="qty_input_t1_final")
        
        u = st.selectbox("人員", ["小翔", "阿玄", "少宏", "阿晴", "阿偉", "阿福", "阿鬼"], key="user_t1_main")
        cnc_machines = [f"CNC-{i:02d}" for i in range(1, 12)] + ["廠內備庫"]
        m = st.selectbox("機台", cnc_machines, key="machine_t1_main")
        r = st.selectbox("原因", ["正常磨損", "異常崩刃", "調機", "其他"], key="reason_t1_main")
        wo = st.text_input("工單號碼 (選填)", key="wo_t1_main").strip()
        
        if st.button("確認領用", type="primary", key="submit_btn_t1_main"):
            if qty > current_stock_val: 
                st.error("❌ 庫存不足！無法領取")
            else:
                new_stock = current_stock_val - qty
                col_num = df_inv.columns.get_loc("目前庫存") + 1
                sh.worksheet("inventory").update_cell(idx + 2, col_num, new_stock)
                
                log_data = [datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "領用", t_sel, qty, u, m, r, wo if wo else "無"]
                sh.worksheet("logs").append_row(log_data)
                
                st.success(f"✅ {t_name} 領用成功！已扣除 {qty} 個")
                st.rerun()

# ==========================================
# TAB 2: 管理員後台 (全中文欄位綁死，絕無衝突)
# ==========================================
with t2:
    if st.text_input("輸入管理密碼", type="password", key="admin_password_final") == "1234":
        sub = st.radio("功能選擇", ["庫存總覽與叫貨", "進貨入庫", "全新建檔", "修改與校正庫存"], horizontal=True, key="admin_sub_radio")
        
        # 1. 庫存總覽與 LINE 一鍵叫貨
        if sub == "庫存總覽與叫貨":
            st.markdown("### 🚨 庫存告急專區 (低於或等於安全庫存)")
            df_alert = df_inv[df_inv["目前庫存"].astype(int) <= df_inv["安全庫存"].astype(int)]
            
            if df_alert.empty:
                st.success("✅ 目前所有刀具水位安全，沒有缺貨！")
            else:
                st.dataframe(df_alert.style.apply(c_low, axis=1), hide_index=True, use_container_width=True)
                
                date_str = datetime.now().strftime('%m/%d')
                line_text = f"【CNC 刀具補貨通知 - {date_str}】\n親愛的廠商您好，我們需要增補以下刀具：\n"
                for _, row in df_alert.iterrows():
                    shortage = int(row['安全庫存']) * 2 - int(row['currently_stored' if 'currently_stored' in df_inv.columns else '目前庫存'])
                    if shortage <= 0: shortage = 5
                    line_text += f"▪️ {row['品名規格']} (編號:{row['刀具編號']}) * 需求數量: {shortage} 支\n"
                line_text += "再麻煩您安排出庫，謝謝！"
                
                st.text_area("📋 LINE 叫貨文字 (直接複製即可貼到 LINE)", value=line_text, height=180, key="line_box_t2_final")
            
            st.write("---")
            st.markdown("### 🔍 庫存分類總覽與搜尋")
            cats_view = ["全部"] + df_inv["分類"].unique().tolist()
            cat_sel_view = st.selectbox("選擇要查看的分類", cats_view, key="cat_view_t2_final")
            df_view = df_inv if cat_sel_view == "全部" else df_inv[df_inv["分類"] == cat_sel_view]
            
            search_k = st.text_input("輸入關鍵字 (如品名/規格) 快速搜尋：", key="search_k_t2_final").strip()
            if search_k:
                df_view = df_view[df_view["品名規格"].str.contains(search_k, case=False) | df_view["刀具編號"].str.contains(search_k, case=False)]
            st.dataframe(df_view.style.apply(c_low, axis=1), hide_index=True, use_container_width=True)

        # 2. 進貨入庫
        elif sub == "進貨入庫":
            st.markdown("### 📦 進貨入庫")
            t_in_name = st.selectbox("選擇進貨刀具品名", df_inv["品名規格"].tolist(), key="t_in_selectbox_final")
            idx_in = df_inv[df_inv["品名規格"] == t_in_name].index[0]
            q_in = st.number_input("進貨數量", min_value=1, step=1, key="q_in_input_final")
            
            if st.button("確認進貨", key="btn_confirm_in_final"):
                target_col = df_inv.columns.get_loc("目前庫存") + 1
                new_stock = int(df_inv.loc[idx_in, "目前庫存"]) + q_in
                sh.worksheet("inventory").update_cell(idx_in + 2, target_col, new_stock)
                
                in_log = [datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "進貨", df_inv.loc[idx_in, "刀具編號"], q_in, "管理員", "補貨", "進貨", "無"]
                sh.worksheet("logs").append_row(in_log)
                
                st.success(f"✅ 已成功為 {t_in_name} 補入 {q_in} 個！")
                st.rerun()

        # 3. 全新建檔
        elif sub == "全新建檔":
            st.markdown("### 🆕 全新建檔")
            with st.form("new_tool_form_final"):
                ncat = st.selectbox("分類", ["銑刀", "圓鼻刀", "球刀", "粉末鑽頭", "黑鑽", "絲功", "銑牙刀"])
                nid = st.text_input("新刀具編號 (例如: EM-005)")
                nname = st.text_input("品名規格 (例如: 鎢鋼平底銑刀 D10)")
                nloc = st.text_input("儲位 (例如: A架-01)")
                nstock = st.number_input("初始庫存", min_value=0, step=1)
                nsafe = st.number_input("安全庫存", min_value=0, step=1)
                
                if st.form_submit_button("確認建檔"):
                    if nid in df_inv["刀具編號"].values: st.error("❌ 編號重複了！")
                    elif nname in df_inv["品名規格"].values: st.error("❌ 品名規格重複了！")
                    else:
                        sh.worksheet("inventory").append_row([ncat, nid, nname, nloc, nstock, nsafe])
                        st.success("🎉 全新建檔成功！")
                        st.rerun()

        # 4. 修改與校正庫存功能
        elif sub == "修改與校正庫存":
            st.markdown("### 🔧 修改刀具基本資料與強制校正庫存")
            edit_name = st.selectbox("選擇你要修改的刀具", df_inv["品名規格"].tolist(), key="edit_select_t2_final")
            e_idx = df_inv[df_inv["品名規格"] == edit_name].index[0]
            
            with st.form("edit_tool_form_final"):
                st.write(f"正在修改：**{edit_name}**")
                ecat = st.selectbox("分類", ["銑刀", "圓鼻刀", "球刀", "粉末鑽頭", "黑鑽", "絲功", "銑牙刀"], index=["銑刀", "圓鼻刀", "球刀", "粉末鑽頭", "黑鑽", "絲功", "銑牙刀"].index(df_inv.loc[e_idx, '分類']))
                eid = st.text_input("刀具編號", value=df_inv.loc[e_idx, '刀具編號'])
                ename = st.text_input("品名規格", value=df_inv.loc[e_idx, '品名規格'])
                eloc = st.text_input("儲位", value=df_inv.loc[e_idx, '儲位'])
                estock = st.number_input("目前真實庫存校正 (強行更改)", min_value=0, step=1, value=int(df_inv.loc[e_idx, '目前庫存']))
                esafe = st.number_input("安全庫存修改", min_value=0, step=1, value=int(df_inv.loc[e_idx, '安全庫存']))
                
                if st.form_submit_button("儲存修改", type="primary"):
                    row_num = e_idx + 2
                    sh.worksheet("inventory").update_cell(row_num, 1, ecat)
                    sh.worksheet("inventory").update_cell(row_num, 2, eid)
                    sh.worksheet("inventory").update_cell(row_num, 3, ename)
                    sh.worksheet("inventory").update_cell(row_num, 4, eloc)
                    sh.worksheet("inventory").update_cell(row_num, 5, estock)
                    sh.worksheet("inventory").update_cell(row_num, 6, esafe)
                    
                    calib_log = [datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "後台校正", eid, f"校正為{estock}", "管理員", "無", "資料修改", "無"]
                    sh.worksheet("logs").append_row(calib_log)
                    
                    st.success("🎉 資料與庫存修改成功！")
                    st.rerun()
    else:
        st.warning("🔒 需管理員密碼")

# ==========================================
# TAB 3: 歷史紀錄 (Excel、消耗數據完全獨立運作)
# ==========================================
with t3:
    if st.text_input("輸入密碼查看歷史", type="password", key="pw_log_final") == "1234":
        
        if not df_log.empty:
            st.markdown("### 📥 報表導出專區")
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                df_log.to_excel(writer, sheet_name='完整歷史紀錄', index=False)
                df_inv.to_excel(writer, sheet_name='當前庫存狀態', index=False)
            
            st.download_button(
                label="🟢 點我下載【CNC刀具庫存與歷史紀錄.xlsx】",
                data=buffer.getvalue(),
                file_name=f"CNC_刀具管理報表_{datetime.now().strftime('%Y%m%d')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="excel_download_btn_final"
            )
            st.write("---")

        st.markdown("### 📈 廠內刀具消耗數據分析")
        if df_log.empty:
            st.info("目前尚無領用數據。")
        else:
            df_log_clean = df_log.copy()
            df_log_clean["數量"] = pd.to_numeric(df_log_clean["數量"], errors='coerce').fillna(0).astype(int)
            df_usage = df_log_clean[df_log_clean["動作"] == "領用"]
            
            if not df_usage.empty:
                c_analysis_1, c_analysis_2, c_analysis_3 = st.columns(3)
                with c_analysis_1:
                    st.markdown("#### 📊 機台吃刀量排行 (Top 5)")
                    machine_rank = df_usage.groupby("機台")["數量"].sum().reset_index()
                    machine_rank = machine_rank.sort_values(by="數量", ascending=False).head(5)
                    st.dataframe(machine_rank, hide_index=True, use_container_width=True)
                    
                with c_analysis_2:
                    st.markdown("#### 👤 人員領刀量排行 (Top 5)")
                    user_rank = df_usage.groupby("人員")["數量"].sum().reset_index()
                    user_rank = user_rank.sort_values(by="數量", ascending=False).head(5)
                    st.dataframe(user_rank, hide_index=True, use_container_width=True)
                    
                with c_analysis_3:
                    st.markdown("#### 🚨 領用原因比例分析")
                    reason_rank = df_usage.groupby("原因")["數量"].sum().reset_index()
                    st.dataframe(reason_rank, hide_index=True, use_container_width=True)
                    
                top_machine = machine_rank.iloc[0]["機台"] if not machine_rank.empty else "無"
                top_reason_row = reason_rank.sort_values(by="數量", ascending=False).iloc[0] if not reason_rank.empty else None
                
                if top_machine != "無" and top_machine != "廠內備庫":
                    st.warning(f"💡 **管理員提示**：目前統計 **{top_machine}** 消耗刀具數量最多。")
                if top_reason_row is not None and top_reason_row["原因"] == "異常崩刃":
                    st.error(f"⚠️ **警報**：目前工廠最主要的損耗原因為 **【異常崩刃】**。")

        st.write("---")
        st.markdown("### 📜 完整出入庫歷史紀錄")
        st.dataframe(df_log, use_container_width=True)
    else:
        st.warning("🔒 僅限管理人員")
