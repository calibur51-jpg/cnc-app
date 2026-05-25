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
        
        if st.button("確認領用", type="primary", use_container_width=True):
            if qty > cur_stock:
                st.error("❌ 庫存不足！")
            else:
                new_s = cur_stock - qty
                get_sh().worksheet("inventory").update_cell(idx+2, df_inv.columns.get_loc("目前庫存")+1, new_s)
                get_sh().worksheet("logs").append_row([datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "領用", t_sel, qty, u, m, r, wo])
                st.success(f"✅ 已領刀：{t_name} 共 {qty} 支")
                st.session_state["q_val"] = 1
                st.cache_data.clear()
                import time; time.sleep(1); st.rerun()

with t2:
    if st.text_input("密碼", type="password", key="pw2") == "1234":
        sub = st.radio("功能", ["叫貨", "進貨", "建檔", "校正"], horizontal=True)
        if sub == "叫貨":
            alert = df_inv[df_inv["目前庫存"].astype(int) <= df_inv["安全庫存"].astype(int)]
            if alert.empty: st.success("庫存安全")
            else: st.dataframe(alert, hide_index=True)
        elif sub == "進貨":
            t_in = st.selectbox("刀具", df_inv["品名規格"].tolist())
            idx_in = df_inv[df_inv["品名規格"] == t_in].index[0]
            q_in = st.number_input("數量", min_value=1, step=1)
            if st.button("確認進貨"):
                get_sh().worksheet("inventory").update_cell(idx_in+2, df_inv.columns.get_loc("目前庫存")+1, int(df_inv.loc[idx_in, "目前庫存"]) + q_in)
                get_sh().worksheet("logs").append_row([datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "進貨", df_inv.loc[idx_in,"刀具編號"], q_in, "管理", "補貨", "進貨", "無"])
                st.success("成功"); st.cache_data.clear(); st.rerun()
        elif sub == "建檔":
            with st.form("f_new"):
                c, nid, nname, nloc = st.selectbox("分類", ["銑刀","圓鼻刀","球刀","粉末鑽頭","黑鑽","絲功","銑牙刀"]), st.text_input("編號"), st.text_input("品名"), st.text_input("儲位")
                nstock, nsafe = st.number_input("目前庫存", min_value=0), st.number_input("安全庫存", min_value=0)
                if st.form_submit_button("確認建檔"):
                    get_sh().worksheet("inventory").append_row([c, nid, nname, nloc, nstock, nsafe])
                    st.success("成功"); st.cache_data.clear(); st.rerun()
        elif sub == "校正":
            e_name = st.selectbox("刀具", df_inv["品名規格"].tolist())
            e_idx = df_inv[df_inv["品名規格"] == e_name].index[0]
            with st.form("f_edit"):
                c_list = ["銑刀","圓鼻刀","球刀","粉末鑽頭","黑鑽","絲功","銑牙刀"]
                ec = st.selectbox("分類", c_list, index=c_list.index(df_inv.loc[e_idx, '分類']))
                eid, enm, eloc = st.text_input("編號", df_inv.loc[e_idx, '刀具編號']), st.text_input("品名", df_inv.loc[e_idx, '品名規格']), st.text_input("儲位", df_inv.loc[e_idx, '儲位'])
                estk, esaf = st.number_input("目前庫存", value=int(df_inv.loc[e_idx, '目前庫存'])), st.number_input("安全庫存", value=int(df_inv.loc[e_idx, '安全庫存']))
                if st.form_submit_button("儲存"):
                    sh_r = get_sh()
                    for i, val in enumerate([ec, eid, enm, eloc, estk, esaf], 1): sh_r.worksheet("inventory").update_cell(e_idx+2, i, val)
                    st.success("成功"); st.cache_data.clear(); st.rerun()

with t3:
    if st.text_input("密碼", type="password", key="pw3") == "1234":
        if not df_log.empty:
            buf = io.BytesIO()
            with pd.ExcelWriter(buf, engine='xlsxwriter') as w:
                df_log.to_excel(w, sheet_name='紀錄', index=False)
                df_inv.to_excel(w, sheet_name='庫存', index=False)
            st.download_button("下載報表", buf.getvalue(), "CNC.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        st.dataframe(df_log, use_container_width=True)
