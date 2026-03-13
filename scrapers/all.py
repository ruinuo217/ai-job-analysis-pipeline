import pandas as pd
import os

def final_data_cleaning(row):
    """
    資料清洗大總管：處理職稱修正、薪資換算、年資校正
    """
    # --- 1. 處理「其他」職稱 (偵測關鍵字補回) ---
    if row['job_title'] == '其他':
        # 抓取原始職稱與描述，統一轉小寫比對
        content = (str(row['original_job_title']) + " " + str(row['raw_job_description'])).lower()
        if any(x in content for x in ['frontend', '前端', 'ios', 'android']): 
            row['job_title'] = '前端工程師'
        elif any(x in content for x in ['backend', '後端', 'golang', 'java', 'php']): 
            row['job_title'] = '後端工程師'
        elif any(x in content for x in ['data', '資料', 'python', 'sql']): 
            row['job_title'] = '資料工程師'
        elif any(x in content for x in ['full stack', '全端']): 
            row['job_title'] = '全端工程師'
        else: 
            row['job_title'] = '軟體工程師'

    # --- 2. 處理時薪轉月薪 (100 < 薪資 < 1000) ---
    # 加上 pd.notna 確保有值才做比較，避免 NaN 報錯
    if pd.notna(row['min_salary']) and 100 < row['min_salary'] < 1000:
        row['min_salary'] = int(row['min_salary'] * 176)
        # 如果 max 也是時薪就一起乘，如果是 0 就維持 0
        if pd.notna(row['max_salary']) and 100 < row['max_salary'] < 1000:
            row['max_salary'] = int(row['max_salary'] * 176)
        else:
            row['max_salary'] = row['min_salary']

    # --- 3. 處理年資亂碼 ( Yourator 的 99 年或負數) ---
    if pd.notna(row['experience_years']) and (row['experience_years'] >= 40 or row['experience_years'] < 0):
        row['experience_years'] = 0
        
    return row

# ==========================================
# 執行合併流程
# ==========================================

# 1. 定義要讀取的檔案清單
file_list = [
    'data/104_jobs.csv', 
    'data/518_job.csv', 
    'data/1111_jobs.csv', 
    'data/cake_jobs.csv', 
    'data/Yes123_job.csv', 
    'data/Yourator_job.csv'
]

dfs = []
for f in file_list:
    if os.path.exists(f):
        print(f"正在讀取: {f}...")
        dfs.append(pd.read_csv(f))
    else:
        print(f"[警告] 找不到檔案: {f}，跳過...")

if not dfs:
    print("[錯誤] 完全找不到任何 CSV 檔案，請檢查執行路徑！")
else:
    # 2. 直接上下合併
    df_all = pd.concat(dfs, ignore_index=True)
    print(f"原始資料筆數: {len(df_all)}")

    # 3. 執行「超淨化」清洗邏輯
    print("正在執行資料清洗 (職稱修正、薪資換算、年資校正)...")
    df_all = df_all.apply(final_data_cleaning, axis=1)

    # 4. 跨平台去重複處理
    # 邏輯：同一間公司且原始職稱完全一樣就視為重複
    before_drop = len(df_all)
    df_all.drop_duplicates(subset=['company_name', 'original_job_title'], keep='first', inplace=True)
    print(f"成功剔除重複職缺: {before_drop - len(df_all)} 筆")

    # 5. 輸出黃金訓練集
    df_all.to_csv('all_jobs_clean.csv', index=False, encoding='utf-8-sig')
    print("-" * 30)
    print(f"任務達成！共產出 {len(df_all)} 筆清洗後資料。")
    print("已儲存為: all_jobs_clean.csv")