import pandas as pd
import numpy as np

# 1. 讀取你剛剛產出的 all_jobs_clean.csv
input_file = 'all_jobs_clean.csv'
df = pd.read_csv(input_file)
original_len = len(df)

print("--- [階段一] 原始資料健康檢查 ---")
print(f"初始總筆數: {original_len}")
print(f"各平台分布:\n{df['source_platform'].value_counts()}\n")

print("--- 發現的異常狀況 (準備清除) ---")
null_core_count = df[['job_title', 'company_name']].isnull().any(axis=1).sum()
print(f"核心欄位(職稱/公司)為空的筆數: {null_core_count} 筆")

weird_salary_df = df[(df['min_salary'] < 1000) & (df['min_salary'] > 0)]
print(f"薪資異常(低於1000)的筆數: {len(weird_salary_df)} 筆")

weird_exp_df = df[df['experience_years'] >= 40]
print(f"年資異常(大於等於40年)的筆數: {len(weird_exp_df)} 筆\n")


print("--- [階段二] 啟動強制淨化程序 ---")

# 動作 1: 刪除核心欄位為空的資料 (職稱、公司、平台、網址都不能是空的)
df = df.dropna(subset=['job_title', 'company_name', 'source_platform', 'job_url'])

# 動作 2: 刪除薪資異常低於 1000 的資料
df = df[df['min_salary'] >= 1000]

# 動作 3: 確保字串欄位的空值被填補 (讓 Pandas 的 NaN 變成真正的空字串，避免資料庫報錯)
df['skill_name'] = df['skill_name'].fillna("")
df['raw_job_description'] = df['raw_job_description'].fillna("無詳細描述")
df['original_job_id'] = df['original_job_id'].fillna("unknown_id")
df['original_job_title'] = df['original_job_title'].fillna(df['job_title']) 

# 動作 4: 雙重保險，把極端年資通通校正歸零 (視為不限經驗)
df.loc[df['experience_years'] >= 40, 'experience_years'] = 0

# 動作 5: 確保面議標記只有 0 跟 1
df['is_negotiable'] = df['is_negotiable'].apply(lambda x: 1 if x in [1, '1', True, 'true', 'True'] else 0)


final_len = len(df)
print(f"淨化完成！共切除 {original_len - final_len} 筆髒資料。")
print(f"最終完美筆數: {final_len} 筆\n")

print("--- [階段三] 最終欄位空值總體檢 (必須全部是 0) ---")
print(df.isnull().sum())

# 3. 另存完美新檔
output_file = 'all_jobs_perfect.csv'
df.to_csv(output_file, index=False, encoding='utf-8-sig')

print(f"\n乾淨資料已另存為: 【 {output_file} 】")