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
st.title("CNC 刀具智慧管理系統 (終極旗艦版)")

# 低庫存標色邏輯
def c_low(row): 
    return ['background-color: #ffcccc; color: #800000; font-weight: bold;'] * len(row) if int(row['目前庫存']) <= int(row['安全庫存']) else [''] * len(row)

t1, t2, t3 = st.tabs(["現場領用", "⚙️ 管理員後台", "📜 歷史紀錄"])

# ==========================================
# TAB 1: 現場領用
# ==========================================
with t1:
    cats = ["全部"] + df_inv["分類"].unique().tolist()
    cat_sel = st.selectbox("請先選擇大分類", cats)
    df_f = df_inv if cat_sel == "全部" else df_inv[df_inv["分類"] == cat_sel]
    
    tool_list = df_f["品名規格"].tolist()
    if not tool_list:
        st.warning("此分類下目前無刀具資料")
    else:
        t_name = st.selectbox("請選擇刀具名稱", tool_list)
        idx = df_inv[df_inv["品名規格"] == t_name].index[0]
        t_sel = df_inv.loc[idx, "刀具編號"]
        
        current_stock_val = int(df_inv.loc[idx, "目前庫存"])
        
        st.info(f"📍 規格: {t_name} | 編號: {t_sel} | 儲位: {df_inv.loc[idx, '儲位']} | 目前庫存: {current_stock_val}")
        
        if "qty_in" not in st.session_state: st.session_state["qty_in"] = 1
        qty = st.number_input("數量", min_value=1, step=1, key="qty_in")
        
        c1, c2 = st.columns(2)
        with c1: 
            if st.button("+1"): st.session_state["qty_in"] += 1
        with c2: 
            if st.button("歸零"): st.session_state["qty_in"] = 1
        
        u = st.selectbox("人員", ["小翔", "阿玄", "少宏", "阿晴", "阿偉", "阿福", "阿鬼"], key="uk1")
        cnc_machines = [f"CNC-{i:02d}" for i in range(1, 12)] + ["廠內備庫"]
        m = st.selectbox("機台", cnc_machines, key="mk1")
        r = st.selectbox("原因", ["正常磨損", "異常崩刃", "調機", "其他"], key="rk1")
        wo = st.text_input("工單號碼 (選填)").strip()
        
        if st.button("確認領用", type="primary"):
            if current_stock_val < qty: 
                st.error("❌ 庫存不足！無法領取")
            else:
                new_stock = current_stock_val - qty
                col_num = df_inv.columns.get_loc("目前庫存") + 1
                sh.worksheet("inventory").update_cell(idx + 2, col_num, new_stock)
                
                log_data = [datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "領用", t_sel, qty, u, m, r, wo if wo else "無"]
                sh.worksheet("logs").append_row(log_data)
                
                st.success(f"✅ 領用成功！已扣除 {qty} 個")
                st.rerun()

# ==========================================
# TAB 2: 管理員後台
# ==========================================
with t2:
    if st.text_input("輸入管理密碼", type="password") == "1234":
        sub = st.radio("功能選擇", ["庫存總覽與叫貨", "進貨入庫", "全新建檔", "修改與校正庫存"], horizontal=True)
        
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
                    shortage = int(row['安全庫存']) * 2
