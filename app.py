import streamlit as st
import pandas as pd
import requests
import time
import io

# --- 1. 設定區 ---
# 這些 CSV 連結是讀取即時資料最穩定、不用安裝額外套件的方式
INV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTo2vi_36qF4mzPkxzNOJPTip7y-TXJLBm745noRRa4v_L_qkJ0DhFkaJ7tvYLCYWdFV3wbXOtH--zJ/pub?gid=0&single=true&output=csv"
LOG_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTo2vi_36qF4mzPkxzNOJPTip7y-TXJLBm745noRRa4v_L_qkJ0DhFkaJ7tvYLCYWdFV3wbXOtH--zJ/pub?gid=1320901506&single=true&output=csv"
SET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTo2vi_36qF4mzPkxzNOJPTip7y-TXJLBm745noRRa4v_L_qkJ0DhFkaJ7tvYLCYWdFV3wbXOtH--zJ/pub?gid=657176737&single=true&output=csv"

WEBHOOK_URL = "https://script.google.com/macros/s/AKfycbyZ6-S7x4fp4iCQbdpClMlXQFUxQ9q036XFtCZxuObS2mqaF7wv-U26QOJhqGsvxHyskQ/exec"

# --- 2. 函數區 ---
@st.cache_data(ttl=5) # 短快取，搭配下方時間戳記技術實現即時讀取
def get_data():
    try:
        # 使用時間戳記強制 Google 丟棄舊快取，讀取最新資料
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

# 初始化 Session State
if 'data' not in st.session_state:
    st.session_state.data = get_data()

# 同步按鈕
if st.button("🔄 立即同步最新庫存"):
    st.session_state.data = get_data()
    st.rerun()

df_inv, df_log, df_set = st.session_state.data

# 在此加入你原本的 TAB 與扣庫存邏輯 (呼叫 get_sh().worksheet(...).update_cell 時會自動運作)
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
        # 取得對應的 Index
        idx = df_inv[df_inv["品名規格"] == t_name].index[0]
        t_sel = df_inv.loc[idx, "刀具編號"]
        cur_stock = int(df_inv.loc[idx, "目前庫存"])
        st.info(f"編號:{t_sel} | 儲位:{df_inv.loc[idx, '儲位']} | 庫存:{cur_stock}")
        
        # 數量調整
        if "q_val" not in st.session_state: st.session_state["q_val"] = 1
        col1, col2 = st.columns(2)
        with col1: 
            if st.button("➕ 加1", key="b_add"): st.session_state["q_val"] += 1; st.rerun()
        with col2: 
            if st.button("🔄 歸1", key="b_res"): st.session_state["q_val"] = 1; st.rerun()
        
        qty = st.number_input("數量", min_value=1, value=st.session_state["q_val"])
        st.session_state["q_val"] = qty
        
        # 領用資訊
        u_list = df_set["人員"].replace("", pd.NA).dropna().unique().tolist()
        m_list = df_set["機台"].replace("", pd.NA).dropna().tolist()
        u = st.selectbox("人員", u_list)
        m = st.selectbox("機台", m_list)
        r = st.selectbox("原因", ["正常磨損", "斷刀", "架機", "其他"])
        wo = st.text_input("工單").strip()
        
        if st.button("確認領用", type="primary", use_container_width=True):
            if qty > cur_stock:
                st.error("❌ 庫存不足！")
            else:
                # 準備傳送給 Apps Script 的資料
                payload = {
                    "action": "領用",
                    "row": idx + 2, # 告訴後端要改哪一行
                    "t_sel": t_sel,
                    "qty": qty,
                    "u": u,
                    "m": m,
                    "r": r,
                    "wo": wo
                }
                
                try:
                    # 發送請求
                    response = requests.post(WEBHOOK_URL, json=payload)
                    if response.status_code == 200:
                        # --- Optimistic UI 更新 (讓網頁感覺變快) ---
                        st.session_state.data[0].loc[idx, "目前庫存"] -= qty
                        
                        st.success(f"✅ 已領刀：{t_name} x {qty}")
                        st.session_state["q_val"] = 1
                        import time
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error("寫入失敗，請確認 Apps Script 部署")
                except Exception as e:
                    st.error(f"連線失敗: {e}")
with t2:
    st.header("📦 庫存總覽")
    # 顯示所有庫存資料，方便課長組長快速檢閱
    st.dataframe(df_inv, use_container_width=True)
    
    st.divider()
    
    st.header("⚙️ 系統管理")
    mode = st.radio("選擇操作模式", ["刀具建檔", "庫存校正"], horizontal=True)
    
    if mode == "刀具建檔":
        st.subheader("📝 新增刀具")
        with st.form("new_tool_form"):
            new_id = st.text_input("刀具編號")
            new_name = st.text_input("品名規格")
            new_cat = st.text_input("分類")
            new_loc = st.text_input("儲位")
            new_qty = st.number_input("初始庫存", min_value=0, value=0)
            
            if st.form_submit_button("確認建檔"):
                payload = {
                    "action": "建檔",
                    "t_id": new_id,
                    "t_name": new_name,
                    "cat": new_cat,
                    "loc": new_loc,
                    "qty": new_qty
                }
                if post_data_to_sheet(payload):
                    st.success("✅ 建檔成功！(請重新整理以更新清單)")
                else:
                    st.error("❌ 建檔失敗，請確認 Webhook 設定")

    elif mode == "庫存校正":
        st.subheader("🔧 庫存數量校正")
        # 選擇要校正的刀具
        target_tool = st.selectbox("選擇刀具", df_inv["品名規格"].tolist())
        current_inv = df_inv[df_inv["品名規格"] == target_tool].iloc[0]
        
        st.write(f"目前庫存：{current_inv['目前庫存']} | 儲位：{current_inv['儲位']}")
        new_adj_qty = st.number_input("輸入正確庫存總數", min_value=0, value=int(current_inv['目前庫存']))
        
        if st.button("確認校正"):
            payload = {
                "action": "校正",
                "t_sel": current_inv['刀具編號'],
                "new_qty": new_adj_qty
            }
            if post_data_to_sheet(payload):
                st.success(f"✅ {target_tool} 已校正為 {new_adj_qty}")
                # 樂觀更新記憶體中的顯示
                idx = df_inv[df_inv["刀具編號"] == current_inv['刀具編號']].index[0]
                st.session_state.data[0].loc[idx, "目前庫存"] = new_adj_qty
                st.rerun()
            else:
                st.error("❌ 校正失敗")
with t3:
    # --- 【關鍵修正】：確保 T3 區塊每次渲染時都讀取當下最新的 Session State ---
    _, df_log, _ = st.session_state.data
    
    if st.text_input("密碼", type="password", key="pw3") == "1234":
        st.header("📊 消耗分析與報表")
        
        if not df_log.empty:
            # 確保欄位名稱正確 (這裡將數量強制轉數值)
            df_log["數量"] = pd.to_numeric(df_log["數量"], errors='coerce').fillna(0)
            df_usage = df_log[df_log["動作"] == "領用"].copy()
            
            # --- 圖表區 ---
            if not df_usage.empty:
                c1, c2, c3 = st.columns(3)
                with c1: 
                    st.markdown("**機台消耗排行**")
                    st.bar_chart(df_usage.groupby("備註")["數量"].sum())
                with c2: 
                    st.markdown("**人員領用統計**")
                    st.bar_chart(df_usage.groupby("經辦人員")["數量"].sum())
                with c3: 
                    st.markdown("**原因分析統計**")
                    st.bar_chart(df_usage.groupby("原因類型")["數量"].sum())

            st.markdown("---")
            st.header("📜 歷史紀錄進階篩選")
            
            # --- 進階篩選區 ---
            col_a, col_b, col_c = st.columns(3)
            
            # 這裡重新讀取一次設定資料以確保下拉選單是最新的
            _, _, df_set = st.session_state.data 
            
            all_reasons = ["正常磨損", "斷刀", "架機", "其他"]
            sel_reasons = col_a.multiselect("篩選原因:", all_reasons, default=[])
            
            all_staff = df_set["人員"].replace("", pd.NA).dropna().unique().tolist()
            sel_staff = col_b.multiselect("篩選人員:", all_staff, default=[])
            
            all_machines = df_set["機台"].replace("", pd.NA).dropna().tolist()
            sel_machines = col_c.multiselect("篩選機台:", all_machines, default=[])
            
            search_wo = st.text_input("🔍 搜尋工單號碼 (選填):")
            
            # --- 綜合過濾邏輯 ---
            df_filtered = df_log.copy()
            
            if sel_reasons:
                df_filtered = df_filtered[df_filtered["原因類型"].astype(str).isin([str(s) for s in sel_reasons])]
            if sel_staff:
                df_filtered = df_filtered[df_filtered["經辦人員"].astype(str).isin([str(s) for s in sel_staff])]
            if sel_machines:
                df_filtered = df_filtered[df_filtered["備註"].astype(str).isin([str(s) for s in sel_machines])]
            
            if search_wo and search_wo.strip() != "":
                if "工單號碼" in df_filtered.columns:
                    df_filtered = df_filtered[df_filtered["工單號碼"].astype(str).str.contains(search_wo.strip(), case=False, na=False)]
            
            st.dataframe(df_filtered, use_container_width=True)
            
            # 報表匯出
            buf = io.BytesIO()
            with pd.ExcelWriter(buf) as w:
                df_log.to_excel(w, sheet_name='紀錄', index=False)
                df_inv.to_excel(w, sheet_name='庫存', index=False)
            st.download_button("📥 下載完整報表 (Excel)", buf.getvalue(), "CNC_Report.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
