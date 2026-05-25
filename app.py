import streamlit as st
import pandas as pd
import requests
from datetime import datetime
import gspread
import os

# =====================================================================
# 🛠️ 基礎雲端設定 (試算表 ID 與 LINE Token)
# =====================================================================
SPREADSHEET_ID = "1Y3XJLmzIH2y2l-XWkQfOzhEPBcxSyFFW3RvYpG6JZJ8"

# 💡 填入你原本申請好的 LINE Notify Token (若留空則不發送通知)
LINE_TOKEN = "" 

# 自動在同資料夾內搜尋 Google 下載的 .json 憑證檔案
json_files = [f for f in os.listdir('.') if f.endswith('.json')]
JSON_FILE_NAME = json_files[0] if json_files else None

# 初始化 Google Sheets 連線
def get_sheet_data(worksheet_name):
    if not JSON_FILE_NAME:
        return None, pd.DataFrame()
    try:
        gc = gspread.service_account(filename=JSON_FILE_NAME)
        sh = gc.open_by_key(SPREADSHEET_ID)
        ws = sh.worksheet(worksheet_name)
        data = ws.get_all_records()
        df = pd.DataFrame(data)
        return ws, df
    except Exception as e:
        st.error(f"連線 Google 試算表失敗。錯誤訊息: {e}")
        return None, pd.DataFrame()

# LINE 簡訊通知功能
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

# =====================================================================
# 📱 網頁介面配置
# =====================================================================
st.set_page_config(page_title="CNC 刀具庫存管理系統", layout="wide")
st.title("🛠️ CNC 刀具庫存管理系統 (雲端版)")

if not JSON_FILE_NAME:
    st.error("❌ 錯誤：在 GitHub 專案中找不到 .json 憑證檔案！請確認憑證是否有正確上傳。")
else:
    # 讀取雲端資料
    ws_inv, df_inv = get_sheet_data("inventory")
    ws_log, df_log = get_sheet_data("logs")

    if df_inv.empty:
        st.warning("正在讀取雲端試算表資料中，請稍候...")
    else:
        # 建立原本設定好的三大分頁
        tab1, tab2, tab3 = st.tabs(["📌 現場領用/退回", "📊 即時庫存看板", "📜 歷史異動紀錄"])

        # -----------------------------------------------------------------
        # 分頁 1：現場領用與退回登錄
        # -----------------------------------------------------------------
        with tab1:
            st.header("現場刀具動態登錄")
            col1, col2 = st.columns(2)
            
            with col1:
                action = st.radio("請選擇動作", ["領用 (-)", "入庫/退回 (+)"])
                operator = st.text_input("經辦人員 (請輸入姓名) *必填", key="operator").strip()
                work_order = st.text_input("工單號碼 (選填)", key="work_order").strip()
                reason_type = st.selectbox("原因類型", ["正常加工損耗", "異常破損", "新刀入庫", "工程測試", "其他"])
                note = st.text_input("備註說明", key="note").strip()
                
            with col2:
                # 自動抓取試算表中的所有不重複分類
                category_list = sorted(df_inv["分類"].unique().tolist()) if "分類" in df_inv.columns else []
                sel_cat = st.selectbox("1. 選擇刀具分類", category_list)
                
                # 根據分類聯動篩選刀具
                sub_df = df_inv[df_inv["分類"] == sel_cat]
                tool_options = [f"{row['刀具編號']} | {row['品名規格']} (現存:{row['目前庫存']})" for _, row in sub_df.iterrows()]
                selected_tool_str = st.selectbox("2. 選擇具體刀具", tool_options)
                
                qty = st.number_input("3. 輸入異動數量", min_value=1, value=1, step=1)

            # 提交按鈕
            if st.button("確認提交資料", type="primary"):
                if not operator:
                    st.error("❌ 提交失敗：請務必輸入『經辦人員』姓名！")
                elif not selected_tool_str:
                    st.error("❌ 提交失敗：未選擇任何刀具！")
                else:
                    # 解析選擇的刀具編號
                    tool_id = selected_tool_str.split(" | ")[0]
                    idx = df_inv[df_inv["刀具編號"] == tool_id].index[0]
                    current_stock = int(df_inv.loc[idx, "目前庫存"])
                    tool_name = df_inv.loc[idx, "品名規格"]
                    safe_stock = int(df_inv.loc[idx, "安全庫存"])

                    # 對應到試算表的真實列數 (Index + 2)
                    sheet_row = int(idx) + 2
                    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    
                    if action == "領用 (-)":
                        if current_stock < qty:
                            st.error(f"❌ 庫存不足！目前僅剩 {current_stock} 把，無法領用 {qty} 把。")
                        else:
                            new_stock = current_stock - qty
                            # 更新目前庫存欄位
                            ws_inv.update_cell(sheet_row, df_inv.columns.get_loc("目前庫存") + 1, new_stock)
                            
                            # 寫入 logs 分頁
                            ws_log.append_row([now_str, "領用", tool_id, qty, operator, note, reason_type, work_order])
                            st.success(f"🎉 領用成功！{tool_name} 已領出 {qty} 把。最新庫存: {new_stock} 把。")
                            
                            # 🚨 安全庫存 LINE 警報功能
                            if new_stock <= safe_stock:
                                msg = f"\n⚠️【CNC 刀具安全庫存警報】\n刀具編號: {tool_id}\n品名規格: {tool_name}\n目前庫存 ({new_stock}) 已低於或等於安全水位 ({safe_stock})！\n請現場管理員儘速補貨。"
                                send_line_notification(msg)
                            st.rerun()
                    else:
                        # 入庫功能
                        new_stock = current_stock + qty
                        ws_inv.update_cell(sheet_row, df_inv.columns.get_loc("目前庫存") + 1, new_stock)
                        
                        # 寫入 logs 分頁
                        ws_log.append_row([now_str, "入庫", tool_id, qty, operator, note, reason_type, work_order])
                        st.success(f"🎉 入庫成功！{tool_name} 已補進 {qty} 把。最新庫存: {new_stock} 把。")
                        st.rerun()

        # -----------------------------------------------------------------
        # 分頁 2：即時庫存看板 (包含原本設定的紅色高亮篩選)
        # -----------------------------------------------------------------
        with tab2:
            st.header("廠內即時庫存狀態")
            
            # 原本的防呆篩選器
            show_low_stock = st.checkbox("🚨 只顯示已低於安全庫存的缺刀品項")
            display_df = df_inv.copy()
            
            if show_low_stock:
                display_df = display_df[display_df["目前庫存"] <= display_df["安全庫存"]]
                
            # 原本的紅色危險高亮背景函數
            def highlight_low_stock(row):
                return ['background-color: #ffcccc; color: #cc0000; font-weight: bold;' if row['目前庫存'] <= row['安全庫存'] else '' for _ in row]
                
            if not display_df.empty:
                st.dataframe(display_df.style.apply(highlight_low_stock, axis=1), use_container_width=True, hide_index=True)
            else:
                st.info("👍 目前廠內所有刀具庫存皆在安全水位以上。")

        # -----------------------------------------------------------------
        # 分頁 3：歷史異動紀錄 (最新時間排在最上面)
        # -----------------------------------------------------------------
        with tab3:
            st.header("歷史領用與入庫紀錄總覽")
            if not df_log.empty:
                # 將最新紀錄反轉排在最上方
                df_log_sorted = df_log.iloc[::-1]
                st.dataframe(df_log_sorted, use_container_width=True, hide_index=True)
            else:
                st.info("目前尚無任何領用或入庫異動紀錄。")
