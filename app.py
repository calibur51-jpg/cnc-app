import streamlit as st
import pandas as pd
import requests
import time
import io
from PIL import Image

# --- 【初始化】自動化 QR 參數讀取 ---
if 'scanned_id' not in st.session_state:
    st.session_state.scanned_id = None

# 讀取網址參數 (自動偵測掃描結果)
query_params = st.query_params
if "scan" in query_params:
    st.session_state.scanned_id = query_params["scan"]

# --- 1. 設定區 ---
INV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTo2vi_36qF4mzPkxzNOJPTip7y-TXJLBm745noRRa4v_L_qkJ0DhFkaJ7tvYLCYWdFV3wbXOtH--zJ/pub?gid=0&single=true&output=csv"
LOG_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTo2vi_36qF4mzPkxzNOJPTip7y-TXJLBm745noRRa4v_L_qkJ0DhFkaJ7tvYLCYWdFV3wbXOtH--zJ/pub?gid=1320901506&single=true&output=csv"
SET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTo2vi_36qF4mzPkxzNOJPTip7y-TXJLBm745noRRa4v_L_qkJ0DhFkaJ7tvYLCYWdFV3wbXOtH--zJ/pub?gid=657176737&single=true&output=csv"

WEBHOOK_URL = "https://script.google.com/macros/s/AKfycbyZ6-S7x4fp4iCQbdpClMlXQFUxQ9q036XFtCZxuObS2mqaF7wv-U26QOJhqGsvxHyskQ/exec"

# --- 2. 函數區 ---
@st.cache_data(ttl=5)
def get_data():
    try:
        ts = time.time()
        df_inv = pd.read_csv(f"{INV_URL}&_={ts}", encoding='utf-8-sig')
        df_log = pd.read_csv(f"{LOG_URL}&_={ts}", encoding='utf-8-sig')
        df_set = pd.read_csv(f"{SET_URL}&_={ts}", encoding='utf-8-sig')
        return df_inv, df_log, df_set
    except Exception as e:
        st.error(f"連線失敗: {e}")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

def post_data_to_sheet(payload):
    try:
        response = requests.post(WEBHOOK_URL, json=payload)
        return response.status_code == 200
    except:
        return False

# --- 3. 介面區 ---
st.title("明星精密刀具管理系統")

if 'data' not in st.session_state:
    st.session_state.data = get_data()

if st.button("🔄 立即同步最新庫存"):
    st.session_state.data = get_data()
    st.rerun()

df_inv, df_log, df_set = st.session_state.data

t1, t2, t3, t4 = st.tabs(["領用", "後台", "紀錄", "進貨與盤點系統"])
with t1:
    st.header("🔪 刀具領用")
    _, df_log, df_set = st.session_state.data
    
    # --- 【已移除 QR 掃描區塊】 ---

    # --- 3. 篩選與選擇邏輯 ---
    if "scanned_id" in st.session_state and st.session_state.scanned_id is not None:
        match = df_inv[df_inv["刀具編號"].astype(str) == st.session_state.scanned_id]
        if not match.empty:
            st.session_state["t1_cat"] = match.iloc[0]["分類"]
            st.session_state["t1_tool"] = match.iloc[0]["品名規格"]
            st.session_state.scanned_id = None # 清除狀態
        else:
            st.error(f"❌ 找不到編號 {st.session_state.scanned_id} 的刀具")
            st.session_state.scanned_id = None

    cats = ["全部"] + df_inv["分類"].unique().tolist()
    cat_sel = st.selectbox("分類", cats, key="t1_cat")
    
    df_f = df_inv if cat_sel == "全部" else df_inv[df_inv["分類"] == cat_sel]
    t_list = df_f["品名規格"].tolist()
    
    if st.session_state.get("t1_tool") not in t_list:
        st.session_state["t1_tool"] = t_list[0] if t_list else None
    
    t_name = st.selectbox("選擇領用刀具", t_list, key="t1_tool")

    cur_stock = 0
    idx = 0
    t_sel = ""
    
    tool_info = df_inv[df_inv["品名規格"] == t_name]
    if not tool_info.empty:
        idx = tool_info.index[0]
        t_sel = tool_info.loc[idx, "刀具編號"]
        cur_stock = int(tool_info.loc[idx, "目前庫存"])
        st.info(f"編號:{t_sel} | 儲位:{tool_info.loc[idx, '儲位']} | 庫存:{cur_stock}")
    else:
        st.warning("⚠️ 請選擇刀具規格")

    # (以下程式碼完全不變，維持你的領用邏輯)
    if "q_val" not in st.session_state: st.session_state["q_val"] = 1
    c1, c2 = st.columns(2)
    with c1: 
        if st.button("➕ 加1", key="b_add"): 
            st.session_state["q_val"] += 1
            st.rerun()
    with c2: 
        if st.button("🔄 歸1", key="b_res"): 
            st.session_state["q_val"] = 1
            st.rerun()
    qty = st.number_input("數量", min_value=1, value=st.session_state["q_val"])
    st.session_state["q_val"] = qty
    u_list = df_set["人員"].replace("", pd.NA).dropna().unique().tolist()
    m_list = df_set["機台"].replace("", pd.NA).dropna().tolist()
    u = st.selectbox("人員", u_list, key="t1_user")
    m = st.selectbox("機台", m_list, key="t1_machine")
    r = st.selectbox("原因", ["正常磨損", "斷刀", "架機", "其他"], key="t1_reason")
    wo = st.text_input("工單", key="t1_wo").strip()
    msg_area = st.empty()
    if st.button("確認領用", type="primary", use_container_width=True):
        if qty > cur_stock:
            msg_area.error("❌ 庫存不足！")
        else:
            with st.spinner("正在執行領用作業..."):
                payload = {"action": "領用", "row": idx + 2, "t_sel": t_sel, "qty": qty, "u": u, "m": m, "r": r, "wo": wo}
                try:
                    response = requests.post(WEBHOOK_URL, json=payload, timeout=10)
                    if response.status_code == 200:
                        st.session_state.data[0].loc[idx, "目前庫存"] -= qty
                        st.session_state["q_val"] = 1
                        msg_area.success(f"✅ 已領刀：{t_name} x {qty}")
                        time.sleep(1.5)
                        st.rerun()
                    else:
                        msg_area.error(f"❌ 寫入失敗")
                except Exception as e:
                    msg_area.error(f"❌ 寫入失敗: {e}")

# (其他 T2, T3, T4 區塊保持不變...)
