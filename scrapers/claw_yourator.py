import requests
import pandas as pd
import re
import time
import os
from bs4 import BeautifulSoup

# =====================================================
# ⚙️ 設定區
# =====================================================
MAX_PAGES   = 100    # 100頁 ≈ 2000筆
OUTPUT_FILE = "Yourator_Standard.csv"
BASE_URL    = "https://www.yourator.co"
API_URL     = "https://www.yourator.co/api/v4/jobs"
KEYWORDS = [
    '工程師', '軟體工程師', '韌體工程師', '前端工程師',
    '後端工程師', '資料工程師', 'DevOps', 'AI工程師', '全端工程師',
]
DELAY       = 1.5   # 每筆詳細頁間隔秒數

# =====================================================
# 📚 技術白名單（與 Yes123 / 518 一致）
# =====================================================
tech_mapping = {
    # === 軟體與資料庫 ===
    "Python":       ["python", "python3"],
    "Java":         ["java"],
    "C++":          ["c++", "cpp"],
    "C#":           ["c#", "csharp", "c#.net"],
    "JavaScript":   ["javascript", "js", "java script"],
    "TypeScript":   ["typescript", "ts"],
    "Golang":       ["go", "golang"],
    "Ruby":         ["ruby", "ruby on rails"],
    "Rust":         ["rust"],
    "PHP":          ["php", "laravel"],
    "SQL":          ["sql", "ms sql", "ms sql server", "sql server"],
    "MySQL":        ["mysql"],
    "PostgreSQL":   ["postgresql", "postgres"],
    "NoSQL":        ["nosql", "mongodb", "redis"],

    # === 前端、手機 App 與介面設計 ===
    "React":        ["react", "react.js", "reactjs", "react native"],
    "Vue":          ["vue", "vue.js", "vuejs"],
    "Next.js":      ["next.js", "nextjs"],
    "Node.js":      ["node.js", "nodejs", "node"],
    "HTML":         ["html", "html5"],
    "CSS":          ["css", "css3", "tailwind", "sass"],
    "Swift":        ["swift", "ios"],
    "Kotlin":       ["kotlin", "android"],
    "Flutter":      ["flutter"],
    "UI/UX設計":    ["ui/ux", "ui", "ux", "figma", "sketch", "使用者體驗"],
    "SEO":          ["seo", "搜尋引擎優化"],

    # === 雲端、DevOps 與系統 ===
    "AWS":          ["aws", "amazon web services"],
    "GCP":          ["gcp", "google cloud platform"],
    "Azure":        ["azure"],
    "Docker":       ["docker"],
    "Kubernetes":   ["kubernetes", "k8s"],
    "Git":          ["git", "github", "gitlab"],
    "Linux":        ["linux", "ubuntu", "centos"],
    "Windows Server": ["windows server"],
    "TCP/IP":       ["tcp/ip", "tcp"],
    "CI/CD":        ["ci/cd", "cicd", "jenkins"],

    # === AI、資料科學與分析 ===
    "R語言":        ["r", "r language", "r語言"],
    "Tableau":      ["tableau"],
    "Power BI":     ["power bi", "powerbi"],
    "Excel":        ["excel"],
    "Hadoop":       ["hadoop"],
    "Spark":        ["spark", "apache spark"],
    "Pandas":       ["pandas", "numpy"],
    "PyTorch":      ["pytorch"],
    "TensorFlow":   ["tensorflow", "tf"],
    "OpenAI API":   ["openai", "llm", "chatgpt"],

    # === 硬體、韌體與機構 ===
    "AutoCAD":      ["autocad", "cad"],
    "SolidWorks":   ["solidworks", "solid works"],
    "Pro/E":        ["pro/e", "proe", "creo"],
    "PLC":          ["plc"],
    "Verilog":      ["verilog"],
    "VHDL":         ["vhdl"],
    "FPGA":         ["fpga"],
    "PCB":          ["pcb", "layout"],
    "Altium":       ["altium", "altium designer", "ad"],
    "OrCAD":        ["orcad"],
    "PADS":         ["pads"],
    "MCU":          ["mcu"],
    "ARM":          ["arm"],
    "BIOS":         ["bios"],
    "C語言":        ["c", "c language", "c語言"],
    "RTOS":         ["rtos", "freertos"],
    "MATLAB":       ["matlab"],
    "LabVIEW":      ["labview"],

    # === 品保、製造與專案管理 ===
    "ISO 9001":     ["iso 9001", "iso9001", "iso-9001"],
    "ISO 14001":    ["iso 14001", "iso14001"],
    "Six Sigma":    ["six sigma", "6 sigma", "6-sigma", "六標準差"],
    "FMEA":         ["fmea"],
    "SPC":          ["spc"],
    "APQP":         ["apqp"],
    "PPAP":         ["ppap"],
    "MES":          ["mes"],
    "ERP":          ["erp", "sap"],
    "Jira":         ["jira"],
    "Scrum":        ["scrum"],
    "Agile":        ["agile", "敏捷開發"],
    "QA":           ["qa", "quality assurance"],
    "QC":           ["qc", "quality control"],
}

def extract_skills(text):
    found_skills = []
    text_lower = text.lower()
    for std_name, aliases in tech_mapping.items():
        for alias in aliases:
            a = alias.lower()
            if re.search(r'[\u4e00-\u9fff]', a):
                pattern = re.escape(a)
            else:
                pattern = (r'(?:^|(?<=[\s\W\u4e00-\u9fff]))'
                           + re.escape(a)
                           + r'(?=[\s\W\u4e00-\u9fff]|$)')
            if re.search(pattern, text_lower):
                found_skills.append(std_name)
                break
    return ",".join(sorted(list(set(found_skills))))

def normalize_job_title(title):
    t = title.lower()
    if any(k in t for k in ["前端", "frontend", "front-end", "react", "vue", "ui工程"]):
        return "前端工程師"
    if any(k in t for k in ["後端", "backend", "back-end", "server", "api"]):
        return "後端工程師"
    if any(k in t for k in ["全端", "fullstack", "full-stack", "full stack"]):
        return "全端工程師"
    if any(k in t for k in ["資料", "data", "機器學習", "ml", "ai", "分析師"]):
        return "資料科學家"
    if any(k in t for k in ["韌體", "firmware", "嵌入式", "embedded", "fpga", "mcu"]):
        return "韌體工程師"
    if any(k in t for k in ["硬體", "hardware", "pcb", "電路", "circuit"]):
        return "硬體工程師"
    if any(k in t for k in ["app", "ios", "android", "mobile", "flutter", "swift", "kotlin"]):
        return "App工程師"
    if any(k in t for k in ["devops", "sre", "雲端", "cloud", "infra"]):
        return "DevOps工程師"
    if any(k in t for k in ["qa", "qc", "測試", "test"]):
        return "QA工程師"
    if any(k in t for k in ["機構", "cad", "solidworks", "設計工程"]):
        return "機構工程師"
    return "工程師"

def parse_salary(sal_text):
    """
    Yourator 薪資格式：
    - NT$ 50,000 - 75,000 (月薪)
    - NT$ 70,000 -  (月薪)    ← 只有下限
    - 面議（經常性薪資達4萬元）
    """
    if not sal_text:
        return 40000, 40000, 1

    sal_clean = sal_text.strip()

    if "面議" in sal_clean:
        return 40000, 40000, 1

    is_annual = "年薪" in sal_clean

    nums = []
    for n in re.findall(r'[\d,]+', sal_clean):
        try:
            val = int(n.replace(',', ''))
            if val >= 1000:
                nums.append(val)
        except ValueError:
            continue

    if not nums:
        return 40000, 40000, 1

    min_s = nums[0]
    if len(nums) >= 2:
        max_s = nums[1]
    else:
        # 只有下限（如 NT$ 70,000 - ）
        max_s = int(min_s * 1.2)

    if is_annual:
        min_s = int(min_s / 12)
        max_s = int(max_s / 12)

    return min_s, max_s, 0

def parse_experience(text):
    """從條件要求文字中抽取工作經驗年數，不拘回傳 0"""
    if not text:
        return 0
    # 「工作經驗  2年以上」「經驗：3年」「1~3年」
    m = re.search(r'工作經驗[^0-9]*(\d+)', text)
    if m:
        return int(m.group(1))
    m = re.search(r'(\d+)\s*[~～至\-]\s*\d+\s*年', text)
    if m:
        return int(m.group(1))
    m = re.search(r'(\d+)\s*年以上', text)
    if m:
        return int(m.group(1))
    if any(k in text for k in ["不拘", "不限", "應屆"]):
        return 0
    return 0

# =====================================================
# HTTP Session
# =====================================================
session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.8",
    "Referer": "https://www.yourator.co/",
})

# =====================================================
# 載入已抓的 job_id（斷點續跑）
# =====================================================
done_ids = set()
if os.path.exists(OUTPUT_FILE):
    try:
        df_exist = pd.read_csv(OUTPUT_FILE)
        done_ids = set(df_exist["original_job_id"].astype(str).tolist())
        print(f"✅ 已有 {len(done_ids)} 筆，斷點續跑")
    except Exception:
        pass

all_rows = []

# =====================================================
# 主迴圈：列表頁 API
# =====================================================
for keyword in KEYWORDS:
    print(f"\n🔑 關鍵字：{keyword}")
    for page in range(1, MAX_PAGES + 1):
        params = {
            "page": page,
            "sort": "most_related",
            "term[]": keyword,
        }
        try:
            resp = session.get(API_URL, params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            print(f"❌ 列表頁 {page} 失敗：{e}")
            break

        payload = data.get("payload", {})
        jobs = payload.get("jobs", [])
        has_more = payload.get("hasMore", False)

        print(f"📄 [{keyword}] 第 {page} 頁，共 {len(jobs)} 筆")

        if not jobs:
            print("沒有更多職缺，跳下個關鍵字")
            break

        page_rows = []

        for job in jobs:
            job_id   = str(job.get("id", ""))
            job_name = job.get("name", "").strip()
            path     = job.get("path", "")
            salary   = job.get("salary", "")
            tags     = job.get("tags", [])
            company  = job.get("company", {})
            company_name = company.get("brand", "").strip()
            job_url  = BASE_URL + path

            if job_id in done_ids:
                print(f"  ⏭️  跳過 {job_id}")
                continue

            min_s, max_s, is_neg = parse_salary(salary)

            job_title = next((t for t in tags if "工程師" in t), None)
            if not job_title:
                job_title = normalize_job_title(job_name)

            raw_desc   = ""
            experience = 0
            try:
                det_resp = session.get(job_url, timeout=15,
                                       headers={"Accept": "text/html,application/xhtml+xml"})
                det_resp.raise_for_status()
                soup = BeautifulSoup(det_resp.text, "html.parser")

                headings = soup.find_all("h2", class_=lambda c: c and "job-heading" in c)
                for h2 in headings:
                    label = h2.get_text(strip=True)
                    section = h2.find_next_sibling("section", class_=lambda c: c and "content__area" in c)
                    if not section:
                        continue
                    text = section.get_text(separator="\n", strip=True)
                    if label == "工作內容":
                        raw_desc = text
                    elif label == "條件要求":
                        experience = parse_experience(text)

            except Exception as e:
                print(f"  ⚠️  詳細頁失敗 {job_id}：{e}")

            # ── 過濾非工程師職缺 ──
            ENGINEER_KEYWORDS = [
                "工程師", "engineer", "developer", "開發", "韌體", "firmware",
                "embedded", "devops", "sre", "architect", "架構", "程式",
            ]
            name_lower = job_name.lower()
            tags_lower = " ".join(tags).lower()
            if not any(k in name_lower or k in tags_lower for k in ENGINEER_KEYWORDS):
                done_ids.add(job_id)
                print(f"  ⛔ 跳過非工程師：{job_name}")
                continue

            skill_text = job_name + " " + raw_desc
            skill_name = extract_skills(skill_text)

            row = {
                "source_platform":    "Yourator",
                "original_job_id":    job_id,
                "job_title":          job_title,
                "original_job_title": job_name,
                "company_name":       company_name,
                "min_salary":         min_s,
                "max_salary":         max_s,
                "is_negotiable":      is_neg,
                "experience_years":   experience,
                "job_url":            job_url,
                "skill_name":         skill_name,
                "raw_job_description": raw_desc,
            }
            page_rows.append(row)
            done_ids.add(job_id)
            print(f"  ✅ {job_id} | {company_name} | {job_name} | {min_s}~{max_s} | exp={experience}")
            time.sleep(DELAY)

        if page_rows:
            all_rows.extend(page_rows)
            df_new = pd.DataFrame(page_rows)
            if os.path.exists(OUTPUT_FILE):
                df_new.to_csv(OUTPUT_FILE, mode="a", header=False, index=False, encoding="utf-8-sig")
            else:
                df_new.to_csv(OUTPUT_FILE, index=False, encoding="utf-8-sig")
            print(f"  💾 已存 {len(page_rows)} 筆")

        if not has_more:
            print(f"🏁 [{keyword}] 沒有更多頁面")
            break

        time.sleep(1)

# 最終統計
if os.path.exists(OUTPUT_FILE):
    df_final = pd.read_csv(OUTPUT_FILE)
    print(f"\n🎉 完成！共 {len(df_final)} 筆 → {OUTPUT_FILE}")