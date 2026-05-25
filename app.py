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
with t1
