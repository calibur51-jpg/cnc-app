import streamlit as st
import pandas as pd
import gspread
import os
from datetime import datetime

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

# 初始化頁面
st.set_page_config(page_title="CNC", layout="wide")
st.title("CNC 刀具智慧管理系統 (雲端版)")

if not JSON_FILE_NAME:
    st.error("找不到 JSON 憑證檔！")
    st.stop()

sh, df_inv, df_log = get_data()

# ==========================================
# 邏輯輔助
# ==========================================
def c_low(row): return ['background-color: #ffcccc; color: #800000; font-weight: bold;'] * len(row) if int(row['目前庫存']) <= int(row['安全庫存']) else [''] * len(row)

# ==========================================
# TAB 1: 現場領用
# ==========================================
t1, t2, t3 = st.tabs(["現場領用", "⚙️ 管理員後台", "📜 歷史紀錄"])
with t1:
    cats = ["全部"] + df_inv["分類"].unique().tolist()
    cat_sel = st.selectbox("請先選擇大分類", cats)
    df_f = df_inv if cat_sel == "全部" else df_inv[df_inv["分類"] == cat_sel]
    t_sel = st.selectbox("選擇刀具編號", df_f["刀具編號"].tolist())
    idx = df_inv[df_inv["刀具編號"] == t_sel].index[0]
    st.text(f"規格: {df_inv.loc[idx, '品名規格']} | 儲位: {df_inv.loc[idx, '儲位']}")
    qty = st.number_input("數量", min_value=1, step=1, key="qty_in")
    
    c1, c2 = st.columns(2)
    with c1: 
        if st.button("+1"): st.session_state["qty_in"] = st.session_state.get("qty_in", 1) + 1
    with c2: 
        if st.button("歸零"): st.session_state["qty_in"] = 1
    
    u = st.selectbox("人員", ["張師傅", "李師傅", "王師傅", "劉課長"], key="uk1")
    m = st.selectbox("機台", ["CNC-01", "CNC-02", "CNC-03", "CNC-04", "廠內備庫"], key="mk1")
    r = st.selectbox("原因", ["正常磨損", "異常崩刃", "調機", "其他"], key="rk1")
    wo = st.text_input("工單號碼", key="wo_num")
    
    if st.button("確認領用", type="primary"):
        if df_inv.loc[idx, "目前庫存"] < qty: st.error("❌ 庫存不足！")
        else:
            new_stock = int(df_inv.loc[idx, "目前庫存"]) - qty
            sh.worksheet("inventory").update_cell(idx + 2, df_inv.columns.get_loc("目前庫存") + 1, new_stock)
            sh.worksheet("logs").append_row([datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "領用", t_sel, qty, u, m, r, wo if wo else "無"])
            st.rerun()

# ==========================================
# TAB 2: 管理員
# ==========================================
with t2:
    if st.text_input("輸入管理密碼", type="password") == "1234":
        sub = st.radio("功能選擇", ["庫存總覽", "進貨入庫"], horizontal=True)
        if sub == "庫存總覽":
            st.dataframe(df_inv.style.apply(c_low, axis=1), hide_index=True, use_container_width=True)
        else:
            t_in = st.selectbox("選擇刀具", df_inv["刀具編號"].tolist())
            q_in = st.number_input("進貨數量", min_value=1)
            if st.button("確認進貨"):
                new_stock = int(df_inv.loc[df_inv["刀具編號"] == t_in, "目前庫存"].values[0]) + q_in
                sh.worksheet("inventory").update_cell(df_inv[df_inv["刀具編號"] == t_in].index[0] + 2, df_inv.columns.get_loc("目前庫存") + 1, new_stock)
                sh.worksheet("logs").append_row([datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "進貨", t_in, q_in, "管理員", "補貨", "進貨", "無"])
                st.rerun()
    else: st.warning("🔒 需密碼")

# ==========================================
# TAB 3: 歷史紀錄
# ==========================================
with t3:
    if st.text_input("輸入密碼查看歷史", type="password", key="pw_log") == "1234":
        st.dataframe(df_log, use_container_width=True)
