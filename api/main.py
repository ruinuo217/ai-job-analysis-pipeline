from flask import Flask, jsonify, render_template
from flasgger import Swagger
import os
from dotenv import load_dotenv
import pymysql

load_dotenv()

connection = pymysql.connect(
    host=os.getenv("DB_HOST"),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASS"),
    database=os.getenv("DB_NAME"),
    charset="utf8mb4",
    cursorclass=pymysql.cursors.DictCursor,
)

app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False  # 解決中文亂碼問題
swagger = Swagger(app)               # 初始化 Swagger API 文件

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/job/top-skills", methods=["GET"])
def get_top_skills():
    """
    市場熱門觀測站 API (取得主流技能、含金量與熱門職缺)
    ---
    tags:
      - AI 職缺分析
    responses:
      200:
        description: 成功回傳 Top 5 需求技能、高薪技能與熱門職稱
    """
    connection.ping(reconnect=True)
    with connection.cursor() as cursor:
        # 需求量最高技能 Top 5 (市場主流)
        cursor.execute(
            """
            SELECT s.skill_name, COUNT(m.job_id) AS demand_count
            FROM skills s
            JOIN job_skills_mapping m ON s.skill_id = m.skill_id
            GROUP BY s.skill_id, s.skill_name
            ORDER BY demand_count DESC
            LIMIT 5;
        """
        )
        top_demand_skills = cursor.fetchall()

        # 含金量最高技能 Top 5 (談薪武器)
        cursor.execute(
            """
            SELECT s.skill_name, ROUND(AVG((j.min_salary + j.max_salary) / 2)) AS avg_salary
            FROM skills s
            JOIN job_skills_mapping m ON s.skill_id = m.skill_id
            JOIN jobs j ON m.job_id = j.job_id
            WHERE j.min_salary IS NOT NULL AND j.max_salary IS NOT NULL
            GROUP BY s.skill_id, s.skill_name
            HAVING COUNT(j.job_id) >= 10
            ORDER BY avg_salary DESC
            LIMIT 5;
        """
        )
        top_salary_skills = cursor.fetchall()

        # 開缺最多的熱門職稱 Top 5
        cursor.execute(
            """
            SELECT job_title, COUNT(job_id) AS opening_count
            FROM jobs
            WHERE job_title IS NOT NULL
            GROUP BY job_title
            ORDER BY opening_count DESC
            LIMIT 5;
        """
        )
        top_job_titles = cursor.fetchall()

    return jsonify(
        {
            "top_demand_skills": top_demand_skills,
            "top_salary_skills": top_salary_skills,
            "top_job_titles": top_job_titles,
        }
    )

if __name__ == "__main__":
    app.run(port=3939, debug=True)