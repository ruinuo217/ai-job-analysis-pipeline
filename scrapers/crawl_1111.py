import time
import re
import csv
import logging
import random
import os
from datetime import datetime
import requests
from bs4 import BeautifulSoup

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s: %(message)s"
)


# CSV 檔案儲存設定
def save_to_csv(jobs_list, filename="jobs.csv"):
    if not jobs_list:
        logging.info("沒有抓取到任何職缺資料，不建立 CSV。")
        return

    if isinstance(jobs_list, dict):
        jobs_list = [jobs_list]

    keys = jobs_list[0].keys()
    file_exists = os.path.isfile(filename)

    try:
        with open(filename, "a", newline="", encoding="utf-8-sig") as f:
            dict_writer = csv.DictWriter(f, fieldnames=keys)
            if not file_exists:
                dict_writer.writeheader()
            dict_writer.writerows(jobs_list)
        logging.info(f"成功儲存 {len(jobs_list)} 筆資料至 {filename}")
    except Exception as e:
        logging.error(f"儲存 CSV 失敗: {e}")


def parse_salary(salary_str):
    """
    將待遇字串轉換為最低與最高月薪
    """
    min_s, max_s = None, None
    is_negotiable = 0
    if not salary_str:
        return min_s, max_s, is_negotiable

    # 將千分位逗號移除
    s = salary_str.replace(",", "")
    # 找數字
    nums = re.findall(r"\d+", s)

    if "月薪" in s:
        if len(nums) >= 2:
            min_s, max_s = int(nums[0]), int(nums[1])
        elif len(nums) == 1:
            min_s = int(nums[0])
    elif "年薪" in s:
        if len(nums) >= 2:
            min_s, max_s = int(nums[0]) // 12, int(nums[1]) // 12
        elif len(nums) == 1:
            min_s = int(nums[0]) // 12
    elif "面議" in s:
        is_negotiable = 1
        if len(nums) >= 1:  # 待遇面議(經常性薪資達4萬元或以上)
            val = int(nums[0])
            min_s = val * 10000 if val < 100 else val
        else:
            min_s = 40000  # 預設經常性滿4萬
    else:
        # 時薪、日薪等暫不轉換月薪
        pass
    if min_s and max_s is None:
        max_s = min_s * 1.2
    return min_s, max_s, is_negotiable


def get_detail(soup, keyword):
    """
    自詳細頁面提取對應欄位的內容
    """
    h3 = soup.find("h3", string=lambda s: s and keyword in s)
    if h3:
        sibling = h3.find_next_sibling()
        if sibling:
            return sibling.get_text(separator=",", strip=True)  # 用 ',' 取代標籤間隔
    return ""


def crawl_1111_jobs(keywords, max_pages=5):
    seen_job_ids = set()

    categories = [
        "100100,100300,100600,100800,101100,101300,101500,101800,102200",
        "100200,100500,100700,100900,101200,101400,101600,102000,100400,102100",
    ]

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36 Edg/145.0.0.0",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Cache-Control": "max-age=0",
        "sec-ch-ua": '"Not:A-Brand";v="99", "Microsoft Edge";v="145", "Chromium";v="145"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Site": "same-origin",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-User": "?1",
        "Sec-Fetch-Dest": "document",
        "Referer": "https://www.1111.com.tw/",
        "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6,zh-CN;q=0.5,ja;q=0.4",
    }

    session = requests.Session()
    session.headers.update(headers)

    for kw in keywords:
        for cat in categories:
            logging.info(f"開始搜尋關鍵字: {kw}")
            session.cookies.clear()

            jobs_info = []
            for page in range(1, max_pages + 1):
                url = "https://www.1111.com.tw/search/job"
                params = {"page": str(page), "ks": kw, "c0": cat, "wk": "1"}

                try:
                    response = session.get(url, params=params, timeout=10)
                    response.raise_for_status()
                except Exception as e:
                    logging.error(f"請求列表頁失敗: 第 {page} 頁 - {e}")
                    time.sleep(2)
                    continue

                soup = BeautifulSoup(response.text, "html.parser")
                jobs = soup.select(".job-card")

                if not jobs:
                    logging.info(f"第 {page} 頁沒有找到職缺區塊，結束該參數的換頁。")
                    break

                logging.info(f"第 {page} 頁找到 {len(jobs)} 個職缺區塊")

                for job in jobs:
                    try:
                        title_element = job.find(
                            "a", class_=lambda c: c and "text-[#212529]" in c
                        )
                        if title_element:
                            job_url_raw = title_element.get("href", "")
                            job_url = (
                                "https://www.1111.com.tw" + job_url_raw
                                if job_url_raw.startswith("/")
                                else job_url_raw
                            )
                            job_name = title_element.get("title", "")
                        else:
                            # 備用提取方式
                            title_element = job.find(
                                "a", href=lambda h: h and h.startswith("/job/")
                            )
                            if not title_element:
                                continue
                            job_url_raw = title_element.get("href", "")
                            job_url = (
                                "https://www.1111.com.tw" + job_url_raw
                                if job_url_raw.startswith("/")
                                else job_url_raw
                            )
                            job_name = (
                                title_element.get("title", "")
                                or title_element.text.strip()
                            )

                        company_element = job.find(
                            "a", class_=lambda c: c and "leading-[1.6]" in c
                        )
                        if company_element:
                            company = company_element.get("title", "").strip()
                        else:
                            # 備用提取方式
                            company_element = job.find(
                                "a", href=lambda h: h and h.startswith("/corp/")
                            )
                            company = (
                                company_element.get("title", "").strip()
                                if company_element
                                else ""
                            )

                        # 從 url 中提取 ID
                        job_id = job_url.split("/")[-1].split("?")[0]

                        if job_id not in seen_job_ids:
                            seen_job_ids.add(job_id)
                            jobs_info.append(
                                {
                                    "id": job_id,
                                    "url": job_url,
                                    "job_name": job_name,
                                    "company_name": company,
                                }
                            )
                    except Exception as e:
                        continue

                # time.sleep(random.uniform(1, 2))

            # 接著依序進入詳細頁面抓取深入資料
            for info in jobs_info:
                try:
                    try:
                        detail_resp = session.get(info["url"], timeout=10)
                        detail_resp.raise_for_status()
                    except Exception as e:
                        logging.warning(f"詳細頁面載入失敗: {info['url']} - {e}")
                        time.sleep(2)
                        continue

                    detail_soup = BeautifulSoup(detail_resp.text, "html.parser")

                    # 薪水
                    salary_str = get_detail(detail_soup, "工作待遇")
                    min_s, max_s, is_negotiable = parse_salary(salary_str)

                    # 職務類別
                    job_title_str = get_detail(detail_soup, "職務類別")
                    job_title = job_title_str.split(",、,")[0] if job_title_str else ""

                    # 工作經歷
                    work_exp_str = get_detail(detail_soup, "工作經驗")
                    work_exp = (
                        0
                        if "不拘" in work_exp_str or "以下" in work_exp_str
                        else (
                            int(re.search(r"\d+", work_exp_str).group())
                            if re.search(r"\d+", work_exp_str)
                            else 0
                        )
                    )

                    # 工作技能
                    skills = get_detail(detail_soup, "電腦專長").replace(",、,", ",")
                    skills2 = get_detail(detail_soup, "工作技能").replace(",、,", ",")

                    skills_list = ",".join([s for s in [skills, skills2] if s])

                    summary = get_detail(detail_soup, "職缺描述").strip()
                    # 組合資料並存入 CSV
                    final_data = {
                        "source_platform": "1111",
                        "original_job_id": info["id"],
                        "job_title": job_title,
                        "original_job_title": info["job_name"],
                        "company_name": info["company_name"],
                        "min_salary": min_s,
                        "max_salary": max_s,
                        "is_negotiable": is_negotiable,
                        "experience_years": work_exp,
                        "job_url": info["url"],
                        "skill_name": skills_list,
                        "summary": summary,
                    }
                    save_to_csv(final_data)
                    logging.info(
                        f"已收集: {final_data['original_job_title']} - {final_data['company_name']}"
                    )

                    # time.sleep(random.uniform(1, 2))  # 隨機暫停，避免被擋

                except Exception as e:
                    logging.error(f"抓取詳細頁面失敗: {info['url']} - {e}")


if __name__ == "__main__":
    keywords = ["工程師"]
    crawl_1111_jobs(keywords, max_pages=150)  # 翻頁次數，可依需求調整
