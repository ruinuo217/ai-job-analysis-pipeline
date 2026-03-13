import pandas as pd
import os


def final_data_cleaning(row):
    
    # --- 1. 處理「其他」職稱 ---
    if row['job_title'] in ('其他', '工程師', '軟體工程師'):

        title = str(row['original_job_title']).lower()
        desc  = str(row['raw_job_description']).lower()

        # ══ 第一層：非技術職直接歸類，return 不往下跑 ══
        NON_TECH_MAP = {
            '行銷': '行銷/業務',     'marketing': '行銷/業務',
            '業務': '行銷/業務',     'sales': '行銷/業務',
            '行政': '行政/管理',     'admin': '行政/管理',
            '助理': '行政/管理',     'assistant': '行政/管理',
            '專員': '行政/管理',
            '會計': '財務/會計',     'accounting': '財務/會計',
            '財務': '財務/會計',
            '人資': '人資/招募',     'hr': '人資/招募',
            'recruit': '人資/招募',
            '設計師': 'UI/UX設計師', 'designer': 'UI/UX設計師',
            '產品經理': '產品經理',  'product manager': '產品經理',
            'intern': '實習生',      '實習': '實習生',
            '習生': '實習生',
        }
        for keyword, category in NON_TECH_MAP.items():
            if keyword in title:
                row['job_title'] = category
                return row

        # ══ 第二層：從 original_job_title 直接命中具體技術職 ══
        TITLE_MAP = {
            # 語言/框架 → 後端
            'c#': '後端工程師',    'java': '後端工程師',
            'python': '後端工程師','golang': '後端工程師',
            'ruby': '後端工程師',  'php': '後端工程師',
            '.net': '後端工程師',  'node': '後端工程師',
            'spring': '後端工程師','django': '後端工程師',
            # 前端
            'vue': '前端工程師',   'react': '前端工程師',
            'angular': '前端工程師','javascript': '前端工程師',
            'typescript': '前端工程師',
            # APP
            'ios': 'APP工程師',    'android': 'APP工程師',
            'flutter': 'APP工程師','swift': 'APP工程師',
            'kotlin': 'APP工程師',
            # 自動化/PLC
            'plc': '自動化工程師', '自動化': '自動化工程師',
            'scada': '自動化工程師','hmi': '自動化工程師',
            # AI/資料
            'ai工程': 'AI工程師',  'ml': 'AI工程師',
            'data': '資料工程師',  '資料': '資料工程師',
            # 韌體
            '韌體': '韌體工程師',  'firmware': '韌體工程師',
            '嵌入式': '韌體工程師','embedded': '韌體工程師',
            # 測試
            'test': 'QA/品管工程師','測試': 'QA/品管工程師',
            'qa': 'QA/品管工程師', 'qc': 'QA/品管工程師',
            # 資安
            '資安': '資安工程師',  'security': '資安工程師',
            # MIS/IT
            'mis': 'MIS/IT工程師', 'helpdesk': 'MIS/IT工程師',
            'it支援': 'MIS/IT工程師',
            # 非軟體工程師
            '機械': '機械工程師',  '機構': '機械工程師',
            '電機': '電機工程師',  '電力': '電機工程師',
            '電子': '電子工程師',  'pcb': '電子工程師',
            '化工': '製程/化工工程師','製程': '製程/化工工程師',
            '土木': '土木工程師',  '結構': '土木工程師',
            'ic設計': 'IC設計工程師','vlsi': 'IC設計工程師',
        }
        for keyword, category in TITLE_MAP.items():
            if keyword in title:
                row['job_title'] = category
                return row

        # ══ 第三層：title 比不到，改用 desc 關鍵字雷達 ══
        def match(desc_kws):
            return any(k in desc for k in desc_kws)

        if match(['machine learning', '機器學習', 'deep learning', 'llm', 'mlops']):
            row['job_title'] = 'AI工程師'
        elif match(['資料管線', 'etl', 'data pipeline', '爬蟲', 'data engineer']):
            row['job_title'] = '資料工程師'
        elif match(['kubernetes', 'terraform', 'ci/cd', 'devops', 'aws', 'gcp', 'azure']):
            row['job_title'] = '雲端/DevOps工程師'
        elif match(['後端開發', 'spring boot', 'django', 'fastapi', 'node.js']):
            row['job_title'] = '後端工程師'
        elif match(['前端開發', 'vue', 'react', 'angular', 'typescript', 'css']):
            row['job_title'] = '前端工程師'
        elif match(['ios', 'android', 'flutter', 'swift', 'kotlin', 'react native']):
            row['job_title'] = 'APP工程師'
        elif match(['full stack', '全端開發']):
            row['job_title'] = '全端工程師'
        elif match(['韌體', 'rtos', 'bsp', 'linux kernel', '嵌入式']):
            row['job_title'] = '韌體工程師'
        elif match(['資訊安全', '滲透測試', 'vulnerability', 'siem']):
            row['job_title'] = '資安工程師'
        elif match(['網路架構', 'routing', 'switching', 'firewall', 'ccna']):
            row['job_title'] = '網路工程師'
        elif match(['系統維運', '系統管理', 'windows server', 'linux admin']):
            row['job_title'] = '系統工程師'
        elif match(['品質管理', '測試規劃', 'test plan', 'test case']):
            row['job_title'] = 'QA/品管工程師'
        elif match(['機械設計', '機構設計', '製造工程', 'autocad']):
            row['job_title'] = '機械工程師'
        elif match(['電子電路', 'pcb設計', 'fpga', 'verilog']):
            row['job_title'] = '電子工程師'
        elif match(['plc', 'scada', '自動化控制']):
            row['job_title'] = '自動化工程師'
        else:
            # ══ 最終 Fallback ══
            is_sw = any(k in desc for k in [
                'software', '軟體開發', '程式', 'coding',
                'python', 'java', 'git', 'api', '開發', 'c#', '.net', 'sql'
            ])
            if not is_sw and '工程師' in str(row['original_job_title']):
                is_sw = True
            row['job_title'] = '軟體工程師' if is_sw else '其他職類'


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
    '104_final.csv', '518_final.csv', '1111_final.csv', 
    'cake_final.csv', 'Yes123_final.csv', 'Yourator_final.csv'
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