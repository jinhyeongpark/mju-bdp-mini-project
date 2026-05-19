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

    BREAK_LOW = 2000
    BREAK_HIGH = 3000
    max_val = df["total_commits"].max()

    fig, (ax_top, ax_bot) = plt.subplots(2, 1, figsize=(14, 8), sharex=True,
                                          gridspec_kw={"height_ratios": [1, 3], "hspace": 0.05})
    languages = df["primary_language"].unique()
    for lang in languages:
        lang_df = df[df["primary_language"] == lang].sort_values("date")
        ax_top.plot(lang_df["date"], lang_df["total_commits"], marker="o", label=lang, linewidth=2, markersize=4)
        ax_bot.plot(lang_df["date"], lang_df["total_commits"], marker="o", label=lang, linewidth=2, markersize=4)

    ax_top.set_ylim(BREAK_HIGH, max_val * 1.05)
    ax_bot.set_ylim(0, BREAK_LOW)

    ax_top.spines["bottom"].set_visible(False)
    ax_bot.spines["top"].set_visible(False)
    ax_top.tick_params(bottom=False)

    # break 사선 표시
    d = 0.015
    kwargs = dict(transform=ax_top.transAxes, color="k", clip_on=False, linewidth=1)
    ax_top.plot((-d, +d), (-d, +d), **kwargs)
    ax_top.plot((1 - d, 1 + d), (-d, +d), **kwargs)
    kwargs.update(transform=ax_bot.transAxes)
    ax_bot.plot((-d, +d), (1 - d, 1 + d), **kwargs)
    ax_bot.plot((1 - d, 1 + d), (1 - d, 1 + d), **kwargs)

    ax_top.grid(True, linestyle="--", alpha=0.6)
    ax_bot.grid(True, linestyle="--", alpha=0.6)

    ax_bot.xaxis.set_major_locator(mdates.MonthLocator(interval=6))
    ax_bot.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    plt.xticks(rotation=45, ha="right")

    ax_bot.set_xlabel("Timeline (Year-Month)", fontsize=12)
    fig.text(0.04, 0.5, "Total Commits", va="center", rotation="vertical", fontsize=12)
    fig.suptitle("Commit Trend by Language (2022 - 2026)", fontsize=14, y=1.01)

    handles, labels = ax_bot.get_legend_handles_labels()
    ax_top.legend(handles, labels, title="Programming Languages", bbox_to_anchor=(1.05, 1), loc='upper left')

    plt.tight_layout()
    plt.savefig(output_image_path1, bbox_inches="tight")
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
