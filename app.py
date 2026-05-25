import streamlit as st
import pandas as pd
import os
import shutil
import requests
from datetime import datetime

# 💡 您的 LINE Notify Token 貼在這裡 (例如 "AbCdEfGhIjK...")
LINE_TOKEN = ""

F_INV = r"\\192.168.0.220\明星共用資料夾\cnc_app\cnc_inventory.csv"
F_LOG = r"\\192.168.0.220\明星共用資料夾\cnc_app\cnc_log.csv"
BACKUP_DIR = r"\\192.168.0.220\明星共用資料夾\cnc_app\backup"

# 確保備份資料夾存在
if not os.path.exists(BACKUP_DIR):
    os.makedirs(BACKUP_DIR)

# 自動備份函式
def backup_data():
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    try:
        shutil.copy(F_INV, os.path.join(BACKUP_DIR, f"inv_{ts}.csv"))
        shutil.copy(F_LOG, os.path.join(BACKUP_DIR, f"log_{ts}.csv"))
    except:
        pass

# LINE 發送函式
def send_line(msg):
    if not LINE_TOKEN: return
    headers = {"Authorization": f"Bearer {LINE_TOKEN}"}
    data = {"message": msg}
    try:
        requests.post("https://notify-api.line.me/api/notify", headers=headers, data=data)
    except:
        pass

# 初始化檔案
if not os.path.exists(F_INV):
    pd.DataFrame([
        {"分類": "銑刀", "刀具編號": "TL-001", "品名規格": "鎢鋼四刃平底銑刀 D10", "儲位": "A架-01", "目前庫存": 39, "安全庫存": 3},
        {"分類": "球刀", "刀具編號": "TL-002", "品名規格": "球型銑刀 R2*L50", "儲位": "A架-02", "目前庫存": 2, "安全庫存": 5}
    ]).to_csv(F_INV, index=False)
if not os.path.exists(F_LOG):
    pd.DataFrame(columns=["時間", "動作", "刀具編號", "數量", "經辦人員", "備註", "原因類型", "工單號碼"]).to_csv(F_LOG, index=False)

df_inv, df_log = pd.read_csv(F_INV), pd.read_csv(F_LOG)
if "分類" not in df_inv.columns: df_inv["分類"] = "其他"
if "工單號碼" not in df_log.columns: df_log["工單號碼"] = "無"

st.set_page_config(page_title="CNC", layout="wide")
st.title("CNC 刀具智慧管理系統")

def add_qty(n): st.session_state["qty_in"] = st.session_state.get("qty_in", 1) + n
def reset_qty(): st.session_state["qty_in"] = 1
def c_low(row): return ['background-color: #ffcccc; color: #800000; font-weight: bold;'] * len(row) if int(row['目前庫存']) <= int(row['安全庫存']) else [''] * len(row)

t1, t2, t3 = st.tabs(["現場領用", "⚙️ 管理員後台", "📜 歷史紀錄"])

# ==========================================
# TAB 1: 現場領用
# ==========================================
with t1:
    if "last_tool" not in st.session_state: st.session_state["last_tool"] = None
    if "qty_in" not in st.session_state: st.session_state["qty_in"] = 1
    
    cats = ["全部"] + df_inv["分類"].unique().tolist()
    cat_sel = st.selectbox("請先選擇大分類", cats)
    df_f = df_inv if cat_sel == "全部" else df_inv[df_inv["分類"] == cat_sel]
    
    t_sel = st.selectbox("選擇刀具編號", df_f["刀具編號"].tolist())
    idx = df_inv[df_inv["刀具編號"] == t_sel].index[0]
    
    st.text(f"規格: {df_inv.loc[idx, '品名規格']} | 儲位: {df_inv.loc[idx, '儲位']}")
    
    # 數量輸入
    qty = st.number_input("數量", min_value=1, step=1, key="qty_in")
    c1, c2 = st.columns(2)
    with c1: st.button("+1", on_click=add_qty, args=(1,))
    with c2: st.button("歸零", on_click=reset_qty)
    
    # 💡 數量防呆攔截機制
    confirm_large = False
    if qty >= 5:
        st.warning("⚠️ 系統偵測單次領用量較大 (≥5)，請打勾確認防止誤觸！")
        confirm_large = st.checkbox("確認數量無誤", key="chk_large")
    
    u = st.selectbox("人員", ["張師傅", "李師傅", "王師傅", "劉課長"], key="uk1")
    m = st.selectbox("機台", ["CNC-01", "CNC-02", "CNC-03", "CNC-04", "廠內備庫"], key="mk1")
    r = st.selectbox("原因", ["正常磨損", "異常崩刃", "調機", "其他"], key="rk1")
    wo_input = st.text_input("工單號碼 (選填)", key="wo_num").strip()
    
    if st.button("確認領用", type="primary"):
        if qty >= 5 and not confirm_large:
            st.error("❌ 數量大於 5，請先勾選上方確認框！")
        elif df_inv.loc[idx, "目前庫存"] < qty: 
            st.error("❌ 庫存不足！無法領取")
        else:
            # 扣除庫存並寫入紀錄
            df_inv.loc[idx, "目前庫存"] -= qty
            df_inv.to_csv(F_INV, index=False)
            final_wo = wo_input if wo_input else "無"
            nl = pd.DataFrame([{"時間": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "動作": "領用", "刀具編號": t_sel, "數量": qty, "經辦人員": u, "備註": m, "原因類型": r, "工單號碼": final_wo}])
            pd.concat([nl, df_log], ignore_index=True).to_csv(F_LOG, index=False)
            
            # 💡 呼叫自動備份
            backup_data()
            
            # 💡 檢查是否低於安全庫存並發送 LINE
            cur_stock = df_inv.loc[idx, "目前庫存"]
            safe_stock = df_inv.loc[idx, "安全庫存"]
            if cur_stock <= safe_stock:
                send_line(f"\n⚠️ 【刀具庫存告急】\n編號: {t_sel}\n規格: {df_inv.loc[idx, '品名規格']}\n剩餘數量: {cur_stock}\n安全水位: {safe_stock}\n請盡速安排補貨！")
            
            st.session_state["last_tool"] = t_sel
            st.session_state["last_qty"] = qty
            st.rerun()

    if st.session_state.get("last_tool"):
        st.success(f"✅ 領用成功！{st.session_state['last_tool']} 已扣除 {st.session_state['last_qty']} 個")
        if st.button("清理顯示，準備下次領用"):
            st.session_state["last_tool"] = None
            st.rerun()

# ==========================================
# TAB 2: 管理員後台
# ==========================================
with t2:
    if st.text_input("輸入管理密碼", type="password") == "1234":
        sub = st.radio("功能選擇", ["庫存總覽與搜尋", "進貨入庫", "全新建檔"], horizontal=True)
        
        if sub == "庫存總覽與搜尋":
            st.markdown("### 🔍 庫存搜尋與總覽")
            search_k = st.text_input("輸入關鍵字 (編號/規格) 搜尋：")
            df_view = df_inv
            if search_k:
                df_view = df_inv[df_inv["刀具編號"].str.contains(search_k, case=False) | df_inv["品名規格"].str.contains(search_k, case=False)]
            st.dataframe(df_view.style.apply(c_low, axis=1), hide_index=True, use_container_width=True)
            if st.checkbox("顯示庫存圖表"):
                st.bar_chart(df_view.set_index("刀具編號")[["目前庫存", "安全庫存"]])

        elif sub == "進貨入庫":
            st.markdown("### 📦 進貨入庫")
            search_in = st.text_input("快速搜尋要進貨的刀具：")
            df_s = df_inv[df_inv["刀具編號"].str.contains(search_in, case=False)] if search_in else df_inv
            t_in = st.selectbox("請選擇刀具", df_s["刀具編號"].tolist())
            q_in = st.number_input("進貨數量", min_value=1, step=1)
            if st.button("確認進貨"):
                df_inv.loc[df_inv["刀具編號"] == t_in, "目前庫存"] += q_in
                df_inv.to_csv(F_INV, index=False)
                nl = pd.DataFrame([{"時間": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "動作": "進貨", "刀具編號": t_in, "數量": q_in, "經辦人員": "系統管理員", "備註": "管理員補貨", "原因類型": "進貨", "工單號碼": "無"}])
                pd.concat([nl, df_log], ignore_index=True).to_csv(F_LOG, index=False)
                
                # 💡 進貨也觸發自動備份
                backup_data()
                
                st.success(f"✅ 已成功為 {t_in} 補入 {q_in} 個！")
                st.info("請點選下方按鈕重整畫面")
                if st.button("刷新頁面"): st.rerun()

        elif sub == "全新建檔":
            with st.form("new_tool_form"):
                ncat = st.text_input("分類")
                nid = st.text_input("新刀具編號")
                nname = st.text_input("品名規格")
                nloc = st.text_input("儲位")
                nstock = st.number_input("初始庫存", 0)
                nsafe = st.number_input("安全庫存", 0)
                if st.form_submit_button("確認建檔"):
                    if nid in df_inv["刀具編號"].values: st.error("編號重複！")
                    else:
                        new_r = pd.DataFrame([{"分類": ncat, "刀具編號": nid, "品名規格": nname, "儲位": nloc, "目前庫存": nstock, "安全庫存": nsafe}])
                        pd.concat([df_inv, new_r], ignore_index=True).to_csv(F_INV, index=False)
                        backup_data() # 建檔也備份
                        st.success("建檔成功！")
                        st.rerun()
    else: st.warning("🔒 需密碼")

# ==========================================
# TAB 3: 歷史紀錄
# ==========================================
with t3:
    if st.text_input("輸入密碼查看歷史", type="password", key="pw_log") == "1234":
        st.markdown("### 📜 完整出入庫歷史紀錄 (可看工單號碼)")
        df_log_latest = pd.read_csv(F_LOG)
        if "工單號碼" not in df_log_latest.columns: df_log_latest["工單號碼"] = "無"
        st.dataframe(df_log_latest, use_container_width=True)
    else: st.warning("🔒 僅限管理人員")
