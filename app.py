import streamlit as st
import pandas as pd
import requests
from datetime import datetime
import gspread

# 試算表 ID
SPREADSHEET_ID = "1Y3XJLmzIH2y2l-XWkQfOzhEPBcxSyFFW3RvYpG6JZJ8"
LINE_TOKEN = "" # 你的 LINE Token 保持不變

# Google 雲端金鑰設定
gcp_config = {
  "type": "service_account",
  "project_id": "cnc-system-497409",
  "private_key_id": "64ccd035a4d1152f16007c13a779e58b538bc5c0",
  "private_key": "-----BEGIN PRIVATE KEY-----\nMIIEvwIBADANBgkqhkiG9w0BAQEFAASCBKkwggSlAgEAAoIBAQDew94XflZwGltT\noIcU6g8AgV60gUZmFeoXuMul1nH9CXxqafDHD05you2CsJe7k6dQMFTSKJfpsGJZ\nbOF94v4D4+evGWIirD9T1mSQHRBdrIU5uIxMTdn7xNyXQ6OT25SLR+iWKFgtxiBJ\nKlfKIYEvRi3NR9+wggZPUHxjTa4nE7hdrZPNQgFqwhRomYOJL/Ei5s2Uz1Mf8xWr\nUg9hRa+IMSPpWtV539fwXMK3iJDq56E0wHMvLGBbJHgfxKgDq13BgH8fpOTibW41\nHKstS7+KtkudEjXIzZRLQOGb4+roSvoWNIm6X0u5huSPbrh+WT8F+gqJ6mYjVPA2\nzuPQDcKrAgMBAAECggEAA9itJj0ZaciEUmAizpE9pRKWyG/nzHqmyhx38VGC/ycb\nLaZncLVEJrKT5OSYgIKlXVSx6KPbmHHIbcB1iRW5F4DnggLil03frtqBOtCY21hp\nP6/lRd2ddlcJDNhiikdv7yyH4l/b9essqSONoU3Z/y9eoLBgnZmav+MLfGN3YfFR\nYQCgvYGKonzjajGntRZJZRlhzI7iQmHYBI9kgpGJpjJV/A+3F//4JgCAB31QBfYE\ntQzwhmFI5S8lIS539w928AF46uUNm2KJ5d9Q3vXEO6XJnsZPkisowcVFKcCRRqRb\nfOQxzuNrqloGbaf7idZNfoqGmbdW7ySU8HRtftvToQKBgQDyf1Do1rhmAz0DT4GP\nhp0GQ2oT85TrR0eFZkKYXVTaZqe3ZSk3jgor4dTfVCY8DbHovqEkKco5kr4F1yuy\n/WaPylnEKv78zep+SOgWZF3x1TcZMozqVd4+f/cu+V+jSjC696bADb6IBx1ZKnJP\naWHMOqcfPyyyenYRN2pBEaHx6QKBgQDrK0cwaE/Xe+XS9QRWv8rpvrwL/Y5JhE8U\n1rQwQozKVQeeSYhogVt5qNpRm+i7Gkg16Xz5Bvb+IvkP2HqnlHgdFY3czo7O6jgV\nBYoy5rzCQjTMNvTK18IPokoHjk6/bQx2ZgX7puuoDt+7EKVEvsOoWu3afw7/M4W3\n8T0aLD//cwKBgQCcUSHQ1gkMCW5dIfU8lePG09Ifhlcqy0n5Xg/zs8Ys+xuGBvno\ny/EWlH7qb44uDA3xIGEztJSdRFCl5yxONzbT3fa7k5PHVt2gBlNFi/FbILxhy8o2\njJ+03jxy1WGnGv4Kp/Wfu7xkZ2GtxsTlF+NpCS4N4GVpr7NIKdael0UzcQKBgQDC\lNKYeRbnAvsMa/MlHBh3A3xwp2Gd7r3ITkZVUBtSJrzg+ZLGdZIMveu2brxIY9yv\nzvu6yUqAyMsvkz0Zf71Kw1TYCIkdJ6szqZvJtiUkzscE2cv+Mju919hNHDCIL2CK\nbqwwptKCAZyZGZLFqNoXaPU5PrxX6HeR1SdrioWBhQKBgQDs+8bPfs7WpxuoQO/n\ntZdmM4O3j+wkRt4WL3ID2so49f81iep0SXeJVwN9jxfxBmQLbfd4+Hffd/lZYPlz\nqBkSMKgYB4UQRviVh4VxL9QJ1VQiB3KtKav39W1MJO5JJg/hpEP6tiamJaCBTKeA\n27ixAC0DuHLF6/sp79cXdTKiLA==\n-----END PRIVATE KEY-----\n",
  "client_email": "streamlit-cnc@cnc-system-497409.iam.gserviceaccount.com",
  "client_id": "107256542466649214202",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/streamlit-cnc%40cnc-system-497409.iam.gserviceaccount.com",
  "universe_domain": "googleapis.com"
}

# 初始化 Google Sheets 連線
def get_sheet_data(worksheet_name):
    try:
        gc = gspread.service_account_from_dict(gcp_config)
        sh = gc.open_by_key(SPREADSHEET_ID)
        ws = sh.worksheet(worksheet_name)
        data = ws.get_all_records()
        df = pd.DataFrame(data)
        return ws, df
    except Exception as e:
        st.error(f"連線 Google 試算表失敗。錯誤訊息: {e}")
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
    st.warning("正在等待雲端資料庫連線設定...")
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

                # 計算新庫存 (試算表行數要 +2)
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
            df_log_sorted = df_log.iloc[::-1]
            st.dataframe(df_log_sorted, use_container_width=True, hide_index=True)
        else:
            st.info("目前尚無任何領用紀錄。")
