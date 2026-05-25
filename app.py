import streamlit as st
import pandas as pd
import gspread
import os
from datetime import datetime
import io

SPREADSHEET_ID = "1Y3XJLmzIH2y2l-XWkQfOzhEPBcxSyFFW3RvYpG6JZJ8"
jsons = [f for f in os.listdir('.') if f.endswith('.json')]
JSON_FILE = jsons[0] if jsons else None

if not JSON_FILE:
    st.error("找不到 JSON 憑證檔！")
    st.stop()

@st.cache_data(ttl=5)
def get_data():
    gc = gspread.service_account(filename=JSON_FILE)
    sh = gc.open_by_key(SPREADSHEET_ID)
    inv = pd.DataFrame(sh.worksheet("inventory").get_all_records())
    log = pd.DataFrame(sh.worksheet("logs").get_all_records())
    return inv, log

def get_sh():
    gc = gspread.service_account(filename=JSON_FILE)
    return gc.open_by_key(SPREADSHEET_ID)

df_inv, df_log = get_data()

st.set_page_config(page_title="CNC", layout="wide")
st.title("CNC 刀具系統")

t1, t2, t3 = st.tabs(["領用", "後台", "紀錄"])

with t1:
    cats = ["全部"] + df_inv["分類"].unique().tolist()
    cat_sel = st.selectbox("分類", cats, key="c1")
    df_f = df_inv if cat_sel == "全部" else df_inv[df_inv["分類"] == cat_sel]
    
    t_list = df_f["品名規格"].tolist()
    if not t_list:
        st.warning("無資料")
    else:
        t_name = st.selectbox("刀具", t_list, key="n1")
        idx = df_inv[df_inv["品名規格"] == t_name].index[0]
        t_sel = df_inv.loc[idx, "刀具編號"]
        cur_stock = int(df_inv.loc[idx, "目前庫存"])
        
        st.info(f"編號:{t_sel} | 儲位:{df_inv.loc[idx, '儲位']} | 庫存:{cur_stock}")
        
        if "q_val" not in st.session_state: st.session_state["q_val"] = 1
        col1, col2 = st.columns(2)
        with col1: 
            if st.button("➕ 加1", key="b_add"): st.session_state["q_val"] += 1; st.rerun()
        with col2: 
            if st.button("🔄 歸1", key="b_res"): st.session_state["q_val"] = 1; st.rerun()

        qty = st.number_input("數量", min_value=1, value=st.session_state["q_val"])
        st.session_state["q_val"] = qty
        
        u = st.selectbox("人員", ["小翔","阿玄","少宏","阿晴","阿偉","阿福","阿鬼"])
        m = st.selectbox("機台", [f"CNC-{i:02d}" for i in range(1,12)]+["備庫"])
        r = st.selectbox("原因", ["正常磨損", "異常崩刃", "調機", "其他"])
        wo = st.text_input("工單").strip()
        
        if st.button("確認領用", type="primary"):
            st.session_state["confirm_data"] = {"q": qty, "u": u, "m": m, "r": r, "wo": wo, "idx": idx, "cur": cur_stock, "ts": t_sel, "nm": t_name}

        if "confirm_data" in st.session_state:
            d = st.session_state["confirm_data"]
            st.warning(f"⚠️ 請確認：【{d['nm']}】共 {d['q']} 支，領用人 {d['u']}，機台 {d['m']}。")
            if st.button("✅ 確定執行", type="primary"):
                if d['q'] > d['cur']: 
                    st.error("❌ 庫存不足！")
                else:
                    new_s = d['cur'] - d['q']
                    get_sh().worksheet("inventory").update_cell(d['idx']+2, df_inv.columns.get_loc("目前庫存")+1, new_s)
                    get_sh().worksheet("logs").append_row([datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "領用", d['ts'], d['q'], d['u'], d['m'], d['r'], d['wo']])
                    
                    # 成功後顯示提示並清理
                    st.success(f"🎉 領用成功：{d['nm']} x {d['q']} 支 (剩餘庫存: {new_s})")
                    st.session_state["q_val"] = 1
                    del st.session_state["confirm_data"]
                    st.cache_data.clear()
                    # 延遲後重整，讓使用者看到成功提示
                    if st.button("返回"): st.rerun()

with t2:
    if st.text_input("密碼", type="password", key="pw2") == "1234":
        sub = st.radio("功能", ["叫貨", "進貨", "建檔", "校正"], horizontal=True)
        # 後台邏輯保持...
        if sub == "叫貨":
            alert = df_inv[df_inv["目前庫存"].astype(int) <= df_inv["安全庫存"].astype(int)]
            if alert.empty: st.success("庫存安全")
            else: st.dataframe(alert, hide_index=True)

with t3:
    if st.text_input("密碼", type="password", key="pw3") == "1234":
        if not df_log.empty:
            buf = io.BytesIO()
            with pd.ExcelWriter(buf, engine='openxmlformats.xlsxwriter') as w:
                df_log.to_excel(w, sheet_name='紀錄', index=False)
            st.download_button("下載報表", buf.getvalue(), "CNC.xlsx")
        st.dataframe(df_log, use_container_width=True)
