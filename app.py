import streamlit as st
import pandas as pd
import gspread
import os
from datetime import datetime
import io

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
st.title("CNC 刀具智慧管理系統 (終極旗艦版)")

# 低庫存標色邏輯
def c_low(row): 
    return ['background-color: #ffcccc; color: #800000; font-weight: bold;'] * len(row) if int(row['目前庫存']) <= int(row['安全庫存']) else [''] * len(row)

t1, t2, t3 = st.tabs(["現場領用", "⚙️ 管理員後台", "📜 歷史紀錄"])

# ==========================================
# TAB 1: 現場領用
# ==========================================
with t1:
    cats = ["全部"] + df_inv["分類"].unique().tolist()
    cat_sel = st.selectbox("請先選擇大分類", cats, key="cat_sel_t1")
    df_f = df_inv if cat_sel == "全部" else df_inv[df_inv["分類"] == cat_sel]
    
    tool_list = df_f["品名規格"].tolist()
    if not tool_list:
        st.warning("此分類下目前無刀具資料")
    else:
        t_name = st.selectbox("請選擇刀具名稱", tool_list, key="t_name_t1")
        idx = df_inv[df_inv["品名規格"] == t_name].index[0]
        t_sel = df_inv.loc[idx, "刀具編號"]
        
        current_stock_val = int(df_inv.loc[idx, "目前庫存"])
        st.info(f"📍 規格: {t_name} | 編號: {t_sel} | 儲位: {df_inv.loc[idx, '儲位']} | 目前庫存: {current_stock_val}")
        
        # 💡 初始化數量變數，確保它安全存在於後台
        if "qty_counter" not in st.session_state:
            st.session_state["qty_counter"] = 1
            
        # 顯示數量輸入框，綁定我們的獨立計數器
        qty = st.number_input("數量", min_value=1, step=1, value=st.session_state["qty_counter"], key="qty_display_box")
        st.session_state["qty_counter"] = qty

        c1, c2 = st.columns(2)
        with c1: 
            # 💡 按鈕按下時，直接對變數加 1 並且立刻觸發 rerun 刷新畫面數字
            if st.button("➕ 領用數量 +1", key="real_btn_add"):
                st.session_state["qty_counter"] += 1
                st.rerun()
        with c2: 
            # 💡 按鈕按下時，直接強制將數值歸回 1 並且立刻觸發 rerun
            if st.button("🔄 數量歸零 (回1)", key="real_btn_reset"):
                st.session_state["qty_counter"] = 1
                st.rerun()
        
        u = st.selectbox("人員", ["小翔", "阿玄", "少宏", "阿晴", "阿偉", "阿福", "阿鬼"], key="uk1")
        cnc_machines = [f"CNC-{i:02d}" for i in range(1, 12)] + ["廠內備庫"]
        m = st.selectbox("機台", cnc_machines, key="mk1")
        r = st.selectbox("原因", ["正常磨損", "異常崩刃", "調機", "其他"], key="rk1")
        wo = st.text_input("工單號碼 (選填)", key="wo_t1").strip()
        
        if st.button("確認領用", type="primary", key="submit_t1"):
            if st.session_state["qty_counter"] > current_stock_val: 
                st.error("❌ 庫存不足！無法領取")
            else:
                new_stock = current_stock_val - st.session_state["qty_counter"]
                col_num = df_inv.columns.get_loc("目前庫存") + 1
                sh.worksheet("inventory").update_cell(idx + 2, col_num, new_stock)
                
                log_data = [datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "領用", t_sel, st.session_state["qty_counter"], u, m, r, wo if wo else "無"]
                sh.worksheet("logs").append_row(log_data)
                
                # 領用成功後，重設回 1
                st.session_state["qty_counter"] = 1
                st.success("✅ 領用成功！")
                st.rerun()

# ==========================================
# TAB 2: 管理員後台
# ==========================================
with t2:
    if st.text_input("輸入管理密碼", type="password", key="admin_pw") == "1234":
        sub = st.radio("功能選擇", ["庫存總覽與叫貨", "進貨入庫", "全新建檔", "修改與校正庫存"], horizontal=True)
        
        if sub == "庫存總覽與叫貨":
            st.markdown("### 🚨 庫存告急專區 (低於或等於安全庫存)")
            df_alert = df_inv[df_inv["目前庫存"].astype(int) <= df_inv["安全庫存"].astype(int)]
            
            if df_alert.empty:
                st.success("✅ 目前所有刀具水位安全，沒有缺貨！")
            else:
                st.dataframe(df_alert.style.apply(c_low, axis=1), hide_index=True, use_container_width=True)
                
                date_str = datetime.now().strftime('%m/%d')
                line_text = f"【CNC 刀具補貨通知 - {date_str}】\n親愛的廠商您好，我們需要增補以下刀具：\n"
                for _, row in df_alert.iterrows():
                    shortage = int(row['安全庫存']) * 2 - int(row['開目前庫存' if '開目前庫存' in df_inv.columns else '目前庫存'])
                    if shortage <= 0: shortage = 5
                    line_text += f"▪️ {row['品名規格']} (編號:{row['刀具編號']}) * 需求數量: {shortage} 支\n"
                line_text += "再麻煩您安排出庫，謝謝！"
                
                st.text_area("📋 LINE 叫貨文字 (直接複製即可貼到 LINE)", value=line_text, height=180, key="line_text_box")
            
            st.write("---")
            st.markdown("### 🔍 庫存分類總覽與搜尋")
            
            cats_view = ["全部"] + df_inv["分類"].unique().tolist()
            cat_sel_view = st.selectbox("選擇要查看的分類", cats_view, key="cat_view_tab2")
            df_view = df_inv if cat_sel_view == "全部" else df_inv[df_inv["分類"] == cat_sel_view]
            
            search_k = st.text_input("輸入關鍵字 (如品名/規格) 快速搜尋：", key="search_box_t2").strip()
            if search_k:
                df_view = df_view[df_view["品名規格"].str.contains(search_k, case=False) | df_view["刀具編號"].str.contains(search_k, case=False)]
            st.dataframe(df_view.style.apply(c_low, axis=1), hide_index=True, use_container_width=True)

        elif sub == "進貨入庫":
            st.markdown("### 📦 進貨入庫")
            t_in_name = st.selectbox("選擇進貨刀具品名", df_inv["品名規格"].tolist(), key="t_in_selectbox")
            idx_in = df_inv[df_inv["品名規格"] == t_in_name].index[0]
            q_in = st.number_input("進貨數量", min_value=1, step=1, key="q_in_input")
            
            if st.button("確認進貨", key="btn_confirm_in"):
                target_col = df_inv.columns.get_loc("目前庫存") + 1
                new_stock = int(df_inv.loc[idx_in, "目前庫存"]) + q_in
                sh.worksheet("inventory").update_cell(idx_in + 2, target_col, new_stock)
                
                in_log = [datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "進貨", df_inv.loc[idx_in, "刀具編號"], q_in, "管理員", "補貨", "進貨", "無"]
                sh.worksheet("logs").append_row(in_log)
                
                st.success(f"✅ 已成功為 {t_in_name} 補入 {q_in} 個！")
                st.rerun()

        elif sub == "全新建檔":
            st.markdown("### 🆕 全新建檔")
            with st.form("new_tool_form"):
                ncat = st.selectbox("分類", ["銑刀", "圓鼻刀", "球刀", "粉末鑽頭", "黑鑽", "絲功", "銑牙刀"])
                nid = st.text_input("新刀具編號 (例如: EM-005)")
                nname = st.text_input("品名規格 (例如: 鎢鋼平底銑刀 D10)")
                nloc = st.text_input("儲位 (例如: A架-01)")
                nstock = st.number_input("初始庫存", min_value=0, step
