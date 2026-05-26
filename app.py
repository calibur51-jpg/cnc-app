import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

def clean_pem_key(key_str):
    """ 強制格式化 PEM 字串，解決 InvalidByte 錯誤 """
    # 1. 移除前後多餘的空格
    key = key_str.strip()
    # 2. 處理 Windows 換行符號 (\r\n) 改為標準 Unix 換行 (\n)
    key = key.replace('\r\n', '\n')
    # 3. 確保中間沒有多餘的 \r
    key = key.replace('\r', '')
    # 4. 確保正確的 PEM 結尾 (有些情況下需要補上最後的換行)
    if not key.endswith('\n'):
        key += '\n'
    return key
    
# --- 1. 設定區 ---
INV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTo2vi_36qF4mzPkxzNOJPTip7y-TXJLBm745noRRa4v_L_qkJ0DhFkaJ7tvYLCYWdFV3wbXOtH--zJ/pub?gid=0&single=true&output=csv"
LOG_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTo2vi_36qF4mzPkxzNOJPTip7y-TXJLBm745noRRa4v_L_qkJ0DhFkaJ7tvYLCYWdFV3wbXOtH--zJ/pub?gid=1320901506&single=true&output=csv"
SET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTo2vi_36qF4mzPkxzNOJPTip7y-TXJLBm745noRRa4v_L_qkJ0DhFkaJ7tvYLCYWdFV3wbXOtH--zJ/pub?gid=657176737&single=true&output=csv"

# --- 2. 函數區 ---
@st.cache_resource
def get_sh():
    # 讀取 Secrets
    creds_dict = dict(st.secrets["gcp"])
    
    # 【關鍵】在這裡強制清洗私鑰
    creds_dict["private_key"] = clean_pem_key(creds_dict["private_key"])
    
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    return gspread.authorize(creds).open_by_key("1Y3XJLmzIH2y2l-XWkQfOzhEPBcxSyFFW3RvYpG6JZJ8")


# 呼叫測試
try:
    sh = get_sh()
    st.success("連線成功！")
except Exception as e:
    st.error(f"連線失敗，請檢查權限設定：{e}")
    
def get_data():
    try:
        df_inv = pd.read_csv(INV_URL, encoding='utf-8-sig')
        df_log = pd.read_csv(LOG_URL, encoding='utf-8-sig')
        df_set = pd.read_csv(SET_URL, encoding='utf-8-sig')
        return df_inv, df_log, df_set
    except Exception as e:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
# --- 3. 介面 ---
st.title("明星精密刀具管理系統")
if 'data' not in st.session_state:
    st.session_state.data = get_data()

if st.button("🔄 立即同步最新庫存", key="sync_data_button"):
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
        # 從 df_set 動態抓取清單，並過濾空值
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
                try:
                    # 1. 執行寫入 (將 get_sh() 連線儲存為 sh，避免重複呼叫)
                    sh = get_sh()
                    new_s = cur_stock - qty
                    
                    # 更新庫存
                    sh.worksheet("inventory").update_cell(idx + 2, df_inv.columns.get_loc("目前庫存") + 1, new_s)
                    
                    # 寫入紀錄 (確保 datetime 已匯入)
                    sh.worksheet("logs").append_row([
                        datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 
                        "領用", t_sel, qty, u, m, r, wo
                    ])
                    
                    # 2. 領用成功後的處理
                    st.success("✅ 領用成功！")
                    
                    # 關鍵步驟：清除緩存並強制重整頁面，這樣你馬上就能看到最新的庫存數據
                    st.cache_data.clear()
                    st.rerun()
                    
                except Exception as e:
                    # 如果寫入失敗，顯示具體錯誤，方便除錯
                    st.error(f"寫入失敗，請檢查權限或連線：{e}")
                
                # 這裡增加提示停留
                st.success(f"✅ 已領刀：{t_name} x {qty}")
                st.session_state["q_val"] = 1
                st.cache_data.clear()
                
                import time
                time.sleep(2) # 強制停留 2 秒，讓你絕對看得到
                st.rerun()

with t2:
    if st.text_input("密碼", type="password", key="pw2") == "1234":
        # 💡 新增：後台總庫存瀏覽清單
        with st.expander("📦 查看目前所有刀具庫存", expanded=False):
            st.dataframe(df_inv, use_container_width=True)
            
        sub = st.radio("功能", ["叫貨", "進貨", "建檔", "校正"], horizontal=True)
        
        if sub == "叫貨":
            # ... (原本的叫貨邏輯保持不變) ...
            alert = df_inv[df_inv["目前庫存"].astype(int) <= df_inv["安全庫存"].astype(int)]
            if alert.empty:
                st.success("✅ 目前庫存水位安全！")
            else:
                st.markdown("### 🚨 待叫貨刀具")
                st.dataframe(alert[["品名規格", "刀具編號", "目前庫存", "安全庫存"]], hide_index=True)
                
                txt = "【CNC 刀具補貨需求】\n"
                for _, row in alert.iterrows():
                    need = int(row['安全庫存']) * 2 - int(row['目前庫存'])
                    need = max(need, 5)
                    txt += f"{row['品名規格']} (編號:{row['刀具編號']}) 需求: {need} 支\n"
                st.code(txt, language=None)
                st.success("👆 上方內容已幫你整理好，直接複製即可貼到 LINE")
        
        elif sub == "進貨":
            # ... (原本的進貨邏輯保持不變) ...
            t_in = st.selectbox("刀具", df_inv["品名規格"].tolist())
            q_in = st.number_input("數量", min_value=1, step=1)
            if st.button("確認進貨"):
                idx_in = df_inv[df_inv["品名規格"] == t_in].index[0]
                get_sh().worksheet("inventory").update_cell(idx_in+2, df_inv.columns.get_loc("目前庫存")+1, int(df_inv.loc[idx_in, "目前庫存"]) + q_in)
                get_sh().worksheet("logs").append_row([datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "進貨", df_inv.loc[idx_in,"刀具編號"], q_in, "管理", "補貨", "進貨", "無"])
                st.success("成功"); st.cache_data.clear(); st.rerun()
                
        elif sub == "建檔":
            # ... (原本的建檔邏輯保持不變) ...
            with st.form("f_new"):
                c, nid, nname, nloc = st.selectbox("分類", ["銑刀","圓鼻刀","球刀","粉末鑽頭","黑鑽","絲功","銑牙刀"]), st.text_input("編號"), st.text_input("品名"), st.text_input("儲位")
                nstock, nsafe = st.number_input("庫存", min_value=0), st.number_input("安全", min_value=0)
                if st.form_submit_button("確認"):
                    get_sh().worksheet("inventory").append_row([c, nid, nname, nloc, nstock, nsafe]); st.success("成功"); st.cache_data.clear(); st.rerun()
                    
        elif sub == "校正":
            # ... (原本的校正邏輯保持不變) ...
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
        
        if not df_log.empty:
            df_log["數量"] = pd.to_numeric(df_log["數量"], errors='coerce').fillna(0)
            df_usage = df_log[df_log["動作"] == "領用"].copy()
            
            # --- 圖表區 ---
            if not df_usage.empty:
                c1, c2, c3 = st.columns(3)
                with c1: 
                    st.markdown("**機台消耗排行**"); st.bar_chart(df_usage.groupby("備註")["數量"].sum())
                with c2: 
                    st.markdown("**人員領用統計**"); st.bar_chart(df_usage.groupby("經辦人員")["數量"].sum())
                with c3: 
                    st.markdown("**原因分析統計**"); st.bar_chart(df_usage.groupby("原因類型")["數量"].sum())

            st.markdown("---")
            st.header("📜 歷史紀錄進階篩選")
            
            # --- 進階篩選區 ---
            col_a, col_b, col_c = st.columns(3)
            
            # 1. 原因篩選
            all_reasons = ["正常磨損", "斷刀", "架機", "其他"]
            sel_reasons = col_a.multiselect("篩選原因:", all_reasons, default=[])
            
            # 2. 人員篩選
            all_staff = df_set["人員"].replace("", pd.NA).dropna().unique().tolist()
            sel_staff = col_b.multiselect("篩選人員:", all_staff, default=[])
            
            # 3. 機台篩選
            all_machines = df_set["機台"].replace("", pd.NA).dropna().tolist()
            sel_machines = col_c.multiselect("篩選機台:", all_machines, default=[])
            
            # 工單搜尋框
            search_wo = st.text_input("🔍 搜尋工單號碼 (選填):")
            
            # --- 綜合過濾邏輯 ---
            df_filtered = df_log.copy()
            
            # 多條件篩選
            if sel_reasons:
                df_filtered = df_filtered[df_filtered["原因類型"].astype(str).isin([str(s) for s in sel_reasons])]
            if sel_staff:
                df_filtered = df_filtered[df_filtered["經辦人員"].astype(str).isin([str(s) for s in sel_staff])]
            if sel_machines:
                df_filtered = df_filtered[df_filtered["備註"].astype(str).isin([str(s) for s in sel_machines])]
            
            # 工單搜尋 (關鍵：確保欄位存在且只有輸入時才過濾)
            if search_wo and search_wo.strip() != "":
                if "工單號碼" in df_filtered.columns:
                    df_filtered = df_filtered[df_filtered["工單號碼"].astype(str).str.contains(search_wo.strip(), case=False, na=False)]
                else:
                    st.error("系統未找到 '工單號碼' 欄位，請檢查 Google Sheet 表頭是否正確。")
            
            st.dataframe(df_filtered, use_container_width=True)
            
            # 報表匯出
            buf = io.BytesIO()
            with pd.ExcelWriter(buf) as w:
                df_log.to_excel(w, sheet_name='紀錄', index=False)
                df_inv.to_excel(w, sheet_name='庫存', index=False)
            st.download_button("📥 下載完整報表 (Excel)", buf.getvalue(), "CNC_Report.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
