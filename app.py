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

if not JSON_FILE_NAME:
    st.error("找不到 JSON 憑證檔！")
    st.stop()

sh, df_inv, df_log = get_data()

# 初始化頁面
st.set_page_config(page_title="CNC", layout="wide")
st.title("CNC 刀具智慧管理系統")

# 低庫存標色
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
    
    # 💡 改以「品名規格」作為下拉選單主要顯示，方便師傅看懂
    tool_list = df_f["品名規格"].tolist()
    if not tool_list:
        st.warning("此分類下目前無刀具資料")
    else:
        t_name = st.selectbox("請選擇刀具名稱", tool_list)
        idx = df_inv[df_inv["品名規格"] == t_name].index[0]
        t_sel = df_inv.loc[idx, "刀具編號"]
        
        st.info(f"📍 規格: {t_name} | 編號: {t_sel} | 儲位: {df_inv.loc[idx, '儲位']} | 目前庫存: {df_inv.loc[idx, '目前庫存']}")
        
        if "qty_in" not in st.session_state: st.session_state["qty_in"] = 1
        qty = st.number_input("數量", min_value=1, step=1, key="qty_in")
        
        c1, c2 = st.columns(2)
        with c1: 
            if st.button("+1"): st.session_state["qty_in"] += 1
        with c2: 
            if st.button("歸零"): st.session_state["qty_in"] = 1
        
        # 💡 正確的現場師傅名單
        u = st.selectbox("人員", ["小翔", "阿玄", "少宏", "阿晴", "阿偉", "阿福", "阿鬼"], key="uk1")
        
        # 💡 自動生成 CNC-01 到 CNC-11 的機台清單
        cnc_machines = [f"CNC-{i:02d}" for i in range(1, 12)] + ["廠內備庫"]
        m = st.selectbox("機台", cnc_machines, key="mk1")
        
        r = st.selectbox("原因", ["正常磨損", "異常崩刃", "調機", "其他"], key="rk1")
        wo = st.text_input("工單號碼 (選填)").strip()
        
        if st.button("確認領用", type="primary"):
            if int(df_inv.loc[idx, "目前庫存"]) < qty: 
                st.error("❌ 庫存不足！無法領取")
            else:
                new_stock = int(df_inv.loc[idx, "目前庫存"]) - qty
                sh.worksheet("inventory").update_cell(idx + 2, df_inv.columns.get_loc("目前庫存") + 1, new_stock)
                sh.worksheet("logs").append_row([datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "領用", t_sel, qty, u, m, r, wo if wo else "無"])
                st.success(f"✅ 領用成功！已扣除 {qty} 個")
                st.rerun()

# ==========================================
# TAB 2: 管理員後台 (含分類篩選與庫存告急專區)
# ==========================================
with t2:
    if st.text_input("輸入管理密碼", type="password") == "1234":
        sub = st.radio("功能選擇", ["庫存總覽與搜尋", "進貨入庫", "全新建檔"], horizontal=True)
        
        if sub == "庫存總覽與搜尋":
            # 🚨 這是幫你加的【庫存告急專區】
            st.markdown("### 🚨 庫存告急專區 (低於或等於安全庫存)")
            df_alert = df_inv[df_inv["目前庫存"].astype(int) <= df_inv["安全庫存"].astype(int)]
            if df_alert.empty:
                st.success("✅ 目前所有刀具水位安全，沒有缺貨！")
            else:
                st.dataframe(df_alert.style.apply(c_low, axis=1), hide_index=True, use_container_width=True)
            
            st.write("---")
            
            # 🔍 這是幫你優化的【大分類總覽與搜尋】
            st.markdown("### 🔍 庫存分類總覽與搜尋")
            cats_view = ["全部"] + df_inv["分類"].unique().tolist()
            cat_sel_view = st.selectbox("選擇要查看的分類", cats_view, key="cat_view")
            
            df_view = df_inv if cat_sel_view == "全部" else df_inv[df_inv["分類"] == cat_sel_view]
            
            search_k = st.text_input("輸入關鍵字 (如品名/規格) 快速搜尋：").strip()
            if search_k:
                df_view = df_view[df_view["品名規格"].str.contains(search_k, case=False) | df_view["刀具編號"].str.contains(search_k, case=False)]
            
            st.dataframe(df_view.style.apply(c_low, axis=1), hide_index=True, use_container_width=True)

        elif sub == "進貨入庫":
            st.markdown("### 📦 進貨入庫")
            t_in_name = st.selectbox("選擇進貨刀具品名", df_inv["品名規格"].tolist())
            idx_in = df_inv[df_inv["品名規格"] == t_in_name].index[0]
            q_in = st.number_input("進貨數量", min_value=1, step=1)
            
            if st.button("確認進貨"):
                new_stock = int(df_inv.loc[idx_in, "Currently Stocked" if "Currently Stocked" in df_inv.columns else "目前庫存"]) + q_in
                sh.worksheet("inventory").update_cell(idx_in + 2, df_inv.columns.get_loc("目前庫存") + 1, new_stock)
                sh.worksheet("logs").append_row([datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "進貨", df_inv.loc[idx_in, "刀具編號"], q_in, "管理員", "補貨", "進貨", "無"])
                st.success(f"✅ 已成功為 {t_in_name} 補入 {q_in} 個！")
                st.rerun()

        elif sub == "全新建檔":
            st.markdown("### 🆕 全新建檔")
            with st.form("new_tool_form"):
                ncat = st.selectbox("分類", ["銑刀", "圓鼻刀", "球刀", "粉末鑽頭", "黑鑽", "絲功", "銑牙刀"])
                nid = st.text_input("新刀具編號 (例如: EM-005)")
                nname = st.text_input("品名規格 (例如: 鎢鋼平底銑刀 D10)")
                nloc = st.text_input("儲位 (例如: A架-01)")
                nstock = st.number_input("初始庫存", min_value=0, step=1)
                nsafe = st.number_input("安全庫存", min_value=0, step=1)
                
                if st.form_submit_button("確認建檔"):
                    if nid in df_inv["刀具編號"].values:
                        st.error("❌ 編號重複了，請檢查！")
                    elif nname in df_inv["品名規格"].values:
                        st.error("❌ 品名規格重複了，請換個名稱！")
                    else:
                        sh.worksheet("inventory").append_row([ncat, nid, nname, nloc, nstock, nsafe])
                        st.success("🎉 全新建檔成功！")
                        st.rerun()
    else:
        st.warning("🔒 需管理員密碼")

# ==========================================
# TAB 3: 歷史紀錄
# ==========================================
with t3:
    if st.text_input("輸入密碼查看歷史", type="password", key="pw_log") == "1234":
        st.markdown("### 📜 完整出入庫歷史紀錄")
        st.dataframe(df_log, use_container_width=True)
    else:
        st.warning("🔒 僅限管理人員")
