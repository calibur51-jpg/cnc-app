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
t1, t2, t3, t4 = st.tabs(["領用", "後台", "紀錄", "進貨與盤點系統"])
with t1:
    st.header("🔪 刀具領用")
    
    # --- 1. 掃描區 ---
    with st.expander("📷 掃描 QR Code"):
        img_file = st.file_uploader("點擊這裡拍照/上傳以掃描", type=["jpg", "jpeg", "png"])
        if img_file:
            img = Image.open(img_file)
            img_array = np.array(img)
            detector = cv2.QRCodeDetector()
            data, _, _ = detector.detectAndDecode(img_array)
            if data:
                st.session_state.scanned_id = data
                st.success(f"✅ 識別成功！編號: {data}")
            else:
                st.warning("⚠️ 無法識別此圖片，請確認 QR Code 清晰度")

    # --- 2. 篩選與選擇邏輯 ---
    # 決定預設選項索引
    default_idx = 0
    cat_sel = "全部"
    
    # 如果有掃描結果，自動帶入該刀具的分類與品名索引
    if "scanned_id" in st.session_state:
        match = df_inv[df_inv["刀具編號"].astype(str) == st.session_state.scanned_id]
        if not match.empty:
            cat_sel = match.iloc[0]["分類"]
            # 處理掃描後要自動選到的品名
            target_name = match.iloc[0]["品名規格"]
            del st.session_state.scanned_id # 清除暫存
        else:
            st.error("❌ 系統中找不到此編號的刀具")

    # 分類篩選
    cats = ["全部"] + df_inv["分類"].unique().tolist()
    # 注意：這裡將分類預選設為掃描到的分類
    cat_idx = cats.index(cat_sel) if cat_sel in cats else 0
    cat_sel = st.selectbox("分類", cats, index=cat_idx, key="t1_cat")
    
    # 篩選刀具清單
    df_f = df_inv if cat_sel == "全部" else df_inv[df_inv["分類"] == cat_sel]
    t_list = df_f["品名規格"].tolist()
    
    # 刀具選單 (處理掃描後的預設值)
    if "target_name" in locals() and target_name in t_list:
        default_idx = t_list.index(target_name)
        
    t_name = st.selectbox("選擇領用刀具", t_list, index=default_idx, key="t1_tool")
    
    # 取得選定刀具資訊
    idx = df_inv[df_inv["品名規格"] == t_name].index[0]
    t_sel = df_inv.loc[idx, "刀具編號"]
    cur_stock = int(df_inv.loc[idx, "目前庫存"])
    
    st.info(f"編號:{t_sel} | 儲位:{df_inv.loc[idx, '儲位']} | 庫存:{cur_stock}")
    
    # --- 3. 數量調整 ---
    if "q_val" not in st.session_state: st.session_state["q_val"] = 1
    
    c1, c2 = st.columns(2)
    with c1: 
        if st.button("➕ 加1", key="b_add"): st.session_state["q_val"] += 1; st.rerun()
    with c2: 
        if st.button("🔄 歸1", key="b_res"): st.session_state["q_val"] = 1; st.rerun()
    
    qty = st.number_input("數量", min_value=1, value=st.session_state["q_val"])
    st.session_state["q_val"] = qty
    
    # --- 4. 領用資訊 ---
    u_list = df_set["人員"].replace("", pd.NA).dropna().unique().tolist()
    m_list = df_set["機台"].replace("", pd.NA).dropna().tolist()
    u = st.selectbox("人員", u_list, key="t1_user")
    m = st.selectbox("機台", m_list, key="t1_machine")
    r = st.selectbox("原因", ["正常磨損", "斷刀", "架機", "其他"], key="t1_reason")
    wo = st.text_input("工單", key="t1_wo").strip()
    
    # --- 5. 確認領用 ---
    if st.button("確認領用", type="primary", use_container_width=True):
        if qty > cur_stock:
            st.error("❌ 庫存不足！")
        else:
            payload = {
                "action": "領用", "row": idx + 2, "t_sel": t_sel,
                "qty": qty, "u": u, "m": m, "r": r, "wo": wo
            }
            try:
                response = requests.post(WEBHOOK_URL, json=payload)
                if response.status_code == 200:
                    st.session_state.data[0].loc[idx, "目前庫存"] -= qty
                    st.success(f"✅ 已領刀：{t_name} x {qty}")
                    st.session_state["q_val"] = 1
                    import time; time.sleep(1); st.rerun()
                else:
                    st.error("寫入失敗，請確認 Apps Script 部署")
            except Exception as e:
                st.error(f"連線失敗: {e}")
with t2:
    st.header("🔒 管理員專區")
    pw = st.text_input("輸入管理員密碼", type="password", key="pw_t2")
    
    if pw == "1234":
        st.success("✅ 驗證成功，進入管理模式")
        st.divider()
        
        # --- 1. 折疊式庫存總覽 (含分類與搜尋) ---
        with st.expander("📦 點擊查看所有刀具庫存總覽", expanded=False):
            # 取得分類清單
            categories = ["全部"] + df_inv["分類"].dropna().unique().tolist()
            
            c1, c2 = st.columns(2)
            with c1:
                sel_cat = st.selectbox("分類篩選", options=categories)
            with c2:
                search_text = st.text_input("搜尋關鍵字 (編號/名稱)")
            
            # 過濾邏輯
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
        
        # --- 2. 刀具建檔區塊 ---
        if mode == "刀具建檔":
            st.subheader("📝 新增刀具")
            # 顯示建檔成功訊息 (顯示在區塊下方)
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

        # --- 3. 庫存校正區塊 ---
        elif mode == "庫存校正":
            st.subheader("🔧 庫存數量校正")
            # 顯示校正成功訊息 (顯示在區塊下方)
            if st.session_state.get("last_action") == "校正":
                st.success("✅ 庫存校正成功！")
                del st.session_state.last_action
                
            target_tool = st.selectbox("選擇刀具", df_inv["品名規格"].tolist())
            current_inv = df_inv[df_inv["品名規格"] == target_tool].iloc[0]
            
            st.write(f"目前庫存：{current_inv['目前庫存']} | 儲位：{current_inv['儲位']}")
            new_adj_qty = st.number_input("輸入正確庫存總數", min_value=0, value=int(current_inv['目前庫存']))
            
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
            df_log["數量"] = pd.to_numeric(df_log["數量"], errors='coerce').fillna(0)
            df_usage = df_log[df_log["動作"] == "領用"].copy()
            
            # --- 1. 戰情指標 ---
            c_m1, c_m2, c_m3 = st.columns(3)
            c_m1.metric("總領用次數", len(df_usage))
            c_m2.metric("總消耗數量", int(df_usage["數量"].sum()))
            c_m3.metric("涵蓋機台數", df_usage["備註"].nunique())
            
            st.divider()

            # --- 2. 視覺化分析 ---
            st.subheader("📈 消耗趨勢與排行")
            
            # 排行榜放在最上面，因為最重要
            st.markdown("**🔥 刀具領用排行 (Top 5)**")
            # 假設 logs 裡面記錄的是"刀具編號"，我們用它來分組
            top_tools = df_usage.groupby("刀具編號")["數量"].sum().sort_values(ascending=False).head(5)
            st.bar_chart(top_tools)
            
            # 另外三個分析圖
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
            
            # --- 3. 歷史紀錄與篩選 ---
            st.header("📜 歷史紀錄進階篩選")
            col_a, col_b, col_c = st.columns(3)
            _, _, df_set = st.session_state.data 
            
            sel_reasons = col_a.multiselect("篩選原因:", ["正常磨損", "斷刀", "架機", "其他"])
            sel_staff = col_b.multiselect("篩選人員:", df_set["人員"].replace("", pd.NA).dropna().unique().tolist())
            sel_machines = col_c.multiselect("篩選機台:", df_set["機台"].replace("", pd.NA).dropna().tolist())
            search_wo = st.text_input("🔍 搜尋工單號碼:")
            
            df_filtered = df_log.copy()
            if sel_reasons: df_filtered = df_filtered[df_filtered["原因類型"].isin(sel_reasons)]
            if sel_staff: df_filtered = df_filtered[df_filtered["經辦人員"].isin(sel_staff)]
            if sel_machines: df_filtered = df_filtered[df_filtered["備註"].isin(sel_machines)]
            if search_wo: df_filtered = df_filtered[df_filtered["工單號碼"].astype(str).str.contains(search_wo.strip(), case=False, na=False)]
            
            st.dataframe(df_filtered.sort_values(by="時間", ascending=False), use_container_width=True)
            
            # --- 4. 下載 ---
            buf = io.BytesIO()
            with pd.ExcelWriter(buf) as w:
                df_log.to_excel(w, sheet_name='紀錄', index=False)
                df_inv.to_excel(w, sheet_name='庫存', index=False)
            st.download_button("📥 下載完整報表", buf.getvalue(), "CNC_Report.xlsx")
        else:
            st.info("目前沒有歷史紀錄數據。")
    else:
        st.info("請輸入密碼以查看數據分析。")
with t4:
    st.header("📥 進貨與盤點系統")
    
    # 密碼保護 (使用不同的 key，避免與 T2 衝突)
    pw = st.text_input("輸入管理員密碼", type="password", key="pw_t4")
    
    if pw == "1234":
        st.success("✅ 驗證成功")
        st.divider()

        # --- 1. 庫存預警看板 ---
        low_stock_df = df_inv[df_inv["目前庫存"] <= df_inv["安全庫存"]]
        if not low_stock_df.empty:
            st.warning(f"🚨 注意：共有 {len(low_stock_df)} 項刀具低於安全庫存！")
            with st.expander("📦 查看低庫存清單", expanded=True):
                st.dataframe(low_stock_df[["品名規格", "目前庫存", "安全庫存", "儲位"]], use_container_width=True)
        else:
            st.success("✅ 所有庫存皆在安全水位以上，運作正常。")

        st.divider()

        # --- 2. 搜尋與篩選操作區 ---
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

            # 顯示資訊
            cur_qty = int(tool_info["目前庫存"])
            safe_qty = int(tool_info["安全庫存"])
            price = tool_info["單價"]
            
            col_a, col_b, col_c = st.columns(3)
            col_a.metric("目前庫存", cur_qty)
            col_b.metric("安全水位", safe_qty)
            col_c.metric("單價", f"${price}")

            # --- 3. 進貨/盤點表單 ---
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
                        # 強制更新記憶體
                        idx = df_inv[df_inv["刀具編號"] == tool_info["刀具編號"]].index[0]
                        if mode == "進貨":
                            st.session_state.data[0].loc[idx, "目前庫存"] += qty_input
                        else:
                            st.session_state.data[0].loc[idx, "目前庫存"] = qty_input
                        
                        st.session_state.success_msg = f"✅ {btn_text}成功！"
                        st.rerun()
                    else:
                        st.error("❌ 操作失敗")

        # 成功通知
        if "success_msg" in st.session_state:
            st.success(st.session_state.success_msg)
            del st.session_state.success_msg

    elif pw != "":
        st.warning("⚠️ 密碼錯誤")
    else:
        st.info("請輸入管理員密碼以存取進貨與盤點功能")
