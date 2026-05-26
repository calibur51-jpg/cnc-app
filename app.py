import streamlit as st
import pandas as pd
import gspread
from google.oauth2 import service_account

# --- 1. 設定區 ---
INV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTo2vi_36qF4mzPkxzNOJPTip7y-TXJLBm745noRRa4v_L_qkJ0DhFkaJ7tvYLCYWdFV3wbXOtH--zJ/pub?gid=0&single=true&output=csv"
LOG_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTo2vi_36qF4mzPkxzNOJPTip7y-TXJLBm745noRRa4v_L_qkJ0DhFkaJ7tvYLCYWdFV3wbXOtH--zJ/pub?gid=1320901506&single=true&output=csv"
SET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTo2vi_36qF4mzPkxzNOJPTip7y-TXJLBm745noRRa4v_L_qkJ0DhFkaJ7tvYLCYWdFV3wbXOtH--zJ/pub?gid=657176737&single=true&output=csv"

# --- 2. 讀取與認證函數 ---
def get_data():
    try:
        df_inv = pd.read_csv(INV_URL, encoding='utf-8-sig')
        df_log = pd.read_csv(LOG_URL, encoding='utf-8-sig')
        df_set = pd.read_csv(SET_URL, encoding='utf-8-sig')
        return df_inv, df_log, df_set
    except Exception as e:
        st.error(f"資料讀取失敗: {e}")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

def get_sh():
    import json
    # 直接建立一個原生字典，不要做任何 join 或 split
    # 這就是你從 Google 下載下來的原始 JSON 內容
    creds_dict = {
        "type": "service_account",
        "project_id": "cnc-system-497409",
        "private_key_id": "d3209413a7333a6627e7e82b1470c421887f1bcb",
        "private_key": "-----BEGIN PRIVATE KEY-----\nMIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQDBXszQ8ez3DvoD\n9jfe5mPEKVHwp03WULp2E5jmEfZNnpmoVnNdXm0TC6d4z9Zd2FKRRntvj7m1Bzw2\nxkJSkemb047TKp0B+jFDucJJzkTtNDAiaM77Xk44I4AjTkdQFYOgHjDs+hAMmzvS\n8J3LAcq4FLOnW3yv7Ig0J7biahdKaAa6x8o4RW6nQpz4H3owIgjxGcROobvsmMB\niOaLQmgfVToLlAQcCJ4+0gW+3jHJU1x/gTMmITPWUhG+9Kg0CNSTdr3v3qhk7T8Y\ntWaMB1nkXfAmFwL6xayZVVVbDa42d7T+WEGPNdj83xkG4HE/MEQ+un5A1ryvtazW\nVCp0Ni6JAgMBAAECggEAEqP2e0lpAhd04Tsj32ZG9YbUre3Y1mk1klKZDYurekfI\n0PYVfKmQuvJniGFDrUwASJ4aYdKhcKqkArU5uT803XdHSEKuPD2vsFNIwAfk89dR\nMQ34rvlkMav1ayHdhMIwLDgg2AVSlP6FZbQZh/NyJOzk9SP/+O8Eob921SxsNpk1\n6Pf3F7HzO8MPhwk6UTYaAWyT0Rlj6wwrEe6lZpZd7uwPQqmujV6GtKIcrs4+tguM\nsU2/JNRkt3Nl0BBcKaD+en6bNtk1PYflyzap0ta+mKQ3kEsKG2+ozCvUDmTrykij\nHLSY8Yia8z9Rg5SxqIZql+kF6FVEwxJnJzTotclYsQKBgQDm2eE9E6w0Bgimv2Fi\nvXWp33jQv7X2rdmWM0Sh5qKRXVIz2ezD3LBSIvffCsBmfkVQNAM5Gaa3ZKsPuwbc\nD7wMHBIEpony3DCQZA0R0KIgqZG290Tzh42M9ZBqCDcuvPCiks+mpATtwUSn2HfA\na0kJ/kcZ0Za8v3yfphei9IyFkQKBgQDWb6H4n/1yYPziU6N1raAW8H+9Qd74VIIl\nJxWekO4gLmwmZP8ZGf79ZO9jCde4tmF/Yxp6av5UzMfdgH1/ebfU5Eqs1olWhD+u\nOFGiND49SAkdKCFcKdbOgdpGZubsBg8wJiRfxa5sx/lp/3OD93FTRU21p93eLiSr\nkUsN+L+9eQKBgCUYT8RDvAEkExHQYPK/5P9mBIDuvWulJfinxliJugfHyiTA2PXk\nKYUZT2FM1fviQHsR0I7FW2/OwlolwIVuFdaQUCjlJfebgEZDfYImV1cOSHbxJuhH\nGOzUrN8M8OkWvUgydSGe65fU3ZZnB18pHjR34q74adNspbb1toid6VKxAoGBAI5d\nMtWTsnpbdcj06lLYYK6aINSPhO6tfHIaDrplUhK/f0HGT65kmeu1NVE1WajiPLyM\nGSopGo1GH3MpOSiGsMuAfStei3OK/ZQ3A8uCj8ezqYlX+T3s8RXNFBMlgi40n6TB\nzehfn7vM0APVeuWkQ/Ka0krGFgDJ9cKKBaBTA0lRAoGAZljN5SUQNMkT8p8bFcAL\nr1RGmbRgKm/yxfcMkW52R8bOBmShinliWkr+4/gHToXzF9N9qX6eou2UMIBANK2k\n83jrBGPKFby5Zv4y5uKX6/1HKHmmi3lWqCgHgzU37DRkoowldA26jBGZiXFx336H\ns+VRW8oMlI8KCtPbs86hoEY=\n-----END PRIVATE KEY-----",
        "client_email": "app-484@cnc-system-497409.iam.gserviceaccount.com",
        "client_id": "102780254846012931462",
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
        "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/app-484%40cnc-system-497409.iam.gserviceaccount.com",
        "universe_domain": "googleapis.com"
    }
    
    # 【關鍵】使用 gspread 的原生認證，它會自動處理編碼，不會被底層模組報錯
    return gspread.service_account_from_dict(creds_dict).open_by_key("1Y3XJLmzIH2y2l-XWkQfOzhEPBcxSyFFW3RvYpG6JZJ8")

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
