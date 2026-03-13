import pandas as pd
from sqlalchemy import create_engine, text
from urllib.parse import quote_plus
import os
from dotenv import load_dotenv

# 載入 .env 檔案中的環境變數
load_dotenv()

# =========================================
# 1. 自動偵測路徑並讀取黃金資料
# =========================================
# 取得目前這個 py 檔案所在的資料夾路徑
base_dir = os.path.dirname(os.path.abspath(__file__))

# 組合出正確的 CSV 路徑：指向同層級的 data 資料夾
input_file = os.path.join(base_dir, "data", "all_jobs_perfect.csv")

print(f"正在讀取檔案: {input_file}...")

if not os.path.exists(input_file):
    raise FileNotFoundError(f"❌ 找不到檔案！請確認 {input_file} 是否存在。")

df = pd.read_csv(input_file, keep_default_na=False, encoding='utf-8-sig')
print(f"共讀取到 {len(df)} 筆資料。")

# =========================================
# 2. 安全設定遠端資料庫連線 (從 .env 讀取)
# =========================================
# 抓取隱藏的密碼與設定
db_host = os.getenv("DB_HOST")
db_port = os.getenv("DB_PORT", "3306")
db_user = os.getenv("DB_USER")
db_pass = os.getenv("DB_PASS")
db_name = os.getenv("DB_NAME")

# 防呆機制：確保 .env 有被正確讀取
if not db_pass:
    raise ValueError("❌ 找不到資料庫密碼！請確認你有建立 .env 檔案，並且裡面有設定 DB_PASS。")

password = quote_plus(db_pass)
db_url = f"mysql+pymysql://{db_user}:{password}@{db_host}:{db_port}/{db_name}"
engine = create_engine(db_url)
print("資料庫連線建立成功。")

print("--- 啟動 Append 匯入模式 ---")
try:
    with engine.begin() as conn:

        # =========================================
        # 步驟 A: 寫入 jobs 主表
        # =========================================
        print("\n[步驟 A] 正在將職缺寫入 jobs 表...")
        jobs_df = df.drop(columns=['skill_name', 'uid', 'job_id'], errors='ignore')
        jobs_df.to_sql('jobs', con=conn, if_exists='append', index=False, chunksize=1000)
        print(f"  ✅ 成功寫入 {len(jobs_df)} 筆職缺。")

        # =========================================
        # 步驟 B: 技能字典表 (INSERT IGNORE 避免 UNIQUE 衝突)
        # =========================================
        print("\n[步驟 B] 正在萃取技能並填入 skills 表...")
        all_skills = set()
        for skills_str in df['skill_name']:
            if skills_str:
                for skill in str(skills_str).split(','):
                    s = skill.strip()
                    if s:
                        all_skills.add(s)

        for skill in sorted(all_skills):
            conn.execute(
                text("INSERT IGNORE INTO skills (skill_name) VALUES (:skill_name)"),
                {"skill_name": skill}
            )
        print(f"  ✅ 成功處理 {len(all_skills)} 個技能。")

    # =========================================
    # 步驟 C: 建立 Mapping 關聯
    # (在 with block 外，確保 A/B 已 commit)
    # =========================================
    print("\n[步驟 C] 正在對照 ID 並建立關聯紀錄...")
    jobs_db = pd.read_sql(
        "SELECT job_id, source_platform, original_job_id FROM jobs",
        con=engine
    )
    skills_db = pd.read_sql(
        "SELECT skill_id, skill_name FROM skills",
        con=engine
    )

    # 製作 uid 對照表
    jobs_db['uid'] = jobs_db['source_platform'] + "_" + jobs_db['original_job_id'].astype(str)
    df['uid'] = df['source_platform'] + "_" + df['original_job_id'].astype(str)

    job_id_map = dict(zip(jobs_db['uid'], jobs_db['job_id']))
    skill_id_map = dict(zip(skills_db['skill_name'], skills_db['skill_id']))

    mapping_data = []
    for _, row in df.iterrows():
        j_id = job_id_map.get(row['uid'])
        if not j_id:
            continue
        skills_str = row['skill_name']
        if skills_str:
            for skill in str(skills_str).split(','):
                s_name = skill.strip()
                s_id = skill_id_map.get(s_name)
                if s_id:
                    mapping_data.append({'job_id': j_id, 'skill_id': s_id})

    mapping_df = pd.DataFrame(mapping_data)
    print(f"  共產生 {len(mapping_df)} 筆關聯紀錄。")

    with engine.begin() as conn:
        for _, mrow in mapping_df.iterrows():
            conn.execute(
                text("INSERT IGNORE INTO job_skills_mapping (job_id, skill_id) VALUES (:job_id, :skill_id)"),
                {"job_id": int(mrow['job_id']), "skill_id": int(mrow['skill_id'])}
            )
    print(f"  ✅ 成功寫入 {len(mapping_df)} 筆關聯。")

    # =========================================
    # 完成摘要
    # =========================================
    print("\n" + "=" * 40)
    print("🎉 任務完美達成！")
    print(f"  職缺 (jobs)          : {len(jobs_df)} 筆")
    print(f"  技能 (skills)        : {len(all_skills)} 個")
    print(f"  關聯 (mapping)       : {len(mapping_df)} 筆")
    print("=" * 40)

except Exception as e:
    print(f"\n❌ 匯入出錯了！原因: {e}")
    print("提示：若報 Duplicate entry，請先清空資料表再試：")
    print("  TRUNCATE TABLE job_skills_mapping;")
    print("  TRUNCATE TABLE jobs;")
    print("  TRUNCATE TABLE skills;")