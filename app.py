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
        u, m, r = st.selectbox("人員", ["小翔","阿玄","少宏","阿晴","阿偉","阿福","阿鬼"]), st.selectbox("機台", [f"CNC-{i:02d}" for i in range(1,12)]+["備庫"]), st.selectbox("原因", ["正常磨損", "異常崩刃", "調機", "其他"])
        wo = st.text_input("工單").strip()
        if st.button("確認領用", type="primary", use_container_width=True):
            if qty > cur_stock:
                st.error("❌ 庫存不足！")
            else:
                new_s = cur_stock - qty
                get_sh().worksheet("inventory").update_cell(idx+2, df_inv.columns.get_loc("目前庫存")+1, new_s)
                get_sh().worksheet("logs").append_row([datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "領用", t_sel, qty, u, m, r, wo])
                
                # 這裡增加提示停留
                st.success(f"✅ 已領刀：{t_name} x {qty}")
                st.session_state["q_val"] = 1
                st.cache_data.clear()
                
                import time
                time.sleep(2) # 強制停留 2 秒，讓你絕對看得到
                st.rerun()

with t2:
    if st.text_input("密碼", type="password", key="pw2") == "1234":
        sub = st.radio("功能", ["叫貨", "進貨", "建檔", "校正"], horizontal=True)
        if sub == "叫貨":
            alert = df_inv[df_inv["目前庫存"].astype(int) <= df_inv["安全庫存"].astype(int)]
            if alert.empty:
                st.success("✅ 目前庫存水位安全！")
            else:
                st.markdown("### 🚨 待叫貨刀具")
                # 簡潔表格顯示
                st.dataframe(alert[["品名規格", "刀具編號", "目前庫存", "安全庫存"]], hide_index=True)
                
                # 產生 LINE 文字
                txt = "【CNC 刀具補貨需求】\n"
                for _, row in alert.iterrows():
                    need = int(row['安全庫存']) * 2 - int(row['目前庫存'])
                    need = max(need, 5)
                    txt += f"{row['品名規格']} (編號:{row['刀具編號']}) 需求: {need} 支\n"
                
                # 放在一個小區塊裡，並且給一個專用的複製按鈕
                st.code(txt, language=None)
                st.success("👆 上方內容已幫你整理好，直接複製即可貼到 LINE")
        elif sub == "進貨":
            t_in = st.selectbox("刀具", df_inv["品名規格"].tolist())
            q_in = st.number_input("數量", min_value=1, step=1)
            if st.button("確認進貨"):
                idx_in = df_inv[df_inv["品名規格"] == t_in].index[0]
                get_sh().worksheet("inventory").update_cell(idx_in+2, df_inv.columns.get_loc("目前庫存")+1, int(df_inv.loc[idx_in, "目前庫存"]) + q_in)
                get_sh().worksheet("logs").append_row([datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "進貨", df_inv.loc[idx_in,"刀具編號"], q_in, "管理", "補貨", "進貨", "無"])
                st.success("成功"); st.cache_data.clear(); st.rerun()
        elif sub == "建檔":
            with st.form("f_new"):
                c, nid, nname, nloc = st.selectbox("分類", ["銑刀","圓鼻刀","球刀","粉末鑽頭","黑鑽","絲功","銑牙刀"]), st.text_input("編號"), st.text_input("品名"), st.text_input("儲位")
                nstock, nsafe = st.number_input("庫存", min_value=0), st.number_input("安全", min_value=0)
                if st.form_submit_button("確認"):
                    get_sh().worksheet("inventory").append_row([c, nid, nname, nloc, nstock, nsafe]); st.success("成功"); st.cache_data.clear(); st.rerun()
        elif sub == "校正":
            e_name = st.selectbox("刀具", df_inv["品名規格"].tolist())
            e_idx = df_inv[df_inv["品名規格"] == e_name].index[0]
            with st.form("f_edit"):
                ec, eid, enm, eloc = st.selectbox("分類", ["銑刀","圓鼻刀","球刀","粉末鑽頭","黑鑽","絲功","銑牙刀"], index=0), st.text_input("編號", df_inv.loc[e_idx, '刀具編號']), st.text_input("品名", df_inv.loc[e_idx, '品名規格']), st.text_input("儲位", df_inv.loc[e_idx, '儲位'])
                estk, esaf = st.number_input("庫存", value=int(df_inv.loc[e_idx, '目前庫存'])), st.number_input("安全", value=int(df_inv.loc[e_idx, '安全庫存']))
                if st.form_submit_button("儲存"):
                    sh_r = get_sh()
                    for i, val in enumerate([ec, eid, enm, eloc, estk, esaf], 1): sh_r.worksheet("inventory").update_cell(e_idx+2, i, val)
                    st.success("成功"); st.cache_data.clear(); st.rerun()

with t3:
    if st.text_input("密碼", type="password", key="pw3") == "1234":
        st.header("📊 消耗分析與報表")
        
        # 除錯區：強制顯示所有欄位名稱
        st.write("目前讀取到的欄位名稱列表：")
        st.write(df_log.columns.tolist()) 
        
        if not df_log.empty:
            st.success("請看上面列表，找到那個對應機台的欄位名稱（例如 '機台編號' 或 '設備'）")
        st.dataframe(df_log, use_container_width=True)
