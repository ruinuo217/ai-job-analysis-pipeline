from playwright.sync_api import sync_playwright
import random
import pandas as pd
import re
import os
import time
from urllib.parse import quote

# 你定義的技術地圖
# 建立「標準名稱 : [各種別名/縮寫]」的映射字典
tech_mapping = {
    # === 軟體與資料庫 (擴充現代網頁與後端) ===
    "Python": ["python", "python3"],
    "Java": ["java"],
    "C++": ["c++", "cpp"],
    "C#": ["c#", "csharp", "c#.net"],
    "JavaScript": ["javascript", "js", "java script"],
    "TypeScript": ["typescript", "ts"],
    "Golang": ["go", "golang"],                  # 新增 Backend
    "Ruby": ["ruby", "ruby on rails"],           # 新增 Backend
    "Rust": ["rust"],                            # 新增 Backend
    "PHP": ["php", "laravel"],                   # 擴充 PHP 框架
    "SQL": ["sql"],
    "MySQL": ["mysql"],
    "PostgreSQL": ["postgresql", "postgres"],
    "NoSQL": ["nosql", "mongodb", "redis"],

    # === 前端網頁、手機 App 與介面設計 (擴充) ===
    "React": ["react", "react.js", "reactjs", "react native"],
    "Vue": ["vue", "vue.js", "vuejs"],
    "Next.js": ["next.js", "nextjs"],            # 新增現代前端框架
    "Node.js": ["node.js", "nodejs", "node"],
    "HTML": ["html", "html5"],
    "CSS": ["css", "css3", "tailwind", "sass"],  # 擴充前端切版技術
    "Swift": ["swift", "ios"],                   # 新增 App 開發
    "Kotlin": ["kotlin", "android"],             # 新增 App 開發
    "Flutter": ["flutter"],                      # 新增 App 開發
    "UI/UX設計": ["ui/ux", "ui", "ux", "figma", "sketch", "使用者體驗"],  # 新增介面與體驗設計
    "SEO": ["seo", "搜尋引擎優化"],                # 新增網站優化技能

    # === 雲端、DevOps 與系統 ===
    "AWS": ["aws", "amazon web services"],
    "GCP": ["gcp", "google cloud platform"],
    "Azure": ["azure"],
    "Docker": ["docker"],
    "Kubernetes": ["kubernetes", "k8s"],
    "Git": ["git", "github", "gitlab"],
    "Linux": ["linux", "ubuntu", "centos"],
    "Windows Server": ["windows server"],
    "TCP/IP": ["tcp/ip", "tcp"],
    "CI/CD": ["ci/cd", "cicd", "jenkins"],       # 新增自動化部署

    # === AI、資料科學與分析 (大擴充) ===
    "R語言": ["r", "r language", "r語言"],
    "Tableau": ["tableau"],
    "Power BI": ["power bi", "powerbi"],
    "Excel": ["excel"],
    "Hadoop": ["hadoop"],
    "Spark": ["spark", "apache spark"],
    "Pandas": ["pandas", "numpy"],               # 新增 Python 資料清洗套件
    "PyTorch": ["pytorch"],                      # 新增 AI 深度學習
    "TensorFlow": ["tensorflow", "tf"],          # 新增 AI 深度學習
    "OpenAI API": ["openai", "llm", "chatgpt"],  # 新增最夯的 AI 應用串接

    # === 硬體、韌體與機構 ===
    "AutoCAD": ["autocad", "cad"],
    "SolidWorks": ["solidworks", "solid works"],
    "Pro/E": ["pro/e", "proe", "creo"],
    "PLC": ["plc"],
    "Verilog": ["verilog"],
    "VHDL": ["vhdl"],
    "FPGA": ["fpga"],
    "PCB": ["pcb", "layout"],
    "Altium": ["altium", "altium designer", "ad"],
    "OrCAD": ["orcad"],
    "PADS": ["pads"],
    "MCU": ["mcu"],
    "ARM": ["arm"],
    "BIOS": ["bios"],
    "C語言": ["c", "c language", "c語言"],
    "RTOS": ["rtos", "freertos"],
    "MATLAB": ["matlab"],
    "LabVIEW": ["labview"],

    # === 品保、製造與專案管理 ===
    "ISO 9001": ["iso 9001", "iso9001", "iso-9001"],
    "ISO 14001": ["iso 14001", "iso14001"],
    "Six Sigma": ["six sigma", "6 sigma", "6-sigma", "六標準差"],
    "FMEA": ["fmea"],
    "SPC": ["spc"],
    "APQP": ["apqp"],
    "PPAP": ["ppap"],
    "MES": ["mes"],
    "ERP": ["erp", "sap"],
    "Jira": ["jira"],
    "Scrum": ["scrum"],
    "Agile": ["agile", "敏捷開發"],
    "QA": ["qa", "quality assurance"],
    "QC": ["qc", "quality control"]
}

USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/128.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/127.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_0) AppleWebKit/537.36 Chrome/126.0 Safari/537.36"
]

KEYWORDS = [
    "工程師",
    "軟體工程師",
    "後端工程師",
    "前端工程師",
    "資料工程師",
    "AI工程師",
    "DevOps工程師",
    "Python工程師",
    "Java工程師",
    "App工程師",
    "程式設計師",
    "網站工程師",
    "系統工程師",  # 2460
    # Engineer
    "Software Engineer",
    "Backend Engineer",
    "Frontend Engineer",
    "Data Engineer",
    "Machine Learning Engineer",
    "AI Engineer",
    "DevOps Engineer",
    # Developer
    "Software Developer",
    "Backend Developer",
    "Frontend Developer",
    "Full Stack Developer",
    # # Remote
    # "Remote Software Engineer",
    # "Remote Backend Engineer",
    # "Remote Frontend Engineer",
    # "Remote Data Engineer",
    # "Remote Machine Learning Engineer",
    # "Remote AI Engineer",
    # "Remote DevOps Engineer"
]


def collect_job_links(page, keyword, target_count):

    links = set()
    page_num = 1
    empty_pages = 0

    while len(links) < target_count:

        url = f"https://www.cake.me/jobs?q={quote(keyword)}&page={page_num}"

        print(f"📄 [{keyword}] 抓列表頁 {page_num}")

        # retry 3 次
        for attempt in range(3):
            try:
                page.goto(
                    url,
                    wait_until="domcontentloaded",
                    timeout=60000
                )
                break
            except:
                print("⚠️ Page load timeout，重試")
                time.sleep(3)

                if attempt == 2:
                    print("❌ 跳過此頁")
                    page_num += 1
                    continue

        page.mouse.wheel(0, 2000)

        try:
            page.wait_for_selector(
                'a[data-algolia-event-name="click_job"]',
                timeout=20000
            )
        except:
            print("⚠️ 沒抓到職缺元素")
            empty_pages += 1

            if empty_pages >= 2:
                print("🛑 已經沒有更多職缺頁")
                break

            page_num += 1
            continue

        job_elements = page.query_selector_all(
            'a[data-algolia-event-name="click_job"]'
        )

        if not job_elements:
            print("⚠️ 沒有新職缺")

            empty_pages += 1
            if empty_pages >= 2:
                print("🛑 已經沒有更多職缺頁")
                break

            page_num += 1
            continue

        empty_pages = 0

        new_links = [
            a.get_attribute("href")
            for a in job_elements
            if a.get_attribute("href")
        ]

        links.update(new_links)

        print("目前累積:", len(links))

        page_num += 1

        time.sleep(random.uniform(1.5, 3))

    return list(links)


def scrape_job_page(context, link):

    page = context.new_page()

    try:

        full_url = f"https://www.cake.me{link}"

        page.goto(full_url, wait_until="domcontentloaded")

        title_el = page.query_selector("h1")
        title = title_el.inner_text() if title_el else "N/A"

        job_title_elements = page.query_selector_all(
            'span[class*="labelText"]')

        if len(job_title_elements) > 0:
            job_title = job_title_elements[-1].inner_text()
        else:
            job_title = "N/A"

        company_el = page.query_selector('[class*="companyName"]')
        company = company_el.inner_text() if company_el else "N/A"

        salary_icon = page.locator("i.fa-dollar-sign")

        salary_raw = ""

        if salary_icon.count() > 0:
            try:
                salary_raw = salary_icon.locator(
                    "xpath=ancestor::div[contains(@class,'row')]//span"
                ).inner_text()
            except:
                salary_raw = ""

        experience_years = 0

        exp_icon = page.locator("i.fa-business-time")

        if exp_icon.count() > 0:

            exp_text = exp_icon.locator(
                "xpath=ancestor::div[contains(@class,'row')]//span"
            ).inner_text()

            experience_years = extract_experience(exp_text)

        sections = page.query_selector_all('div[class*="contentSection"]')

        desc = "\n".join([s.inner_text() for s in sections])

        min_s, max_s, is_neg = clean_salary(salary_raw)

        page.close()

        return {
            "source_platform": "Cake",
            "original_job_id": link.split("/")[-1],
            "job_title": job_title,
            "original_job_title": title,
            "company_name": company,
            "min_salary": int(min_s),
            "max_salary": int(max_s),
            "is_negotiable": is_neg,
            "experience_years": experience_years,
            "job_url": full_url,
            "skill_name": extract_skills(desc),
            "raw_job_description": desc.replace("\n", " ")
        }

    except:

        page.close()
        return None


def extract_skills(description):
    """根據技術地圖提取技能"""
    found_skills = set()
    desc_lower = description.lower()
    for tech, aliases in tech_mapping.items():
        for alias in aliases:
            # 使用 \b 確保精確匹配單字
            if re.search(rf'\b{re.escape(alias.lower())}\b', desc_lower):
                found_skills.add(tech)
                break
    return ",".join(found_skills)


def extract_experience(text):

    if not text:
        return 0

    # 不限年資 / 無經驗
    if "不限" in text or "無經驗" in text:
        return 0

    # 抓「x年以上經驗」「x年經驗」
    match = re.search(r'(\d+)\s*年.*?(經驗|工作)', text)

    if match:
        return int(match.group(1))

    return 0


def clean_salary(salary_text):

    if not salary_text:
        return 40000, 40000, 1

    salary_text = salary_text.lower()

    if "面議" in salary_text or "negotiable" in salary_text:
        return 40000, 40000, 1

    if any(x in salary_text.lower() for x in [
        "面議",
        "negotiable",
        "salary negotiable",
        "薪資面議"
    ]):
        return 40000, 40000, 1

    text = salary_text.lower()
    text = text.replace(",", "")
    text = text.replace(" ", "")
    text = text.replace("k", "000")

    nums = re.findall(r'\d+', text)

    if not nums:
        return 40000, 40000, 1

    values = [int(n) for n in nums]

    # 處理萬
    if "萬" in text:
        values = [v * 10000 for v in values]

    min_s = values[0]

    if len(values) > 1:
        max_s = values[1]
    else:
        max_s = min_s

    # 年薪轉月薪
    if "年" in text and "月" not in text:
        min_s //= 12
        max_s //= 12

    return min_s, max_s, 0


def scrape_cake_engineer(target_count=2):

    results = []

    with sync_playwright() as p:

        browser = p.chromium.launch(
            headless=False,       # 改為 False 比較不容易被擋
            slow_mo=random.randint(50, 200)
        )

        context = browser.new_context(
            user_agent=random.choice(USER_AGENTS),
            viewport={"width": 1920, "height": 1080}
        )

        page = context.new_page()

        print("🚀 啟動爬蟲，搜尋關鍵字: 工程師")

        # # 隱藏 webdriver
        # page.add_init_script(
        #     "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        # )

        page = context.new_page()

        print("🚀 啟動爬蟲，多關鍵字搜尋")

        all_links = set()

        for keyword in KEYWORDS:

            print(f"\n🔎 搜尋關鍵字: {keyword}")

            links = collect_job_links(page, keyword, target_count=800)

            all_links.update(links)

        links = list(all_links)

        print("總職缺連結數:", len(links))

        for i in range(0, len(links), 5):

            batch = links[i:i+5]

            pages = []

            for link in batch:
                pages.append(scrape_job_page(context, link))

            for result in pages:
                if result:
                    results.append(result)

            print(f"目前抓到 {len(results)} 筆")

            if len(results) >= target_count:
                break

        browser.close()

    df = pd.DataFrame(results)

    df = df.drop_duplicates(subset=["original_job_id"])

    print("去重後職缺數:", len(df))
    # 找到目前 py 檔位置
    current_dir = os.path.dirname(os.path.abspath(__file__))

    # 上一層資料夾
    project_root = os.path.dirname(current_dir)

    # data 資料夾
    data_dir = os.path.join(project_root, "data")

    if not os.path.exists(data_dir):
        os.makedirs(data_dir)

    csv_path = os.path.join(data_dir, "cake_jobs.csv")

    df.to_csv(
        csv_path,
        index=False,
        encoding="utf-8-sig"
    )

    print("📁 CSV 存到:", csv_path)


if __name__ == "__main__":

    # 執行爬蟲
    scrape_cake_engineer(target_count=3500)
