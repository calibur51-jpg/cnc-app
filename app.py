import streamlit as st
import pandas as pd
import gspread
import os
from datetime import datetime
import io

# ==========================================
# 🛠️ 雲端設定與資料庫連動
# ==========================================
SPREADSHEET_ID = "1Y3XJLmzIH2y2l-XWkQfOzhEPBcxSyFFW3RvYpG6JZJ8"
json_files = [f for f in os.listdir('.') if f.endswith('.json')]
JSON_FILE_NAME = json_files[0] if json_files else None

def get_gc():
    return gspread.service_account(filename=JSON_FILE_NAME)

@st.cache_data(ttl=5) # 💡 加入快取緩衝，防止 rerun 時按鈕變數被 Google 資料強制沖刷掉
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

# 初始化頁面
st.set_page_config(page_title="CNC", layout="wide")
st.title("CNC 刀具智慧管理系統 (完全修復神速版)")

# 低庫存標色邏輯
def c_low(row): 
    return ['background-color: #ffcccc; color: #800000; font-weight: bold;'] * len(row) if int(row['目前庫存']) <= int(row['安全庫存']) else [''] * len(row)

t1, t2, t3 = st.tabs(["現場領用", "⚙️ 管理員後台", "📜 歷史紀錄"])

# ==========================================
# TAB 1: 現場領用 (💡 徹底大改！採用 100% 機制鎖定計數器)
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
        st.info(f"📍 規格: {t_name} | 編號: {t_sel} | 儲位: {df_inv.loc[idx, '儲位']} | 目前庫存: {current_stock_val}")
        
        # 💡 使用獨立的狀態暫存區，完全不受重新整理影響
        if "qty_v6" not in st.session_state:
            st.session_state["qty_v6"] = 1
            
        # 建立兩個按鈕，按下當下「直接操作暫存區數字」
        c1, c2 = st.columns(2)
        with c1: 
            if st.button("➕ 數量加 1 支", use_container_width=True, key="btn_add_v6"):
                st.session_state["qty_v6"] += 1
                st.rerun()
        with c2: 
            if st.button("🔄 數量歸零回 1", use_container_width=True, key="btn_reset_v6"):
                st.session_state["qty_v6"] = 1
                st.rerun()

        # 這裡單純用來「顯示」與「微調」最終確定的數量
        qty_final = st.number_input("當前準備領用數量 (可點上方按鈕或手動輸入)", min_value=1, value=st.session_state["qty_v6"], key="qty_show_v6")
        st.session_state["qty_v6"] = qty_final
        
        u = st.selectbox("人員", ["小翔", "阿玄", "少宏", "阿晴", "阿偉", "阿福", "阿鬼"], key="user_t1_v6")
        cnc_machines = [f"CNC-{i:02d}" for i in range(1, 12)] + ["廠內備庫"]
        m = st.selectbox("機台", cnc_machines, key="machine_t1_v6")
        r = st.selectbox("原因", ["正常磨損", "異常崩刃", "調機", "其他"], key="reason_t1_v6")
        wo = st.text_input("工單號碼 (選填)", key="wo_t1_v6").strip()
        
        if st.button("確認領用扣庫存", type="primary", use_container_width=True, key="submit_btn_t1_v6"):
            if st.session_state["qty_v6"] > current_stock_val: 
                st.error("❌ 庫存不足！工廠目前沒那麼多庫存可以領")
            else:
                sh_raw = get_raw_sh()
                new_stock = current_stock_val - st.session_state["qty_v6"]
                col_num = df_inv.columns.get_loc("目前庫存") + 1
                sh_raw.worksheet("inventory").update_cell(idx + 2, col_num, new_stock)
                
                log_data = [datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "領用", t_sel, st.session_state["qty_v6"], u, m, r, wo if wo else "無"]
                sh_raw.worksheet("logs").append_row(log_data)
                
                st.session_state["qty_v6"] = 1 # 成功後洗回 1 支
                st.success(f"✅ {t_
