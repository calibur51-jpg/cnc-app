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
with t2:
    st.header("🔒 管理員專區")
    pw = st.text_input("輸入管理員密碼", type="password", key="pw_t2")
    
    if pw == "1234":
        st.success("✅ 驗證成功，進入管理模式")
        st.divider()
        with st.expander("📦 點擊查看所有刀具庫存總覽", expanded=False):
            categories = ["全部"] + df_inv["分類"].dropna().unique().tolist()
            c1, c2 = st.columns(2)
            with c1:
                sel_cat = st.selectbox("分類篩選", options=categories)
            with c2:
                search_text = st.text_input("搜尋關鍵字 (編號/名稱)")
            df_show = df_inv.copy()
            if sel_cat != "全部":
                df_show = df_show[df_show["分類"] == sel_cat]
            if search_text:
                mask = df_show["刀具編號"].astype(str).str.contains(search_text, case=False, na=False) | \
                       df_show["品名規格"].astype(str).str.contains(search_text, case=False, na=False)
                df_show = df_show[mask]
            st.dataframe(df_show, use_container_width=True)
        st.divider()
        st.header("⚙️ 系統管理")
        mode = st.radio("選擇操作模式", ["刀具建檔", "庫存校正"], horizontal=True)
        if mode == "刀具建檔":
            st.subheader("📝 新增刀具")
            if st.session_state.get("last_action") == "建檔":
                st.success("✅ 建檔成功！系統已同步。")
                del st.session_state.last_action
            category_options = ["銑刀", "鑽頭", "絲攻", "捨棄式刀片", "其他"]
            with st.form("new_tool_form", clear_on_submit=True):
                new_id = st.text_input("刀具編號")
                new_name = st.text_input("品名規格")
                new_cat = st.selectbox("分類", options=category_options)
                new_loc = st.text_input("儲位")
                new_qty = st.number_input("初始庫存", min_value=0, value=0)
                if st.form_submit_button("確認建檔"):
                    payload = {"action": "建檔", "t_id": new_id, "t_name": new_name, "cat": new_cat, "loc": new_loc, "qty": new_qty}
                    if post_data_to_sheet(payload):
                        st.session_state.last_action = "建檔"
                        st.rerun()
                    else:
                        st.error("❌ 建檔失敗")
# --- 3. 庫存校正區塊 (終極修復防退版) ---
        elif mode == "庫存校正":
            st.subheader("🔧 庫存數量校正")
            # 顯示校正成功訊息
            if st.session_state.get("last_action") == "校正":
                st.success("✅ 庫存校正成功！")
                del st.session_state.last_action
                
            target_tool = st.selectbox("選擇刀具", df_inv["品名規格"].tolist())
            current_inv = df_inv[df_inv["品名規格"] == target_tool].iloc[0]
            
            # 💡 終極防呆：先強轉數字，用 astype(int) 確保型態，再用 max(0, ...) 鎖定最小值
            try:
                # 這樣寫最安全，管它是字串、浮點數還是負數，都能完美轉成標準整數
                raw_qty = int(pd.Series(current_inv['目前庫存']).to_numeric(errors='coerce').fillna(0).astype(int).iloc[0])
            except:
                # 萬一真的有鬼，直接給它 0，絕對不讓網頁崩潰
                raw_qty = 0
                
            default_qty = max(0, raw_qty) 
            
            st.write(f"目前庫存：{raw_qty} | 儲位：{current_inv['儲位']}")
            
            # 使用計算後的 default_qty，確保絕對不會低於 min_value=0
            new_adj_qty = st.number_input("輸入正確庫存總數", min_value=0, value=default_qty)
            
            if st.button("確認校正"):
                payload = {"action": "校正", "t_sel": current_inv['刀具編號'], "new_qty": new_adj_qty}
                if post_data_to_sheet(payload):
                    st.session_state.last_action = "校正"
                    # 樂觀更新記憶體
                    idx = df_inv[df_inv["刀具編號"] == current_inv['刀具編號']].index[0]
                    st.session_state.data[0].loc[idx, "目前庫存"] = new_adj_qty
                    st.rerun()
                else:
                    st.error("❌ 校正失敗")
    elif pw != "":
        st.warning("⚠️ 密碼錯誤，請重新輸入")
    else:
        st.info("請輸入管理員密碼以存取管理功能")
with t3:
    _, df_log, _ = st.session_state.data
    
    st.header("📊 刀具管理戰情室")
    
    if st.text_input("輸入密碼", type="password", key="pw3") == "1234":
        if not df_log.empty:
            # 確保數量是數字格式
            df_log["數量"] = pd.to_numeric(df_log["數量"], errors='coerce').fillna(0)
            
            # 檢查歷史紀錄有沒有「單價」欄位，沒有就去對照庫存表的單價
            if "單價" in df_log.columns:
                df_log["單價"] = pd.to_numeric(df_log["單價"], errors='coerce').fillna(0)
            else:
                price_map = df_inv.set_index("刀具編號")["單價"].to_dict()
                df_log["單價"] = df_log["刀具編號"].map(price_map).fillna(0)
                df_log["單價"] = pd.to_numeric(df_log["單價"], errors='coerce').fillna(0)
            
            # --- 1. 原本的戰情指標與圖表 ---
            df_usage = df_log[df_log["動作"] == "領用"].copy()
            c_m1, c_m2, c_m3 = st.columns(3)
            c_m1.metric("總領用次數", len(df_usage))
            c_m2.metric("總消耗數量", int(df_usage["數量"].sum()))
            c_m3.metric("涵蓋機台數", df_usage["備註"].nunique())
            
            st.divider()
            st.subheader("📈 歷史累積消耗分析")
            st.markdown("**🔥 刀具領用排行 (Top 5)**")
            top_tools = df_usage.groupby("刀具編號")["數量"].sum().sort_values(ascending=False).head(5)
            st.bar_chart(top_tools)
            
            col1, col2, col3 = st.columns(3)
            with col1: 
                st.markdown("**機台消耗**")
                st.bar_chart(df_usage.groupby("備註")["數量"].sum())
            with col2: 
                st.markdown("**人員領用**")
                st.bar_chart(df_usage.groupby("經辦人員")["數量"].sum())
            with col3: 
                st.markdown("**原因分析**")
                st.bar_chart(df_usage.groupby("原因類型")["數量"].sum())
            
            st.divider()
            
            # --- 2. 原本的歷史紀錄進階篩選與下載 (自動補上品名規格) ---
            st.header("📜 歷史紀錄進階篩選")
            col_a, col_b, col_c = st.columns(3)
            _, _, df_set = st.session_state.data 
            
            sel_reasons = col_a.multiselect("篩選原因:", ["正常磨損", "斷刀", "架機", "其他"])
            sel_staff = col_b.multiselect("篩選人員:", df_set["人員"].replace("", pd.NA).dropna().unique().tolist())
            sel_machines = col_c.multiselect("篩選機台:", df_set["機台"].replace("", pd.NA).dropna().tolist())
            search_wo = st.text_input("🔍 搜尋工單號碼:")
            
            df_filtered = df_log.copy()
            name_map = df_inv.set_index("刀具編號")["品名規格"].to_dict()
            df_filtered["品名規格"] = df_filtered["刀具編號"].map(name_map).fillna("未知刀具")
            
            all_cols = df_filtered.columns.tolist()
            if "品名規格" in all_cols and "刀具編號" in all_cols:
                all_cols.remove("品名規格")
                idx_id = all_cols.index("刀具編號")
                all_cols.insert(idx_id + 1, "品名規格")
                df_filtered = df_filtered[all_cols]

            if sel_reasons: df_filtered = df_filtered[df_filtered["原因類型"].isin(sel_reasons)]
            if sel_staff: df_filtered = df_filtered[df_filtered["經辦人員"].isin(sel_staff)]
            if sel_machines: df_filtered = df_filtered[df_filtered["備註"].isin(sel_machines)]
            if search_wo: df_filtered = df_filtered[df_filtered["工單號碼"].astype(str).str.contains(search_wo.strip(), case=False, na=False)]
            
            st.dataframe(df_filtered.sort_values(by="時間", ascending=False), use_container_width=True)
            
            buf = io.BytesIO()
            with pd.ExcelWriter(buf) as w:
                df_filtered.to_excel(w, sheet_name='紀錄(含規格)', index=False)
                df_inv.to_excel(w, sheet_name='庫存總表', index=False)
            st.download_button("📥 下載完整總歷史報表 (含品名規格)", buf.getvalue(), "CNC_Full_Report_With_Names.xlsx")
            
            st.divider()

            # --- 3. 本月財務與進銷存對帳區 ---
            df_log["時間"] = pd.to_datetime(df_log["時間"], errors='coerce')
            current_month = pd.Timestamp.now().strftime("%Y-%m")
            df_this_month = df_log[df_log["時間"].dt.strftime("%Y-%m") == current_month].copy()
            
            st.header(f"📅 本月 ({current_month}) 財務與進銷存對帳表")
            
            if not df_this_month.empty:
                df_in = df_this_month[df_this_month["動作"] == "進貨"].groupby("刀具編號")["數量"].sum().reset_index(name="本月進貨總數")
                df_out = df_this_month[df_this_month["動作"] == "領用"].groupby("刀具編號")["數量"].sum().reset_index(name="本月領用總數")
                df_prices = df_this_month.groupby("刀具編號")["單價"].max().reset_index(name="單價")
                
                df_m_report = df_prices.merge(df_in, on="刀具編號", how="left").merge(df_out, on="刀具編號", how="left")
                df_m_report["本月進貨總數"] = df_m_report["本月進貨總數"].fillna(0)
                df_m_report["本月領用總數"] = df_m_report["本月領用總數"].fillna(0)
                
                df_m_report["品名規格"] = df_m_report["刀具編號"].map(name_map).fillna("未命名刀具")
                
                df_m_report["本月進貨總金額"] = df_m_report["本月進貨總數"] * df_m_report["單價"]
                df_m_report["本月用刀總金額"] = df_m_report["本月領用總數"] * df_m_report["單價"]
                
                df_m_report = df_m_report[["刀具編號", "品名規格", "單價", "本月進貨總數", "本月進貨總金額", "本月領用總數", "本月用刀總金額"]]
                
                c_f1, c_f2 = st.columns(2)
                c_f1.metric("本月買刀總金額", f"${int(df_m_report['本月進貨總金額'].sum()):,}")
                c_f2.metric("本月用刀總金額 (消耗成本)", f"${int(df_m_report['本月用刀總金額'].sum()):,}")
                
                st.dataframe(df_m_report, use_container_width=True)
                
                buf_m = io.BytesIO()
                with pd.ExcelWriter(buf_m) as w:
                    df_m_report.to_excel(w, sheet_name='本月財務對帳', index=False)
                st.download_button(f"📥 下載 {current_month} 財務對帳 Excel", buf_m.getvalue(), f"CNC_Monthly_Financial_Report_{current_month}.xlsx")
            else:
                st.info("本月目前尚無任何進貨或領用紀錄。")
                
        else:
            st.info("目前沒有歷史紀錄數據。")
    else:
        st.info("請輸入密碼以查看數據分析。")
with t4:
    st.header("📥 進貨與盤點系統")
    pw = st.text_input("輸入管理員密碼", type="password", key="pw_t4")
    if pw == "1234":
        st.success("✅ 驗證成功")
        st.divider()
        low_stock_df = df_inv[df_inv["目前庫存"] <= df_inv["安全庫存"]]
        if not low_stock_df.empty:
            st.warning(f"🚨 注意：共有 {len(low_stock_df)} 項刀具低於安全庫存！")
            with st.expander("📦 查看低庫存清單", expanded=True):
                st.dataframe(low_stock_df[["品名規格", "目前庫存", "安全庫存", "儲位"]], use_container_width=True)
        else:
            st.success("✅ 所有庫存皆在安全水位以上，運作正常。")
        st.divider()
        st.subheader("⚙️ 選擇目標刀具")
        categories = ["全部"] + df_inv["分類"].dropna().unique().tolist()
        c1, c2 = st.columns(2)
        with c1:
            sel_cat = st.selectbox("篩選分類", options=categories, key="t4_cat")
        with c2:
            search_text = st.text_input("關鍵字搜尋", key="t4_search")
        df_show = df_inv.copy()
        if sel_cat != "全部":
            df_show = df_show[df_show["分類"] == sel_cat]
        if search_text:
            mask = df_show["刀具編號"].astype(str).str.contains(search_text, case=False, na=False) | \
                   df_show["品名規格"].astype(str).str.contains(search_text, case=False, na=False)
            df_show = df_show[mask]
        tool_options = df_show["品名規格"].tolist()
        if not tool_options:
            st.error("找不到符合條件的刀具")
        else:
            sel_tool_name = st.selectbox("搜尋結果", tool_options, key="t4_tool_sel")
            tool_info = df_show[df_show["品名規格"] == sel_tool_name].iloc[0]
            cur_qty = int(tool_info["目前庫存"])
            safe_qty = int(tool_info["安全庫存"])
            price = tool_info["單價"]
            col_a, col_b, col_c = st.columns(3)
            col_a.metric("目前庫存", cur_qty)
            col_b.metric("安全水位", safe_qty)
            col_c.metric("單價", f"${price}")
            mode = st.radio("選擇操作模式", ["進貨", "盤點"], horizontal=True)
            with st.form("t4_action_form", clear_on_submit=True):
                qty_input = st.number_input("數量", min_value=0, value=0)
                u_input = st.text_input("操作人員")
                btn_text = "確認進貨 (累加)" if mode == "進貨" else "確認盤點 (覆寫)"
                if st.form_submit_button(btn_text):
                    payload = {
                        "action": mode,
                        "t_id": tool_info["刀具編號"],
                        "qty": qty_input,
                        "new_qty": qty_input,
                        "u": u_input
                    }
                    if post_data_to_sheet(payload):
                        idx = df_inv[df_inv["刀具編號"] == tool_info["刀具編號"]].index[0]
                        if mode == "進貨":
                            st.session_state.data[0].loc[idx, "目前庫存"] += qty_input
                        else:
                            st.session_state.data[0].loc[idx, "目前庫存"] = qty_input
                        st.session_state.success_msg = f"✅ {btn_text}成功！"
                        st.rerun()
                    else:
                        st.error("❌ 操作失敗")
        if "success_msg" in st.session_state:
            st.success(st.session_state.success_msg)
            del st.session_state.success_msg
    elif pw != "":
        st.warning("⚠️ 密碼錯誤")
    else:
        st.info("請輸入管理員密碼以存取進貨與盤點功能")
