import requests
import pandas as pd
import re
import time
from bs4 import BeautifulSoup

# =====================================================
# ⚙️ 設定區
# =====================================================
DEBUG_MODE = False      # True = 先診斷 HTML 結構，False = 正式抓取
DEEP_DEBUG = False     # True = 印出第一筆容器完整 HTML（用來確認 selector）
MAX_PAGES = 150
OUTPUT_FILE = "Yes123_Standard_Fixed.csv"
DEBUG_HTML_FILE = "yes123_debug.html"  # 診斷用，存第一頁原始 HTML

# =====================================================
# 📚 技術白名單（擴充版）
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
            if re.search(r'[一-鿿]', a):
                # 含中文 alias：plain 比對
                pattern = re.escape(a)
            else:
                # 純英數：左右兩側允許空白、標點、中文（處理「以Verilog撰寫」類情況）
                # 但防止 "r" 誤中 "for"（左側不能是字母）
                pattern = (r'(?:^|(?<=[\s\W\u4e00-\u9fff]))'
                           + re.escape(a)
                           + r'(?=[\s\W\u4e00-\u9fff]|$)')
            if re.search(pattern, text_lower):
                found_skills.append(std_name)
                break
    return ",".join(sorted(list(set(found_skills))))

def normalize_job_title(title):
    """
    將原始職稱對應到標準化職稱。
    規則：抓取官方「職務類別」的第一個，這裡用關鍵字做簡易對應。
    """
    title_lower = title.lower()
    if any(k in title_lower for k in ["前端", "frontend", "front-end", "react", "vue", "ui工程"]):
        return "前端工程師"
    if any(k in title_lower for k in ["後端", "backend", "back-end", "server", "api"]):
        return "後端工程師"
    if any(k in title_lower for k in ["全端", "fullstack", "full-stack", "full stack"]):
        return "全端工程師"
    if any(k in title_lower for k in ["資料", "data", "機器學習", "ml", "ai", "分析師"]):
        return "資料科學家"
    if any(k in title_lower for k in ["韌體", "firmware", "嵌入式", "embedded", "fpga", "mcu"]):
        return "韌體工程師"
    if any(k in title_lower for k in ["硬體", "hardware", "pcb", "電路", "circuit"]):
        return "硬體工程師"
    if any(k in title_lower for k in ["app", "ios", "android", "mobile", "flutter", "swift", "kotlin"]):
        return "App工程師"
    if any(k in title_lower for k in ["devops", "sre", "雲端", "cloud", "infra", "linux系統"]):
        return "DevOps工程師"
    if any(k in title_lower for k in ["qa", "qc", "測試", "test"]):
        return "QA工程師"
    if any(k in title_lower for k in ["機構", "cad", "solidworks", "設計工程"]):
        return "機構工程師"
    # 預設 fallback
    return "工程師"

def parse_salary(sal_text):
    """
    薪資解析：
    - 面議或空白 → min=max=40000, is_negotiable=1
    - 有數字：抓低標/高標
    - 若最大值 > 500000（年薪50萬以上）→ max = min * 1.2（依規格）
    - 支援「萬」單位換算
    """
    if not sal_text or "面議" in sal_text or "待遇面議" in sal_text:
        return 40000, 40000, 1

    nums = []
    for n in re.findall(r'[\d\.]+', sal_text.replace(',', '')):
        try:
            val = float(n)
            if val < 1000 and "萬" in sal_text:
                nums.append(int(val * 10000))
            else:
                nums.append(int(val))
        except ValueError:
            continue

    if not nums:
        return 40000, 40000, 1

    min_s = nums[0]
    if len(nums) > 1:
        max_s = nums[1]
    elif "以上" in sal_text:
        max_s = int(min_s * 1.2)
    else:
        max_s = min_s

    # 規格：若 max > 500000（可能是年薪誤填月薪欄），改為 min * 1.2
    if max_s > 500000:
        max_s = int(min_s * 1.2)

    return min_s, max_s, 0

def clean_job_data(raw):
    """
    依欄位規格清洗資料：
    - source_platform : 固定 'Yes123'
    - original_job_id : 原始 ID（防呆去重用）
    - job_title       : 標準化職稱（由原始職稱推導）
    - original_job_title : 原始職稱（公司自填）
    - company_name    : 公司名稱
    - min_salary      : 最低月薪（面議預設 40000）
    - max_salary      : 最高月薪（>50萬 → min*1.2；面議預設 40000）
    - is_negotiable   : 0=有明確數字, 1=面議
    - experience_years: 年資純數字，不拘填 0
    - job_url         : 完整職缺網址
    - skill_name      : 技術白名單過濾後，逗號串接
    - raw_job_description : 原始完整職缺內容（ELT 備份區）
    """
    min_s, max_s, is_neg = parse_salary(raw.get('sal', ""))

    exp_match = re.search(r'\d+', raw.get('exp', "0"))
    exp_years = int(exp_match.group()) if exp_match else 0

    original_title = raw.get('title', '')
    # job_title：優先用詳細頁「職務類別」第一項，沒抓到才用關鍵字推導
    job_cat   = raw.get('job_cat', '').strip()
    std_title = job_cat if job_cat else normalize_job_title(original_title)

    # raw_job_description：詳細頁工作內容（<h6>工作內容</h6> 下的 <p>），照抄不加工
    raw_desc = raw.get('desc', '')

    return {
        'source_platform':     'Yes123',
        'original_job_id':     raw.get('id'),
        'job_title':           std_title,
        'original_job_title':  original_title,
        'company_name':        raw.get('comp', '未知公司'),
        'min_salary':          min_s,
        'max_salary':          max_s,
        'is_negotiable':       is_neg,
        'experience_years':    exp_years,
        'job_url':             raw.get('job_url', ''),
        'skill_name':          extract_skills(raw.get('skill_raw', '') or raw_desc),
        'raw_job_description': raw_desc,
    }

def make_session():
    session = requests.Session()
    session.headers.update({
        # ✅ 完整的 User-Agent（原版有省略號導致失敗）
        'User-Agent': (
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
            'AppleWebKit/537.36 (KHTML, like Gecko) '
            'Chrome/124.0.0.0 Safari/537.36'
        ),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'zh-TW,zh;q=0.9,en-US;q=0.8',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Referer': 'https://www.yes123.com.tw/',
    })
    # ✅ 先訪問首頁取得合法 Cookie（模擬正常瀏覽行為）
    try:
        session.get("https://www.yes123.com.tw/", timeout=10)
        print("✅ Cookie 初始化成功")
    except Exception as e:
        print(f"⚠️  首頁初始化失敗（但繼續執行）: {e}")
    return session

def debug_html_structure(session):
    """
    診斷模式：抓第一頁 HTML 存檔，並印出所有可能的職缺容器結構
    用途：讓你知道實際 class 名稱，以修正 selector
    """
    print("\n🔍 診斷模式啟動 —— 分析第一頁 HTML 結構...\n")
    payload = {
        'find_key1': '工程師',
        'search_job_t': '1',
        'strRec': '0'
    }
    resp = session.post(
        "https://www.yes123.com.tw/wk_index/joblist.asp",
        data=payload, timeout=20
    )
    resp.encoding = 'utf-8'

    # 存原始 HTML 供你用瀏覽器開啟檢視
    with open(DEBUG_HTML_FILE, 'w', encoding='utf-8') as f:
        f.write(resp.text)
    print(f"📄 原始 HTML 已存到：{DEBUG_HTML_FILE}（用瀏覽器開啟可看完整結構）\n")

    soup = BeautifulSoup(resp.text, 'html.parser')

    # 找所有含 p_id= 的連結（即職缺）
    links = soup.select('a[href*="p_id="]')
    print(f"🔗 找到含 p_id= 的連結數量：{len(links)}")
    if not links:
        print("❌ 完全找不到 p_id 連結，可能被擋或網址結構已改變")
        print("   → 請打開 yes123_debug.html 確認頁面內容")
        return

    # 印出前3個連結的父層 class，幫你找對 selector
    print("\n📦 前 3 個職缺連結的父層 div class（用來確認容器 selector）：")
    for i, link in enumerate(links[:3]):
        print(f"\n  [{i+1}] 連結文字: {link.get_text(strip=True)[:30]}")
        parent = link.parent
        for _ in range(5):  # 往上找最多5層
            if parent and parent.name == 'div':
                print(f"       父層 div class: {parent.get('class')}")
            parent = parent.parent if parent else None

    # 印出頁面中所有 div 的 class 前20個（找規律）
    all_div_classes = list({
        ' '.join(d.get('class', []))
        for d in soup.find_all('div')
        if d.get('class')
    })[:20]
    print(f"\n📋 頁面中出現的 div class（前20個）：")
    for c in all_div_classes:
        print(f"   - {c}")

def parse_job_from_container(container, link, job_id, href):
    """
    從 Job_opening_item 容器抽取職缺資訊。
    採多重 fallback 策略，適應 Yes123 HTML 結構。
    """
    title = link.get_text(strip=True)

    def get_text(selector, default=""):
        tag = container.select_one(selector)
        return tag.get_text(strip=True) if tag else default

    # ── job_url：href 格式為 "job.asp?p_id=XXX&job_id=YYY"（相對路徑，無斜線） ──
    if href.startswith('http'):
        job_url = href
    elif href.startswith('/'):
        job_url = "https://www.yes123.com.tw" + href
    else:
        job_url = "https://www.yes123.com.tw/wk_index/" + href

    # ── 公司名稱：在 Job_opening_item_title 的 <h6><a> ────
    comp = ""
    title_div = container.select_one('.Job_opening_item_title')
    if title_div:
        h6 = title_div.find('h6')
        if h6:
            a_tag = h6.find('a')
            if a_tag:
                comp = a_tag.get_text(strip=True)

    # Fallback：找 href 含 comp_info 的 <a>
    if not comp:
        for a in container.find_all('a'):
            if 'comp_info' in a.get('href', ''):
                comp = a.get_text(strip=True)
                break

    comp = comp or "未知公司"
    info_div = container.select_one('.Job_opening_item_info')

    # ── 薪資 ──────────────────────────────────────────────
    # Yes123 薪資可能在 .pay_static 或含「元」「萬」「薪」的文字節點
    sal = get_text('.pay_static')
    if not sal:
        # 在整個容器找含薪資關鍵字的文字
        for tag in container.find_all(string=re.compile(r'[薪元萬]|面議')):
            text = tag.strip()
            if len(text) >= 2:
                sal = text
                break
    sal = sal or "面議"

    # ── 年資 ──────────────────────────────────────────────
    info_text = info_div.get_text(" ", strip=True) if info_div else ""
    exp_match = re.search(r'(\d+)\s*年', info_text)
    exp = exp_match.group(0) if exp_match else "0"

    # ── 職缺描述 ───────────────────────────────────────────
    desc = container.get_text(separator=" ", strip=True)

    return {
        'id':      job_id,
        'title':   title,
        'comp':    comp,
        'sal':     sal,
        'exp':     exp,
        'desc':    desc,
        'job_url': job_url,
    }

def fetch_job_detail(session, p_id, job_id):
    """
    呼叫右側面板 AJAX endpoint，抓取：
    - 「工作內容」<h6> 下的 <p>  → work_content (str)
    - 「工作經驗」<h6> 下的 <p>  → exp_years (int, 不拘=0)
    回傳 (work_content, exp_years)，失敗時回傳 ("", 0)。
    """
    try:
        resp = session.post(
            "https://www.yes123.com.tw/wk_index/job_refer_list_showRight_2021.asp",
            data={
                'p_id':           p_id,
                'job_id':         job_id,
                'show_type':      '1',
                'search_keyword': '',
            },
            timeout=15
        )
        resp.encoding = 'utf-8'
        soup = BeautifulSoup(resp.text, 'html.parser')

        work_content  = ""
        exp_years     = 0
        job_category  = ""
        original_title = ""

        # ── original_job_title：詳細頁 <a><p>職稱</p></a> ──
        for a in soup.find_all('a'):
            p = a.find('p')
            if p:
                text = p.get_text(strip=True)
                if text:
                    original_title = text
                    break

        # ── skill_name 原始文字：所有含 job_explain 的 div（含 mt 變體）──
        skill_raw = ""
        job_explains = soup.find_all('div', class_=lambda c: c and 'job_explain' in c)
        all_parts = []
        for je in job_explains:
            for s in je.find_all('span', class_='right_main'):
                t = s.get_text(separator=' ', strip=True)
                if t:
                    all_parts.append(t)
        # 同時納入工作內容文字（work_content 已抓到）
        if work_content:
            all_parts.append(work_content)
        skill_raw = ' '.join(all_parts)

        # ── skill_raw：技能與求職專長區 job_explain > right_main ──
        skill_raw = ""
        job_explain = soup.find('div', class_='job_explain')
        if job_explain:
            parts = [s.get_text(strip=True)
                     for s in job_explain.find_all('span', class_='right_main')]
            skill_raw = ' '.join(parts)

        for h6 in soup.find_all('h6'):
            h6_text = h6.get_text(strip=True)
            parent  = h6.find_parent('div')
            if not parent:
                continue

            # ── 工作內容 ──
            if '工作內容' in h6_text:
                paras = parent.find_all('p')
                texts = [p.get_text(strip=True) for p in paras if p.get_text(strip=True)]
                if texts:
                    work_content = ' '.join(texts)

            # ── 工作經驗 ──
            elif '工作經驗' in h6_text:
                paras = parent.find_all('p')
                for p in paras:
                    raw = p.get_text(strip=True)
                    if not raw or '不拘' in raw:
                        exp_years = 0
                        break
                    m = re.search(r'(\d+)', raw)
                    if m:
                        exp_years = int(m.group(1))
                        break

            # ── 職務類別（取第一個，&nbsp; 為分隔符）──
            elif '職務類別' in h6_text:
                paras = parent.find_all('p')
                for p in paras:
                    # innerHTML 中 &nbsp; 會被 BS4 解成  ，用它切割
                    raw_html = str(p)
                    # 先用 &nbsp; 或   切，取第一段
                    import re as _re
                    raw_text = p.get_text(separator='|', strip=True)
                    parts = [x.strip() for x in _re.split(r'[|  ]+', raw_text) if x.strip()]
                    if parts:
                        job_category = parts[0]
                        break

        return work_content, exp_years, job_category, original_title, skill_raw

    except Exception:
        return "", 0, "", "", ""


def load_checkpoint():
    """
    載入已存的 CSV（斷點續跑用）。
    回傳 (existing_rows_list, done_job_ids_set)。
    """
    import os
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
    """每頁結束後存一次，確保中斷不遺失資料。"""
    df = pd.DataFrame(all_data)
    df = df.drop_duplicates(subset=['original_job_id'])
    df.to_csv(OUTPUT_FILE, index=False, encoding='utf-8-sig')


KEYWORDS = [
    '工程師', '軟體工程師', '韌體工程師', '前端工程師',
    '後端工程師', '資料工程師', 'DevOps', 'AI工程師', '全端工程師',
]

def run_scraper(max_pages=MAX_PAGES):
    # ── 斷點續跑：載入已抓資料 ──────────────────────────
    all_data, done_ids = load_checkpoint()
    session = make_session()
    deep_debug_done = False

    print(f"🚀 開始抓取（目標每關鍵字 {max_pages} 頁，目前已有 {len(all_data)} 筆）...\n")

    for keyword in KEYWORDS:
        print(f"\n🔑 關鍵字：{keyword}")
        for page in range(max_pages):
            payload = {
                'find_key1':    keyword,
                'search_job_t': '1',
                'strRec':       str(page * 30)
            }

            try:
                resp = session.post(
                    "https://www.yes123.com.tw/wk_index/joblist.asp",
                    data=payload, timeout=20
                )
                resp.encoding = 'utf-8'
                soup = BeautifulSoup(resp.text, 'html.parser')

                links = soup.select('a[href*="p_id="]')
                if not links:
                    print(f"⚠️  第 {page+1} 頁找不到職缺連結，可能已是最後一頁或被擋")
                    break

                processed_ids = set()
                page_count = 0
                page_skip  = 0

                for link in links:
                    title = link.get_text(strip=True)
                    if len(title) < 2:
                        continue

                    href = link.get('href', '')
                    job_id_match = re.search(r'p_id=([^&]+)', href)
                    if not job_id_match:
                        continue
                    job_id = job_id_match.group(1)

                    # ── 本頁去重 ──
                    if job_id in processed_ids:
                        continue
                    processed_ids.add(job_id)

                    # ── 斷點續跑：已抓過就跳過 ──
                    if job_id in done_ids:
                        page_skip += 1
                        continue

                    container = (
                        link.find_parent('div', class_='Job_opening_item')
                        or link.find_parent('div', class_=re.compile(r'Job_opening', re.I))
                        or link.find_parent('div')
                    )
                    if not container:
                        continue

                    # ── DEEP_DEBUG ──
                    if DEEP_DEBUG and not deep_debug_done:
                        print("\n" + "="*70)
                        print("🔬 DEEP DEBUG — 第一筆職缺容器完整 HTML（只印一次）：")
                        print("="*70)
                        print(container.prettify()[:3000])
                        print("="*70 + "\n")
                        deep_debug_done = True

                    raw_info = parse_job_from_container(container, link, job_id, href)

                    # 詳細頁工作內容
                    detail_job_id_match = re.search(r'job_id=([^&]+)', href)
                    detail_job_id = detail_job_id_match.group(1) if detail_job_id_match else ''
                    detail_p_id   = job_id

                    work_content, exp_years, job_category, orig_title, skill_raw = fetch_job_detail(session, detail_p_id, detail_job_id)
                    raw_info['desc']       = work_content
                    raw_info['exp']        = str(exp_years)
                    raw_info['job_cat']    = job_category
                    raw_info['skill_raw']  = skill_raw
                    if orig_title:
                        raw_info['title']  = orig_title

                    cleaned = clean_job_data(raw_info)
                    all_data.append(cleaned)
                    done_ids.add(job_id)
                    page_count += 1

                    if page_count <= 5 and page == 0:
                        print(f"  🔎 [{len(all_data)}] 原始職稱={raw_info['title'][:12]} | "
                              f"職務類別={job_category[:12] if job_category else '(空)'} | "
                              f"公司={raw_info['comp'][:12]} | "
                              f"年資={exp_years} | "
                              f"工作內容={work_content[:15] if work_content else '(空)'}")

                    time.sleep(0.5)

                # ── 每頁結束存一次檔（斷點保護）──
                save_checkpoint(all_data)
                print(f"✅ [{keyword}] 第 {page+1} 頁：新增 {page_count} 筆｜跳過 {page_skip} 筆｜累計 {len(all_data)} 筆")
                time.sleep(2)

            except requests.exceptions.RequestException as e:
                print(f"❌ 網路錯誤（第 {page+1} 頁）: {e}")
                save_checkpoint(all_data)
                break
            except Exception as e:
                print(f"❌ 解析錯誤（第 {page+1} 頁）: {e}")
                continue

    save_checkpoint(all_data)
    print(f"\n✨ 完成！共 {len(all_data)} 筆有效資料 → {OUTPUT_FILE}")

# =====================================================
# 🚦 主程式入口
# =====================================================
if __name__ == "__main__":
    session = make_session()

    if DEBUG_MODE:
        # 步驟1：先跑診斷，看清楚 HTML 結構
        debug_html_structure(session)
        print("\n" + "="*60)
        print("📌 請根據診斷結果修改 parse_job_from_container() 中的 selector")
        print("   確認無誤後，將 DEBUG_MODE = False 再正式抓取")
        print("="*60)
    else:
        # 步驟2：正式抓取
        run_scraper(MAX_PAGES)