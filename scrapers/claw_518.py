import requests
import pandas as pd
import re
import time
import os
from bs4 import BeautifulSoup
from urllib.parse import urljoin

# =====================================================
# ⚙️ 設定區
# =====================================================
MAX_PAGES   = 200   # 518 每頁約 20 筆，200 頁 ≈ 4000 筆上限
OUTPUT_FILE = "518_Standard.csv"
BASE_URL    = "https://www.518.com.tw"
LIST_URL    = "https://www.518.com.tw/job-index-P-{page}.html?ad=%E5%B7%A5%E7%A8%8B%E5%B8%AB"

# =====================================================
# 📚 技術白名單（與 Yes123 一致）
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
    支援以下格式：
    - 月薪 38,000 至 49,000 元
    - 年薪 700,000 至 1,000,000 元  → 除以12
    - 月薪 31,900 元以上
    - 面議 (每月經常性薪資達四萬以上) → 40000, 40000, 1
    - 時薪/日薪/論件 → 40000, 40000, 1
    """
    if not sal_text:
        return 40000, 40000, 1

    sal_clean = sal_text.strip()

    # 時薪/日薪/論件：不處理，視為面議
    if any(k in sal_clean for k in ["時薪", "論件", "日薪"]):
        return 40000, 40000, 1

    # 純面議（沒有明確數字範圍）
    # 只有包含「面議」且找不到「月薪」「年薪」才算面議
    has_explicit = any(k in sal_clean for k in ["月薪", "年薪", "至", "以上"])
    if "面議" in sal_clean and not has_explicit:
        return 40000, 40000, 1

    is_annual = "年薪" in sal_clean

    nums = []
    for n in re.findall(r'[\d,]+', sal_clean):
        try:
            val = int(n.replace(',', ''))
            if val >= 1000:  # 過濾太小的數字
                nums.append(val)
        except ValueError:
            continue

    if not nums:
        return 40000, 40000, 1

    min_s = nums[0]
    if len(nums) >= 2:
        max_s = nums[1]
    elif "以上" in sal_clean:
        max_s = int(min_s * 1.2)
    else:
        max_s = min_s

    # 年薪換算月薪
    if is_annual:
        min_s = int(min_s / 12)
        max_s = int(max_s / 12)

    return min_s, max_s, 0


# =====================================================
# 🌐 Session
# =====================================================
def make_session():
    session = requests.Session()
    session.headers.update({
        "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                       "AppleWebKit/537.36 (KHTML, like Gecko) "
                       "Chrome/122.0.0.0 Safari/537.36"),
        "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.8",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Referer": "https://www.518.com.tw/",
    })
    # 先 GET 首頁取 cookie
    try:
        session.get("https://www.518.com.tw/", timeout=10)
    except Exception:
        pass
    return session


# =====================================================
# 📄 詳細頁解析
# =====================================================
def fetch_detail(session, job_url):
    """
    進詳細頁抓：
    - original_job_title : <h1> 文字
    - company_name       : 詳細頁 <h2><a> 公司名
    - raw_job_description: 「工作內容更新日期」段落後的主要文字
    - job_title (category): 「職務類別」區第一個連結文字
    - experience_years   : 「工作經驗」值
    - skill_raw          : 「電腦專長」+「其他條件」文字（給 extract_skills 用）
    回傳 dict，失敗回傳 None。
    """
    try:
        resp = session.get(job_url, timeout=15)
        resp.encoding = 'utf-8'
        soup = BeautifulSoup(resp.text, 'html.parser')

        # ── original_job_title ──
        h1 = soup.find('h1')
        original_title = h1.get_text(strip=True) if h1 else ""

        # ── company_name ──
        comp_tag = soup.find('h2')
        company = ""
        if comp_tag:
            a = comp_tag.find('a')
            company = a.get_text(strip=True) if a else comp_tag.get_text(strip=True)

        # ── raw_job_description：「工作內容更新日期」之後的段落 ──
        raw_desc = ""
        for h2 in soup.find_all('h2'):
            if '工作內容' in h2.get_text():
                # 取該 h2 之後的所有同層元素文字，到下一個 h2 為止
                texts = []
                for sib in h2.next_siblings:
                    if sib.name == 'h2':
                        break
                    if hasattr(sib, 'get_text'):
                        t = sib.get_text(separator=' ', strip=True)
                        if t:
                            texts.append(t)
                    elif isinstance(sib, str) and sib.strip():
                        texts.append(sib.strip())
                raw_desc = ' '.join(texts)
                break

        # ── 薪資：class 含 jobItem-salary 的 div 或 span ──
        sal_text = ""
        sal_tag = soup.find(class_=lambda c: c and 'jobItem-salary' in c)
        if sal_tag:
            sal_text = sal_tag.get_text(strip=True)
        # fallback：找「薪資待遇」附近含月薪/年薪的文字
        if not sal_text:
            for tag in soup.find_all(class_=lambda c: c and 'jobItem' in c):
                t = tag.get_text(strip=True)
                if any(k in t for k in ['月薪', '年薪', '面議']):
                    sal_text = t
                    break
        # fallback2：全文正則
        if not sal_text:
            full_text = soup.get_text(separator='\n')
            sal_match = re.search(r'(月薪|年薪|面議)[^\n]{0,60}', full_text)
            if sal_match:
                sal_text = sal_match.group(0).strip()

        # ── 職缺資訊區（地點、職務類別、工作經驗）──
        job_category = ""
        exp_years    = 0

        # 職務類別：找包含 href="/job-index.html?ab=" 的第一個 a
        for a in soup.find_all('a', href=re.compile(r'job-index\.html\?ab=')):
            text = a.get_text(strip=True)
            if text and not text.startswith('、'):
                job_category = text
                break

        # 工作經驗：找「工作經驗」標籤附近的文字
        full_text = soup.get_text(separator='\n')
        exp_match = re.search(r'工作經驗\s*\n?\s*(.+)', full_text)
        if exp_match:
            exp_raw = exp_match.group(1).strip()
            if '不拘' in exp_raw or exp_raw == '':
                exp_years = 0
            else:
                m = re.search(r'(\d+)', exp_raw)
                exp_years = int(m.group(1)) if m else 0

        # ── skill_raw：電腦專長 + 其他條件 ──
        skill_raw = raw_desc  # 預設用工作內容
        # 找「電腦專長」段落
        pc_match = re.search(r'電腦專長\s*\n?\s*(.+?)(?:\n\n|\n[^\n])', full_text, re.DOTALL)
        other_match = re.search(r'其他條件\s*\n?\s*(.+?)(?:\n\n|\Z)', full_text, re.DOTALL)
        extras = []
        if pc_match:
            extras.append(pc_match.group(1).strip())
        if other_match:
            extras.append(other_match.group(1).strip()[:500])
        if extras:
            skill_raw = raw_desc + ' ' + ' '.join(extras)

        return {
            'original_title': original_title,
            'company':        company,
            'raw_desc':       raw_desc,
            'job_category':   job_category,
            'exp_years':      exp_years,
            'skill_raw':      skill_raw,
            'sal':            sal_text,
        }

    except Exception as e:
        return None


# =====================================================
# 📋 列表頁解析（快速取 job_id、薪資、URL）
# =====================================================
def parse_list_page(soup):
    """
    從列表頁每筆職缺抓：
    - job_id  : URL 中的 job-XXXXX 部分
    - job_url : 完整詳細頁 URL
    - sal_text: 薪資文字
    回傳 list of dict
    """
    results = []
    seen = set()

    for h2 in soup.find_all('h2'):
        a = h2.find('a', href=re.compile(r'/job-[A-Za-z0-9]+\.html'))
        if not a:
            continue
        href = a.get('href', '')
        job_id_match = re.search(r'/job-([A-Za-z0-9]+)\.html', href)
        if not job_id_match:
            continue
        job_id = job_id_match.group(1)
        if job_id in seen:
            continue
        seen.add(job_id)

        job_url = urljoin(BASE_URL, href)

        # 薪資：往上找最近的 article/li/div 容器，抓薪資文字
        container = h2.find_parent(['li', 'article', 'div'])
        sal_text = ""
        if container:
            # 518 薪資格式：「月薪 38,000 至 49,000 元」
            sal_match = re.search(
                r'(月薪|年薪|時薪|日薪|論件|面議)[^\n<]{0,60}',
                container.get_text(separator=' ')
            )
            if sal_match:
                sal_text = sal_match.group(0).strip()

        results.append({
            'job_id':  job_id,
            'job_url': job_url,
            'sal':     sal_text,
        })

    return results


# =====================================================
# 💾 斷點續跑
# =====================================================
def load_checkpoint():
    if not os.path.exists(OUTPUT_FILE):
        return [], set()
    try:
        df = pd.read_csv(OUTPUT_FILE, encoding='utf-8-sig', dtype=str)
        rows = df.to_dict('records')
        done_ids = set(df['original_job_id'].dropna().tolist())
        print(f"📂 讀到既有檔案，已有 {len(rows)} 筆，跳過這些 job_id。")
        return rows, done_ids
    except Exception as e:
        print(f"⚠️  讀取既有檔案失敗（{e}），從頭開始。")
        return [], set()

def save_checkpoint(all_data):
    df = pd.DataFrame(all_data)
    df = df.drop_duplicates(subset=['original_job_id'])
    df.to_csv(OUTPUT_FILE, index=False, encoding='utf-8-sig')


# =====================================================
# 🚀 主程式
# =====================================================
def run_scraper():
    all_data, done_ids = load_checkpoint()
    session = make_session()

    print(f"🚀 開始抓取 518（目標每關鍵字 {MAX_PAGES} 頁，已有 {len(all_data)} 筆）...\n")

    for page in range(1, MAX_PAGES + 1):
        url = LIST_URL.format(page=page)
        try:
            resp = session.get(url, timeout=20)
            resp.encoding = 'utf-8'
            soup = BeautifulSoup(resp.text, 'html.parser')

            items = parse_list_page(soup)
            if not items:
                print(f"⚠️  [{keyword}] 第 {page} 頁找不到職缺，跳下個關鍵字")
                break

            page_new  = 0
            page_skip = 0

            for item in items:
                job_id  = item['job_id']
                job_url = item['job_url']

                if job_id in done_ids:
                    page_skip += 1
                    continue

                detail = fetch_detail(session, job_url)
                if not detail:
                    continue

                min_s, max_s, is_neg = parse_salary(detail.get('sal', '') or item['sal'])

                original_title = detail['original_title']
                job_cat        = detail['job_category']
                std_title      = job_cat if job_cat else normalize_job_title(original_title)

                exp_match = re.search(r'\d+', str(detail['exp_years']))
                exp_years = int(exp_match.group()) if exp_match else detail['exp_years']

                row = {
                    'source_platform':     '518',
                    'original_job_id':     job_id,
                    'job_title':           std_title,
                    'original_job_title':  original_title,
                    'company_name':        detail['company'],
                    'min_salary':          min_s,
                    'max_salary':          max_s,
                    'is_negotiable':       is_neg,
                    'experience_years':    exp_years,
                    'job_url':             job_url,
                    'skill_name':          extract_skills(detail['skill_raw']),
                    'raw_job_description': detail['raw_desc'],
                }

                all_data.append(row)
                done_ids.add(job_id)
                page_new += 1

                if page_new <= 3 and page == 1:
                    print(f"  🔎 [{len(all_data)}] 職稱={std_title[:15]} | "
                          f"原始={original_title[:15]} | "
                          f"公司={detail['company'][:12]} | "
                          f"年資={exp_years} | "
                          f"min={min_s} max={max_s} neg={is_neg}")

                time.sleep(0.5)

            save_checkpoint(all_data)
            print(f"✅ [{keyword}] 第 {page} 頁：新增 {page_new} 筆｜跳過 {page_skip} 筆｜累計 {len(all_data)} 筆")
            time.sleep(2)

        except requests.exceptions.RequestException as e:
            print(f"❌ 網路錯誤（第 {page} 頁）: {e}")
            save_checkpoint(all_data)
            break
        except Exception as e:
            print(f"❌ 解析錯誤（第 {page} 頁）: {e}")
            continue

    save_checkpoint(all_data)
    print(f"\n✨ 完成！共 {len(all_data)} 筆 → {OUTPUT_FILE}")


if __name__ == "__main__":
    run_scraper()