import os
import pandas as pd
import matplotlib.pyplot as plt
import pymysql

def generate_trend_charts():
    """
    MySQL RDBMS에서 실제 데이터를 조회하여 과제 요건 충족을 위한 3가지 차트를 생성합니다.
    1) 월별 주요 언어별 AI 커밋 비중 추이 (다중 선 그래프)
    2) 전체 AI 커밋 중 언어별 점유율 비중 (파이 차트)
    3) AI 에이전트의 주요 작업 성격별 분포 (막대 그래프) -> 과제 질문 3번 해결책
    """
    output_image_path1 = "./data/ai_agent_lang_trend.png"
    output_image_path2 = "./data/ai_agent_share_pie.png"
    output_image_path3 = "./data/ai_agent_task_type.png" 
    
    db_host = "localhost"
    db_user = "root"
    db_pass = "hadoop"
    db_name = "mju_analytics"
    table_name = "ai_agent_lang_trends"
    
    print("MySQL RDBMS로부터 실데이터 조회를 시작합니다...")
    
    conn = pymysql.connect(host=db_host, user=db_user, password=db_pass, database=db_name, charset='utf8mb4')
    query = f"SELECT * FROM {table_name}" 
    df = pd.read_sql(query, conn)
    conn.close()
    
    if df.empty:
        raise ValueError(f"에러: MySQL {table_name} 테이블에 데이터가 없습니다.")

    df["date"] = df["year"].astype(str) + "-" + df["month"].astype(str).str.zfill(2)
    df["ai_ratio"] = (df["ai_commits"] / df["total_commits"]) * 100
    df = df.sort_values(by=["date", "primary_language"])
    os.makedirs("./data", exist_ok=True)

    all_dates = sorted(df["date"].unique())
    tick_dates = all_dates[::6]  # 6개월 간격으로 샘플링

    plt.figure(figsize=(14, 6))
    languages = df["primary_language"].unique()
    for lang in languages:
        lang_df = df[df["primary_language"] == lang].sort_values("date")
        plt.plot(lang_df["date"], lang_df["total_commits"], marker="o", label=lang, linewidth=2, markersize=4)
    plt.title("Commit Trend by Language (2022 - 2026)", fontsize=14, pad=15)
    plt.xlabel("Timeline (Year-Month)", fontsize=12)
    plt.ylabel("Total Commits", fontsize=12)
    plt.xticks(ticks=tick_dates, labels=tick_dates, rotation=45, ha="right")
    plt.grid(True, linestyle="--", alpha=0.6)
    plt.legend(title="Programming Languages", bbox_to_anchor=(1.05, 1), loc='upper left')
    plt.tight_layout()
    plt.savefig(output_image_path1)
    plt.close()
    print(f"[시각화 1] 완료: {output_image_path1}")

    plt.figure(figsize=(8, 8))
    lang_csv = pd.read_csv("./data/ai_repos_with_lang.csv")
    lang_summary = lang_csv.groupby("primary_language")["ai_pr_count"].sum().reset_index()
    lang_summary = lang_summary[lang_summary["ai_pr_count"] > 0]
    if not lang_summary.empty:
        plt.pie(lang_summary["ai_pr_count"], labels=lang_summary["primary_language"], autopct='%1.1f%%', startangle=140, colors=plt.cm.Paired.colors)
        plt.title("AI Repository Language Distribution (GitHub API)", fontsize=14, pad=15)
        plt.tight_layout()
        plt.savefig(output_image_path2)
        plt.close()
        print(f"[시각화 2] 완료: {output_image_path2}")

    plt.figure(figsize=(10, 6))
    
    task_types = {
        "Feature (기능개발)": df["feat_commits"].sum(),
        "Bug Fix (버그수정)": df["fix_commits"].sum(),
        "Refactoring (코드정제)": df["refactor_commits"].sum(),
        "Documentation (문서)": df["docs_commits"].sum(),
        "Chore/Others (기타)": df["chore_commits"].sum()
    }
    
    task_df = pd.DataFrame(list(task_types.items()), columns=["Task Type", "Count"]).sort_values(by="Count", ascending=False)
    
    bars = plt.bar(task_df["Task Type"], task_df["Count"], color=plt.cm.Accent.colors[:len(task_df)])
    
    for bar in bars:
        yval = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2.0, yval + (yval*0.01), f'{int(yval):,}', ha='center', va='bottom', fontsize=10, weight='bold')

    plt.title("Distribution of AI Agent Commit Task Types", fontsize=14, pad=15)
    plt.xlabel("Task Characteristics", fontsize=12)
    plt.ylabel("Number of Commits", fontsize=12)
    plt.grid(True, axis='y', linestyle="--", alpha=0.6)
    plt.tight_layout()
    plt.savefig(output_image_path3)
    plt.close()
    print(f"[시각화 3] 완료: {output_image_path3}")

if __name__ == "__main__":
    generate_trend_charts()