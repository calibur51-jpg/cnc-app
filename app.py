import streamlit as st
import pandas as pd
import requests
from datetime import datetime
import gspread

# 💡 請將你剛剛複製的 Google 試算表 ID 填在這裡
# 網址中 /d/ 後面到 /edit 之前的那串字
SPREADSHEET_ID = "1Y3XJLmzIH2y2l-XWkQfOzhEPBcxSyFFW3RvYpG6JZJ8"
LINE_TOKEN = "" # 你的 LINE Token 保持不變

# 初始化 Google Sheets 連線
def get_sheet_data(worksheet_name):
    try:
        # 透過 Streamlit Secrets 安全金鑰連線
        gc = gspread.service_account_from_dict(st.secrets["gcp_service_account"])
        sh = gc.open_by_key(SPREADSHEET_ID)
        ws = sh.worksheet(worksheet_name)
        data = ws.get_all_records()
        df = pd.DataFrame(data)
        return ws, df
    except Exception as e:
        st.error(f"連線 Google 試算表失敗，請檢查憑證。錯誤訊息: {e}")
        return None, pd.DataFrame()

# LINE 通知功能
def send_line_notification(message):
    if not LINE_TOKEN:
        return
    url = "https://notify-api.line.me/api/notify"
    headers = {"Authorization": f"Bearer {LINE_TOKEN}"}
    data = {"message": message}
    try:
        requests.post(url, headers=headers, data=data)
    except:
        pass

st.set_page_config(page_title="CNC 刀具庫存管理系統", layout="wide")
st.title("🛠️ CNC 刀具庫存管理系統 (雲端版)")

# 讀取雲端資料
ws_inv, df_inv = get_sheet_data("inventory")
ws_log, df_log = get_sheet_data("logs")

if df_inv.empty:
    st.warning("正在等待雲端資料庫連線設定...請先完成 Streamlit Cloud 的 Secrets 設定。")
else:
    # 頁面分頁
    tab1, tab2, tab3 = st.tabs(["📌 現場領用/退回", "📊 庫存看板", "📜 歷史紀錄"])

    with tab1:
        st.header("現場刀具動態登錄")
        col1, col2 = st.columns(2)
        with col1:
            action = st.radio("請選擇動作", ["領用 (-)", "入庫/退回 (+)"])
            operator = st.text_input("經辦人員 (請輸入姓名)", key="operator").strip()
            work_order = st.text_input("工單號碼 (選填)", key="work_order").strip()
        with col2:
            category_list = sorted(df_inv["分類"].unique().tolist()) if "分類" in df_inv.columns else []
            sel_cat = st.selectbox("刀具分類", category_list)
            
            # 根據分類篩選刀具
            sub_df = df_inv[df_inv["分類"] == sel_cat]
            tool_options = [f"{row['刀具編號']} | {row['品名規格']} (現存:{row['目前庫存']})" for _, row in sub_df.iterrows()]
            selected_tool_str = st.selectbox("選擇刀具", tool_options)
            qty = st.number_input("數量", min_value=1, value=1, step=1)
            reason_type = st.selectbox("原因類型", ["正常加工損耗", "異常破損", "新刀入庫", "工程測試", "其他"])
            note = st.text_input("備註說明", "").strip()

        if st.button("確認提交", type="primary"):
            if not operator:
                st.error("❌ 提交失敗：請務必輸入『經辦人員』姓名！")
            elif not selected_tool_str:
                st.error("❌ 提交失敗：未選擇刀具！")
            else:
                tool_id = selected_tool_str.split(" | ")[0]
                idx = df_inv[df_inv["刀具編號"] == tool_id].index[0]
                current_stock = int(df_inv.loc[idx, "目前庫存"])
                tool_name = df_inv.loc[idx, "品名規格"]
                safe_stock = int(df_inv.loc[idx, "安全庫存"])

                # 計算新庫存 (試算表行數要 +2，因為 index 從 0 開始且有標頭列)
                sheet_row = int(idx) + 2
                
                if action == "領用 (-)":
                    if current_stock < qty:
                        st.error(f"❌ 庫存不足！目前僅剩 {current_stock} 把，無法領用 {qty} 把。")
                    else:
                        new_stock = current_stock - qty
                        ws_inv.update_cell(sheet_row, df_inv.columns.get_loc("目前庫存") + 1, new_stock)
                        
                        # 寫入紀錄
                        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        ws_log.append_row([now_str, "領用", tool_id, qty, operator, note, reason_type, work_order])
                        
                        st.success(f"🎉 領用成功！{tool_name} 領出 {qty} 把，剩餘庫存: {new_stock}")
                        
                        # 安全庫存警報
                        if new_stock <= safe_stock:
                            msg = f"\n⚠️【安全庫存警報】\n刀具編號: {tool_id}\n品名: {tool_name}\n目前庫存 ({new_stock}) 已低於安全水位 ({safe_stock})！\n請儘速補貨。"
                            send_line_notification(msg)
                        st.rerun()
                else:
                    new_stock = current_stock + qty
                    ws_inv.update_cell(sheet_row, df_inv.columns.get_loc("目前庫存") + 1, new_stock)
                    
                    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    ws_log.append_row([now_str, "入庫", tool_id, qty, operator, note, reason_type, work_order])
                    
                    st.success(f"🎉 入庫成功！{tool_name} 補進 {qty} 把，最新庫存: {new_stock}")
                    st.rerun()

    with tab2:
        st.header("即時庫存看板")
        
        # 安全庫存篩選
        show_low_stock = st.checkbox("只顯示低於安全庫存的刀具")
        display_df = df_inv.copy()
        if show_low_stock:
            display_df = display_df[display_df["目前庫存"] <= display_df["安全庫存"]]
            
        def highlight_low_stock(row):
            return ['background-color: #ffcccc' if row['目前庫存'] <= row['安全庫存'] else '' for _ in row]
            
        if not display_df.empty:
            st.dataframe(display_df.style.apply(highlight_low_stock, axis=1), use_container_width=True, hide_index=True)
        else:
            st.info("目前庫存皆在安全水位。")

    with tab3:
        st.header("歷史異動紀錄")
        if not df_log.empty:
            # 倒序排列，讓最新的紀錄顯示在最上面
            df_log_sorted = df_log.iloc[::-1]
            st.dataframe(df_log_sorted, use_container_width=True, hide_index=True)
        else:
            st.info("目前尚無任何領用紀錄。")
