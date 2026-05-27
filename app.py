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
# 💡 修正 1：加上 ttl=5（快取5秒自動過期），並指定 show_spinner=False 讓重整更流暢
@st.cache_data(ttl=5, show_spinner=False)
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

# --- 3. 畫面開頭與天王老子同步按鈕 ---
st.title("🛠️ CNC 刀具庫存管理系統")

# 💡 修正 2：在最頂端直接提供手動重擊鈕，強制洗掉快取與 session 記憶
if st.button("🔄 立即同步雲端試算表 (當現場資料卡住時點擊)"):
    st.cache_data.clear()              # 清除所有快取
    get_data.clear()                   # 專門強制清除 get_data 函式的快取
    if "data" in st.session_state:
        del st.session_state.data      # 徹底刪除記憶體舊骨架
    st.success("✅ 已成功抹除舊記憶！正在重新連線 Google Sheets...")
    st.rerun()

st.divider()

# --- 4. 資料安全載入流 ---
# 💡 修正 3：確保載入邏輯能正確連動重新載入
if "data" not in st.session_state:
    st.session_state.data = get_data()

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
                sel_cat = st.selectbox("分類篩選", options=categories, key="t2_view_cat")
            with c2:
                search_text = st.text_input("搜尋關鍵字 (編號/名稱)", key="t2_view_search")
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
        
        all_categories = ["全部"] + df_inv["分類"].dropna().unique().tolist()
        
        # --- 1. 刀具建檔區塊 ---
        if mode == "刀具建檔":
            st.subheader("📝 新增刀具")
            if st.session_state.get("last_action") == "建檔":
                st.success("✅ 建檔成功！系統已同步。")
                del st.session_state.last_action
            
            category_options = df_inv["分類"].dropna().unique().tolist()
            if "其他" not in category_options:
                category_options.append("其他")
                
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
                        
        # --- 2. 庫存校正區塊 ---
        elif mode == "庫存校正":
            st.subheader("🔧 庫存數量校正")
            if st.session_state.get("last_action") == "校正":
                st.success("✅ 庫存校正成功！")
                del st.session_state.last_action
                
            cc1, cc2 = st.columns(2)
            with cc1:
                adj_cat = st.selectbox("篩選分類", options=all_categories, key="t2_adj_cat")
            with cc2:
                adj_search = st.text_input("關鍵字搜尋", key="t2_adj_search")
                
            df_adj_show = df_inv.copy()
            if adj_cat != "全部":
                df_adj_show = df_adj_show[df_adj_show["分類"] == adj_cat]
            if adj_search:
                mask_adj = df_adj_show["刀具編號"].astype(str).str.contains(adj_search, case=False, na=False) | \
                           df_adj_show["品名規格"].astype(str).str.contains(adj_search, case=False, na=False)
                df_adj_show = df_adj_show[mask_adj]
                
            tool_list_t2 = df_adj_show["品名規格"].tolist()
            
            if not tool_list_t2:
                st.error("❌ 找不到符合條件的刀具，請重新篩選或清除關鍵字")
            else:
                target_tool = st.selectbox("選擇目標刀具", tool_list_t2, key="t2_tool_sel")
                matched_inv_df = df_inv[df_inv["品名規格"] == target_tool]
                
                if not matched_inv_df.empty:
                    current_inv = matched_inv_df.iloc[0]
                    
                    try:
                        raw_qty = int(pd.Series(current_inv['currently_stock']).to_numeric(errors='coerce').fillna(0).astype(int).iloc[0])
                    except:
                        try:
                            raw_qty = int(pd.Series(current_inv['目前庫存']).to_numeric(errors='coerce').fillna(0).astype(int).iloc[0])
                        except:
                            raw_qty = 0
                        
                    default_qty = max(0, raw_qty) 
                    st.info(f"📊 目前系統紀錄庫存：{raw_qty}支 | 儲位：{current_inv['儲位']}")
                    
                    new_adj_qty = st.number_input("輸入正確現場庫存總數", min_value=0, value=default_qty)
                    
                    if st.button("確認校正", key="t2_adj_confirm_btn"):
                        payload = {"action": "校正", "t_sel": current_inv['刀具編號'], "new_qty": new_adj_qty}
                        if post_data_to_sheet(payload):
                            st.session_state.last_action = "校正"
                            idx = df_inv[df_inv["刀具編號"] == current_inv['刀具編號']].index[0]
                            try:
                                st.session_state.data[0].loc[idx, "目前庫存"] = new_adj_qty
                            except:
                                st.session_state.data[0].loc[idx, "currently_stock"] = new_adj_qty
                                
                            st.cache_data.clear() 
                            st.rerun()
                        else:
                            st.error("❌ 校正失敗")
                else:
                    st.warning("⚠️ 刀具資料同步中，請稍候...")

    elif pw != "":
        st.warning("⚠️ 密碼錯誤，請重新輸入")
    else:
        st.info("請輸入管理員密碼以存取管理功能")
with t3:
    st.header("📊 刀具管理戰情室")
    pw = st.text_input("輸入管理員密碼", type="password", key="pw_t3")
    
    if pw == "1234":
        # 每次進入強制洗掉快取，確保拿到最新後台資料
        st.cache_data.clear()
        
        _, df_log, _ = st.session_state.data
        df_inv = st.session_state.data[0]
        
        if not df_log.empty:
            # 1. 基礎資料與格式整理
            df_log["數量"] = pd.to_numeric(df_log["數量"], errors='coerce').fillna(0)
            
            # 終極月份防禦機制：自動補0 (5 變 05)
            def extract_clean_month(time_str):
                try:
                    s = str(time_str).strip().replace("/", "-")
                    parts = s.split(" ")[0].split("-")
                    if len(parts) >= 2:
                        year = parts[0]
                        month = parts[1].zfill(2)
                        return f"{year}-{month}"
                except:
                    pass
                return "未知月份"

            df_log["月份"] = df_log["時間"].apply(extract_clean_month)
            
            # 統一將 logs 的價格欄位轉為數字
            if "價格" in df_log.columns:
                df_log["價格"] = pd.to_numeric(df_log["價格"], errors='coerce').fillna(0)
            elif "單價" in df_log.columns:
                df_log["價格"] = pd.to_numeric(df_log["單價"], errors='coerce').fillna(0)
            else:
                df_log["價格"] = 0.0

            # --- 【看板與圖表區】 ---
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
            
            # --- 【📜 歷史紀錄進階篩選（不顯示價格）】 ---
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
            
            display_cols = ["時間", "動作", "刀具編號", "品名規格", "數量", "經辦人員", "原因類型", "備註", "工單號碼"]
            display_cols = [c for c in display_cols if c in df_filtered.columns]
            df_filtered = df_filtered[display_cols]

            if sel_reasons: df_filtered = df_filtered[df_filtered["原因類型"].isin(sel_reasons)]
            if sel_staff: df_filtered = df_filtered[df_filtered["經辦人員"].isin(sel_staff)]
            if sel_machines: df_filtered = df_filtered[df_filtered["備註"].isin(sel_machines)]
            if search_wo: df_filtered = df_filtered[df_filtered["工單號碼"].astype(str).str.contains(search_wo.strip(), case=False, na=False)]
            
            st.dataframe(df_filtered.sort_values(by="時間", ascending=False), use_container_width=True)
            
            st.divider()

            # --- 【💰 月底財務與進銷存對帳表】 ---
            current_month = "2026-05" 
            st.header(f"📅 本月 ({current_month}) 財務與進銷存對帳表")
            
            df_this_month = df_log[df_log["月份"] == current_month].copy()
            
            if not df_this_month.empty:
                df_prices = df_this_month[df_this_month["動作"] == "進貨"].groupby("刀具編號")["價格"].max().reset_index(name="當月單價")
                df_in = df_this_month[df_this_month["動作"] == "進貨"].groupby("刀具編號")["數量"].sum().reset_index(name="本月進貨量")
                df_out = df_this_month[df_this_month["動作"] == "領用"].groupby("刀具編號")["數量"].sum().reset_index(name="本月領用量")
                
                df_acc = df_inv[["分類", "刀具編號", "品名規格", "儲位", "目前庫存"]].copy()
                
                if "目前庫存" in df_acc.columns:
                    df_acc["目前庫存"] = pd.to_numeric(df_acc["目前庫存"], errors='coerce').fillna(0).astype(int)
                elif "currently_stock" in df_acc.columns:
                    df_acc["目前庫存"] = pd.to_numeric(df_acc["currently_stock"], errors='coerce').fillna(0).astype(int)
                    
                df_acc = df_acc.merge(df_prices, on="刀具編號", how="left")
                df_acc = df_acc.merge(df_in, on="刀具編號", how="left")
                df_acc = df_acc.merge(df_out, on="刀具編號", how="left")
                
                df_inv_clean = df_inv.copy()
                df_inv_clean["庫存主表單價"] = pd.to_numeric(df_inv_clean["單價"], errors='coerce').fillna(0).astype(float)
                inv_price_map = df_inv_clean.set_index("刀具編號")["庫存主表單價"].to_dict()
                
                df_acc["當月單價"] = pd.to_numeric(df_acc["當月單價"], errors='coerce').fillna(0).astype(float)
                df_acc["備用單價"] = df_acc["刀具編號"].map(inv_price_map).fillna(0).astype(float)
                df_acc["當月單價"] = df_acc.apply(lambda r: r["當月單價"] if r["當月單價"] > 0 else r["備用單價"], axis=1)
                
                df_acc["本月進貨量"] = df_acc["本月進貨量"].fillna(0).astype(int)
                df_acc["本月領用量"] = df_acc["本月領用量"].fillna(0).astype(int)
                
                df_acc["本月新購買總金額"] = df_acc["本月進貨量"] * df_acc["當月單價"]
                df_acc["現有庫存總價值"] = df_acc["目前庫存"] * df_acc["當月單價"]
                
                if "備用單價" in df_acc.columns:
                    df_acc = df_acc.drop(columns=["備用單價"])
                
                # 重新排列欄位順序，讓報表更直覺
                report_cols = ["分類", "刀具編號", "品名規格", "儲位", "目前庫存", "當月單價", "本月進貨量", "本月領用量", "本月新購買總金額", "現有庫存總價值"]
                report_cols = [c for c in report_cols if c in df_acc.columns]
                df_acc = df_acc[report_cols]
                
                # 上方核心財務小看板
                st.subheader("💰 本月財務對帳指標")
                c_f1, c_f2 = st.columns(2)
                c_f1.metric("📊 本月新購買刀總金額", f"${int(df_acc['本月新購買總金額'].sum()):,}")
                c_f2.metric("💰 廠內現有庫存總價值", f"${int(df_acc['現有庫存總價值'].sum()):,}")
                
                st.dataframe(df_acc, use_container_width=True)
                
                # --- 🎨 Excel 精裝高質感美化導出區 ---
                import io
                import openpyxl
                from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
                from openpyxl.utils import get_column_letter

                buffer = io.BytesIO()
                with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                    # 💡 核心優化：index=False 徹底移除最左邊醜醜的 0, 1, 2 流水號
                    df_acc.to_excel(writer, sheet_name='月底對帳表', index=False)
                    workbook = writer.book
                    worksheet = writer.sheets['月底對帳表']
                    
                    font_family = "Microsoft JhengHei" 
                    header_fill = PatternFill(start_color="1F497D", end_color="1F497D", fill_type="solid") # 專業高階深藍
                    total_fill = PatternFill(start_color="DCE6F1", end_color="DCE6F1", fill_type="solid")  # 總計列淡藍色
                    
                    header_font = Font(name=font_family, size=11, bold=True, color="FFFFFF")
                    data_font = Font(name=font_family, size=10)
                    total_font = Font(name=font_family, size=10, bold=True)
                    
                    thin_border = Border(
                        left=Side(style='thin', color='D9D9D9'),
                        right=Side(style='thin', color='D9D9D9'),
                        top=Side(style='thin', color='D9D9D9'),
                        bottom=Side(style='thin', color='D9D9D9')
                    )
                    
                    # 格式化表頭
                    for col_num in range(1, len(df_acc.columns) + 1):
                        cell = worksheet.cell(row=1, column=col_num)
                        cell.fill = header_fill
                        cell.font = header_font
                        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
                    
                    # 格式化資料列
                    max_row = len(df_acc) + 1
                    for row in range(2, max_row + 1):
                        for col in range(1, len(df_acc.columns) + 1):
                            cell = worksheet.cell(row=row, column=col)
                            cell.font = data_font
                            cell.border = thin_border
                            
                            # 1:分類, 2:刀具編號, 4:儲位 -> 置中
                            if col in [1, 2, 4]:
                                cell.alignment = Alignment(horizontal="center")
                            # 3:品名規格 -> 靠左
                            elif col == 3:
                                cell.alignment = Alignment(horizontal="left")
                            # 5:目前庫存, 6:當月單價, 7:本月進貨, 8:本月領用, 9:購買金額, 10:庫存價值 -> 靠右
                            else:
                                cell.alignment = Alignment(horizontal="right")
                                # 單價(6欄)、新購買金額(9欄)、庫存價值(10欄) 加上千分位與 $ 符號
                                if col in [6, 9, 10]:
                                    cell.number_format = '$#,##0'
                                else:
                                    cell.number_format = '#,##0'

                    # 💡 精裝版總計列
                    total_row = max_row + 1
                    for col_num in range(1, len(df_acc.columns) + 1):
                        t_cell = worksheet.cell(row=total_row, column=col_num)
                        t_cell.fill = total_fill
                        t_cell.border = thin_border
                    
                    worksheet.cell(row=total_row, column=3, value="總計 (Total)").font = total_font
                    worksheet.cell(row=total_row, column=3).alignment = Alignment(horizontal="right")
                    
                    # 用 Excel 原生公式進行對齊欄位加總
                    # E:目前庫存(5), G:本月進貨(7), H:本月領用(8), I:新購買金額(9), J:現有庫存價值(10)
                    sum_targets = [(5, 'E'), (7, 'G'), (8, 'H'), (9, 'I'), (10, 'J')]
                    for col_idx, col_letter in sum_targets:
                        t_cell = worksheet.cell(row=total_row, column=col_idx, value=f"=SUM({col_letter}2:{col_letter}{max_row})")
                        t_cell.font = total_font
                        t_cell.alignment = Alignment(horizontal="right")
                        if col_idx in [9, 10]:
                            t_cell.number_format = '$#,##0'
                        else:
                            t_cell.number_format = '#,##0'
                    
                    # 自動調整欄寬
                    for col in worksheet.columns:
                        max_len = max(len(str(cell.value or '')) for cell in col)
                        col_letter = get_column_letter(col[0].column)
                        worksheet.column_dimensions[col_letter].width = max(max_len + 4, 13)
                
                st.download_button(
                    label="📥 下載本月精裝高質感對帳 Excel",
                    data=buffer.getvalue(),
                    file_name=f"刀具月底對帳表_{current_month}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            else:
                st.info("本月份尚無任何歷史明細資料。")
                
    elif pw != "":
        st.warning("⚠️ 密碼錯誤")
    else:
        st.info("請輸入管理員密碼以存取戰情室功能")
with t4:
    st.header("📥 進貨與盤點系統")
    pw = st.text_input("輸入管理員密碼", type="password", key="pw_t4")
    if pw == "1234":
        st.success("✅ 驗證成功")
        st.divider()
        low_stock_df = df_inv[df_inv["currently_stock"] <= df_inv["安全庫存"]] if "currently_stock" in df_inv.columns else df_inv[df_inv["目前庫存"] <= df_inv["安全庫存"]]
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
            
            # 核心防呆：先抓出符合品名的資料集
            matched_df = df_show[df_show["品名規格"] == sel_tool_name]
            
            if not matched_df.empty:
                tool_info = matched_df.iloc[0]
                try:
                    cur_qty = int(tool_info["目前庫存"])
                except:
                    cur_qty = int(tool_info["currently_stock"])
                safe_qty = int(tool_info["安全庫存"])
                
                # 確保單價是標準數字
                try:
                    current_price = float(tool_info["單價"])
                except:
                    current_price = 0.0
                    
                col_a, col_b, col_c = st.columns(3)
                col_a.metric("目前庫存", cur_qty)
                col_b.metric("安全水位", safe_qty)
                col_c.metric("目前系統單價", f"${int(current_price)}")
                
                mode = st.radio("選擇操作模式", ["進貨", "盤點"], horizontal=True)
                
                with st.form("t4_action_form", clear_on_submit=True):
                    qty_input = st.number_input("數量", min_value=0, value=0)
                    
                    # 進貨時可以直接調整單價，預設帶入目前單價
                    if mode == "進貨":
                        price_input = st.number_input("本次進貨單價 (若有變動請直接修改)", min_value=0.0, value=current_price, step=10.0)
                    else:
                        price_input = current_price # 盤點模式不連動改價
                        
                    u_input = st.text_input("操作人員")
                    btn_text = "確認進貨 (累加庫存與更新單價)" if mode == "進貨" else "確認盤點 (覆寫庫存)"
                    
                    if st.form_submit_button(btn_text):
                        payload = {
                            "action": mode,
                            "t_id": tool_info["刀具編號"],
                            "qty": qty_input,
                            "new_qty": qty_input,
                            "price": price_input,
                            "u": u_input
                        }
                        if post_data_to_sheet(payload):
                            idx = df_inv[df_inv["刀具編號"] == tool_info["刀具編號"]].index[0]
                            
                            # 1. 處理庫存記憶體更新 (這次縮排完全理順了)
                            try:
                                if mode == "進貨":
                                    st.session_state.data[0].loc[idx, "目前庫存"] = cur_qty + qty_input
                                else:
                                    st.session_state.data[0].loc[idx, "currently_stock"] = qty_input
                            except:
                                try:
                                    if mode == "進貨":
                                        st.session_state.data[0].loc[idx, "currently_stock"] = cur_qty + qty_input
                                    else:
                                        st.session_state.data[0].loc[idx, "currently_stock"] = qty_input
                                except:
                                    pass
                                    
# 2. 處理單價記憶體更新
                            try:
                                st.session_state.data[0].loc[idx, "單價"] = price_input
                            except:
                                pass
                            
                            # 💡 核心修正：進貨成功後，立刻強制清除網頁快取，逼全站（含 t3 財務看板）重新讀取 Google Sheets
                            st.cache_data.clear() 
                            
                            st.session_state.success_msg = f"✅ {mode}成功！庫存與單價已即時同步。"
                            st.rerun()
                        else:
                            st.error("❌ 操作失敗，請檢查網路連線")
            else:
                st.warning("⚠️ 刀具資料加載中，請稍候...")
                
        if "success_msg" in st.session_state:
            st.success(st.session_state.success_msg)
            del st.session_state.success_msg
    elif pw != "":
        st.warning("⚠️ 密碼錯誤")
    else:
        st.info("請輸入管理員密碼以存取進貨與盤點功能")
