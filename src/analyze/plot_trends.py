import os
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pymysql

def generate_trend_charts():
    output_image_path1 = "./data/ai_agent_lang_trend.png"
    output_image_path2 = "./data/ai_agent_share_pie.png"
    output_image_path3 = "./data/ai_agent_task_type.png"

    db_host = "localhost"
    db_user = "root"
    db_pass = "hadoop"
    db_name = "mju_analytics"
    table_name = "ai_agent_lang_trends"

    print("Querying MySQL RDBMS...")

    conn = pymysql.connect(host=db_host, user=db_user, password=db_pass, database=db_name, charset='utf8mb4')
    query = f"SELECT * FROM {table_name}"
    df = pd.read_sql(query, conn)
    conn.close()

    if df.empty:
        raise ValueError(f"No data in MySQL table: {table_name}")

    TARGET_LANGUAGES = {"Python", "JavaScript", "TypeScript", "Java", "Go",
                        "C#", "Kotlin", "Swift", "PHP", "Shell",
                        "Ruby", "Rust", "C++", "Dart"}
    df = df[df["primary_language"].isin(TARGET_LANGUAGES)]

    df["date"] = pd.to_datetime(
        df["year"].astype(str) + "-" + df["month"].astype(str).str.zfill(2) + "-01"
    )
    df["ai_ratio"] = (df["ai_commits"] / df["total_commits"]) * 100
    df = df.sort_values(by=["date", "primary_language"])
    os.makedirs("./data", exist_ok=True)

    fig, ax = plt.subplots(figsize=(14, 6))
    languages = df["primary_language"].unique()
    for lang in languages:
        lang_df = df[df["primary_language"] == lang].sort_values("date")
        ax.plot(lang_df["date"], lang_df["total_commits"], marker="o", label=lang, linewidth=2, markersize=4)
    ax.set_title("Commit Trend by Language (2022 - 2026)", fontsize=14, pad=15)
    ax.set_xlabel("Timeline (Year-Month)", fontsize=12)
    ax.set_ylabel("Total Commits", fontsize=12)
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=6))
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    plt.xticks(rotation=45, ha="right")
    ax.grid(True, linestyle="--", alpha=0.6)
    ax.legend(title="Programming Languages", bbox_to_anchor=(1.05, 1), loc='upper left')
    plt.tight_layout()
    plt.savefig(output_image_path1)
    plt.close()
    print(f"[Chart 1] Saved: {output_image_path1}")

    lang_csv = pd.read_csv("./data/ai_repos_with_lang.csv")
    lang_summary = lang_csv.groupby("primary_language")["ai_pr_count"].sum().reset_index()
    lang_summary = lang_summary[lang_summary["ai_pr_count"] > 0]
    lang_summary = lang_summary.sort_values("ai_pr_count", ascending=False).reset_index(drop=True)
    if not lang_summary.empty:
        TOP_N_LANG = 8
        top = lang_summary.head(TOP_N_LANG).copy()
        others_sum = lang_summary.iloc[TOP_N_LANG:]["ai_pr_count"].sum()
        if others_sum > 0:
            top = pd.concat([top, pd.DataFrame([{"primary_language": "Others", "ai_pr_count": others_sum}])], ignore_index=True)
        total = top["ai_pr_count"].sum()
        legend_labels = [f"{row.primary_language} ({row.ai_pr_count / total * 100:.1f}%)" for _, row in top.iterrows()]
        fig, ax = plt.subplots(figsize=(10, 8))
        wedges, _ = ax.pie(top["ai_pr_count"], startangle=90, colors=plt.cm.Paired.colors[:len(top)])
        ax.legend(wedges, legend_labels, title="Language (Share)", loc="center left", bbox_to_anchor=(1, 0.5), fontsize=10)
        ax.set_title("AI Repository Language Distribution (GitHub API)", fontsize=14, pad=15)
        plt.tight_layout()
        plt.savefig(output_image_path2)
        plt.close()
        print(f"[Chart 2] Saved: {output_image_path2}")

    plt.figure(figsize=(10, 6))
    task_types = {
        "Feature": df["feat_commits"].sum(),
        "Bug Fix": df["fix_commits"].sum(),
        "Refactoring": df["refactor_commits"].sum(),
        "Documentation": df["docs_commits"].sum(),
        "Chore/Others": df["chore_commits"].sum()
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
    print(f"[Chart 3] Saved: {output_image_path3}")

if __name__ == "__main__":
    generate_trend_charts()
