import streamlit as st
import pandas as pd
import gspread
import os
from datetime import datetime
import io

# ==========================================
# 雲端設定
# ==========================================
SPREADSHEET_ID = "1Y3XJLmzIH2y2l-XWkQfOzhEPBcxSyFFW3RvYpG6JZJ8"
json_files = [f for f in os.listdir('.') if f.endswith('.json')]
JSON_FILE_NAME = json_files[0] if json_files else None

def get_gc():
    return gspread.service_account(filename=JSON_FILE_NAME)

@st.cache_data(ttl=5)
def get_data_cached():
    gc = get_gc()
    sh = gc.open_by_key(SPREADSHEET_ID)
    df_inv = pd.DataFrame(sh.worksheet("inventory").get_all_records())
    df_log = pd.DataFrame(sh.worksheet("logs").get_all_records())
    return df_inv, df_log

def get_raw_sh():
    return get_gc().open_by_key(SPREADSHEET_ID)

if not JSON_FILE_NAME:
    st.error("找不到 JSON 憑證檔！")
    st.stop()

df_inv, df_log = get_data_cached()

st.set_page_config(page_title="CNC", layout="wide")
st.title("CNC 刀具智慧管理系統 (極簡防呆版)")

def c_low(row): 
    return ['background-color: #ffcccc; color: #800000; font-weight: bold;'] * len(row) if int(row['目前庫存']) <= int(row['安全庫存']) else [''] * len(row)

t1, t2, t3 = st.tabs(["現場領用", "管理員後台", "歷史紀錄"])

# ==========================================
# TAB 1: 現場領用
# ==========================================
with t1:
    cats = ["全部"] + df_inv["分類"].unique().tolist()
    cat_sel = st.selectbox("請先選擇大分類", cats, key="cat_sel_t1_v6")
    df_f = df_inv if cat_sel == "全部" else df_inv[df_inv["分類"] == cat_sel]
    
    tool_list = df_f["品名規格"].tolist()
    if not tool_list:
        st.warning("此分類下目前無刀具資料")
    else:
        t_name = st.selectbox("請選擇刀具名稱", tool_list, key="t_name_t1_v6")
        idx = df_inv[df_inv["品名規格"] == t_name].index[0]
        t_sel = df_inv.loc[idx, "刀具編號"]
        current_stock_val = int(df_inv.loc[idx, "目前庫存"])
        
        st.info(f"📍 規格: {t_name} | 編號: {t_sel} | 目前庫存: {current_stock_val}")
        
        if "qty_v6" not in st.session_state:
            st.session_state["qty_v6"] = 1
            
        c1, c2 = st.columns(2)
        with c1: 
            if st.button("➕ 數量加 1", use_container_width=True, key="btn_add_v6"):
                st.session_state["qty_v6"] += 1
                st.rerun()
        with c2: 
            if st.button("🔄 數量歸零", use_container_width=True, key="btn_reset_v6"):
                st.session_state["qty_v6"] = 1
                st.rerun()

        qty_final = st.number_input("當前準備領用數量", min_value=1, value=st.session_state["qty_v6"], key="qty_show_v6")
        st.session_state["qty_v6"] = qty_final
        
        u = st.selectbox("人員", ["小翔", "阿玄", "少宏", "阿晴", "阿偉", "阿福", "阿鬼"], key="user_t1_v6")
        cnc_machines = [f"CNC-{i:02d}" for i in range(1, 12)] + ["廠內備庫"]
        m = st.selectbox("機台", cnc_machines, key="machine_t1_v6")
        r = st.selectbox("原因", ["正常磨損", "異常崩刃", "調機", "其他"], key="reason_t1_v6")
        wo = st.text_input("工單號碼 (選填)", key="wo_t1_v6").strip()
        
        if
