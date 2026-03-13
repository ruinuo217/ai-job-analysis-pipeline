import time
import re
import csv
import logging
import random
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s: %(message)s")

# ==========================================
# 1. CSV 檔案儲存設定 (12個標準欄位)
# ==========================================
def save_to_csv(jobs_list, filename="jobs_104_selenium.csv"):
    if not jobs_list: return
    if isinstance(jobs_list, dict): jobs_list = [jobs_list]
    
    # 🚨 包含 is_negotiable (H欄) 與 raw_job_description (L欄)
    fieldnames = [
        "source_platform", "original_job_id", "job_title", "original_job_title",
        "company_name", "min_salary", "max_salary", "is_negotiable", 
        "experience_years", "job_url", "skill_name", "raw_job_description"
    ]
    
    file_exists = os.path.isfile(filename)
    try:
        with open(filename, "a", newline="", encoding="utf-8-sig") as f:
            dict_writer = csv.DictWriter(f, fieldnames=fieldnames)
            if not file_exists: dict_writer.writeheader()
            dict_writer.writerows(jobs_list)
    except Exception as e: logging.error(f"儲存 CSV 失敗: {e}")

# ==========================================
# 2. PM 清洗邏輯 (薪資 & 全文技術挖掘)
# ==========================================
def clean_salary_logic(min_s, max_s):
    if max_s > 500000: max_s = int(min_s * 1.2)
    return min_s, max_s

def filter_tech_skills(combined_text):
    """
    從超級大字串中挖出技術關鍵字，並「統一標準化名稱」(同義詞字典)
    """
    tech_mapping = {
        # === 軟體與資料庫 (擴充現代網頁與後端) ===
        "Python": ["python", "python3"],
        "Java": ["java"],
        "C++": ["c++", "cpp"],
        "C#": ["c#", "csharp", "c#.net"],
        "JavaScript": ["javascript", "js", "java script"],
        "TypeScript": ["typescript", "ts"],
        "Golang": ["go", "golang"],                  
        "Ruby": ["ruby", "ruby on rails"],           
        "Rust": ["rust"],                            
        "PHP": ["php", "laravel"],                   
        "SQL": ["sql"],
        "MySQL": ["mysql"],
        "PostgreSQL": ["postgresql", "postgres"],
        "NoSQL": ["nosql", "mongodb", "redis"],
        
        # === 前端網頁、手機 App 與介面設計 (擴充) ===
        "React": ["react", "react.js", "reactjs", "react native"],
        "Vue": ["vue", "vue.js", "vuejs"],
        "Next.js": ["next.js", "nextjs"],            
        "Node.js": ["node.js", "nodejs", "node"],
        "HTML": ["html", "html5"],
        "CSS": ["css", "css3", "tailwind", "sass"],  
        "Swift": ["swift", "ios"],                   
        "Kotlin": ["kotlin", "android"],             
        "Flutter": ["flutter"],                      
        "UI/UX設計": ["ui/ux", "ui", "ux", "figma", "sketch", "使用者體驗"], 
        "SEO": ["seo", "搜尋引擎優化"],                
        
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
        "CI/CD": ["ci/cd", "cicd", "jenkins"],       
        
        # === AI、資料科學與分析 (大擴充) ===
        "R語言": ["r", "r language", "r語言"],
        "Tableau": ["tableau"],
        "Power BI": ["power bi", "powerbi"],
        "Excel": ["excel"],
        "Hadoop": ["hadoop"],
        "Spark": ["spark", "apache spark"],
        "Pandas": ["pandas", "numpy"],               
        "PyTorch": ["pytorch"],                      
        "TensorFlow": ["tensorflow", "tf"],          
        "OpenAI API": ["openai", "llm", "chatgpt"],  
        
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
    
    found_tech = []
    for std_name, aliases in tech_mapping.items():
        for alias in aliases:
            if alias == "c":
                pattern = r'(?<![A-Za-z0-9])c(?![A-Za-z0-9\+\#])'
            elif alias in ["r", "js", "ts", "qa", "qc", "go", "tf"]:
                pattern = r'(?<![A-Za-z0-9])' + alias + r'(?![A-Za-z0-9])'
            else:
                pattern = r'(?<![A-Za-z0-9])' + re.escape(alias) + r'(?![A-Za-z0-9])'
                
            if re.search(pattern, combined_text, re.IGNORECASE):
                found_tech.append(std_name)
                break 
                
    return ",".join(found_tech)

# ==========================================
# 3. 虛擬機專用 WebDriver 設定
# ==========================================
def setup_driver():
    options = Options()
    options.add_argument("--headless=new") 
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    driver.set_script_timeout(15)
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    })
    return driver

# ==========================================
# 4. 爬蟲主邏輯
# ==========================================
def crawl_104_jobs_selenium(keyword, max_pages=150): # 🚨 已經幫妳改成抓滿 150 頁上限！
    driver = setup_driver()
    total_count = 0

    for page in range(1, max_pages + 1):
        logging.info(f"正在抓取【{keyword}】第 {page} 頁...")
        url = f"https://www.104.com.tw/jobs/search/?keyword={keyword}&page={page}&jobsource=2018indexpoc&ro=0"
        
        try:
            driver.get(url)
            time.sleep(3) 
            
            total_height = int(driver.execute_script("return document.body.scrollHeight"))
            for i in range(1, total_height, 600):
                driver.execute_script(f"window.scrollTo(0, {i});")
                time.sleep(0.5) 
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            
            jobs_links = []
            for a in driver.find_elements(By.CSS_SELECTOR, "a[href*='/job/']"):
                try:
                    href = a.get_attribute("href")
                    if href and "/job/" in href and "jobsource" in href:
                        clean_link = href.split('?')[0]
                        if clean_link not in jobs_links:
                            jobs_links.append(clean_link)
                except: continue
            
            if not jobs_links:
                logging.info("本頁找不到任何職缺連結。可能已經到達最後一頁！")
                break
                    
            logging.info(f"本頁找到 {len(jobs_links)} 個職缺，準備進入詳細頁擷取...")
            page_data = []
            
            for link in jobs_links:
                try:
                    driver.get(link)
                    time.sleep(1) 
                    
                    job_id = link.split('/')[-1]
                    js_code = """
                        var url = '/job/ajax/content/' + arguments[0];
                        var callback = arguments[1];
                        fetch(url, { headers: { "X-Requested-With": "XMLHttpRequest" } })
                        .then(r => r.json()).then(data => callback(data)).catch(e => callback(null));
                    """
                    detail_json = driver.execute_async_script(js_code, job_id)
                    
                    if not detail_json or "data" not in detail_json: continue
                    data = detail_json["data"]
                    
                    original_job_title = data.get("header", {}).get("jobName", "未知職稱")
                    company_name = data.get("header", {}).get("custName", "未知公司")
                    job_categories = data.get("jobDetail", {}).get("jobCategory", [])
                    job_title = job_categories[0]["description"].split('、')[0].strip() if job_categories else original_job_title

                    salary_desc = data.get("jobDetail", {}).get("salaryDesc", "")
                    raw_min = data.get("jobDetail", {}).get("salaryMin", 0)
                    raw_max = data.get("jobDetail", {}).get("salaryMax", 0)

                    # 破解 104 API 的文字遊戲：把「經常性」也視為面議！
                    is_negotiable = 1 if ("面議" in salary_desc or "經常性" in salary_desc or raw_min == 0) else 0

                    if is_negotiable == 1:
                        min_s = max_s = 40000
                    else:
                        if "年薪" in salary_desc and raw_min > 100000:
                            raw_min, raw_max = raw_min // 12, raw_max // 12
                        min_s, max_s = clean_salary_logic(raw_min, raw_max)
                        if max_s == 0 or max_s < min_s:
                            max_s = min_s

                    cond = data.get("condition", {})
                    exp_str = cond.get("workExp", "")
                    work_exp = int(re.search(r'\d+', exp_str).group()) if re.search(r'\d+', exp_str) else 0

                    raw_texts_to_scan = [
                        data.get("jobDetail", {}).get("jobDescription", ""),
                        cond.get("other", "")
                    ]
                    for sp in cond.get("specialty", []): raw_texts_to_scan.append(sp.get("description", ""))
                    for sk in cond.get("skill", []): raw_texts_to_scan.append(sk.get("description", ""))
                    
                    combined_full_text = " ".join(raw_texts_to_scan)
                    skill_name_str = filter_tech_skills(combined_full_text)

                    page_data.append({
                        "source_platform": "104",
                        "original_job_id": job_id,
                        "job_title": job_title,
                        "original_job_title": original_job_title,
                        "company_name": company_name,
                        "min_salary": min_s,
                        "max_salary": max_s,
                        "is_negotiable": is_negotiable, 
                        "experience_years": work_exp,
                        "job_url": link,
                        "skill_name": skill_name_str,
                        "raw_job_description": combined_full_text 
                    })
                    logging.info(f"✅ 成功: {original_job_title[:8]}... | 面議:{is_negotiable} | 挖出技能: {skill_name_str[:15]}")
                    
                except Exception as e:
                    logging.warning(f"❌ 擷取詳細頁面失敗 ({link}): {e}")
                    
                time.sleep(random.uniform(1.5, 3)) 
                
            if page_data:
                save_to_csv(page_data)
                total_count += len(page_data)
                logging.info(f"🎉 第 {page} 頁完成！目前累積收集: {total_count} 筆")
                
        except Exception as e:
            logging.error(f"存取列表頁面失敗: {e}")
            break
            
    driver.quit()
    logging.info(f"爬蟲任務完全結束！總共入庫 {total_count} 筆黃金資料！")

def deduplicate_csv(filename="jobs_104_selenium.csv"):
    if not os.path.isfile(filename):
        logging.warning(f"找不到檔案: {filename}，跳過去重。")
        return

    with open(filename, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        rows = list(reader)

    before_count = len(rows)
    seen_keys = set()
    unique_rows = []

    for row in rows:
        # ✅ 用「職缺名稱 + 公司名稱」當複合 key，忽略大小寫與前後空白
        job_title   = row.get("original_job_title", "").strip().lower()
        company     = row.get("company_name", "").strip().lower()
        composite_key = (job_title, company)

        if composite_key not in seen_keys:
            seen_keys.add(composite_key)
            unique_rows.append(row)

    after_count = len(unique_rows)
    removed = before_count - after_count

    with open(filename, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(unique_rows)

    logging.info(f"✅ 去重完成！原始:{before_count} 筆 → 去重後:{after_count} 筆 (移除 {removed} 筆重複)")

    if __name__ == "__main__":
    crawl_104_jobs_selenium("工程師", max_pages=150)
    
    # 爬完立刻去重
    deduplicate_csv("jobs_104_selenium.csv")