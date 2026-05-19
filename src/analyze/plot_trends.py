import os
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pymysql

def generate_trend_charts():
    output_image_path1 = "./data/ai_agent_lang_trend.png"
    output_image_path2 = "./data/ai_agent_share_pie.png"
    output_image_path3 = "./data/ai_agent_activity_vs_ai.png"
    output_image_path4 = "./data/ai_agent_lang_growth_index.png"

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
    df = df.sort_values(by=["date", "primary_language"])
    os.makedirs("./data", exist_ok=True)

    # --- Chart 1: Language commit share (%) over time ---
    monthly = df.groupby(["date", "primary_language"])["total_commits"].sum().reset_index()
    monthly_total = monthly.groupby("date")["total_commits"].sum().rename("month_total")
    monthly = monthly.join(monthly_total, on="date")
    monthly["share"] = monthly["total_commits"] / monthly["month_total"] * 100

    # Top 8 languages by total commit volume
    lang_volume = monthly.groupby("primary_language")["total_commits"].sum()
    top_langs = lang_volume.nlargest(8).index.tolist()
    plot_df = monthly[monthly["primary_language"].isin(top_langs)]

    fig, ax = plt.subplots(figsize=(14, 6))
    for lang in top_langs:
        lang_df = plot_df[plot_df["primary_language"] == lang].sort_values("date")
        ax.plot(lang_df["date"], lang_df["share"], marker="o", label=lang, linewidth=2, markersize=4)

    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=6))
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    plt.xticks(rotation=45, ha="right")
    ax.set_xlabel("Timeline (Year-Month)", fontsize=12)
    ax.set_ylabel("Commit Share (%)", fontsize=12)
    ax.set_title("Language Commit Share Trend (2022 - 2026)", fontsize=14)
    ax.legend(title="Language", bbox_to_anchor=(1.01, 1), loc='upper left')
    ax.grid(True, linestyle="--", alpha=0.6)
    plt.tight_layout()
    plt.savefig(output_image_path1, bbox_inches="tight")
    plt.close()
    print(f"[Chart 1] Saved: {output_image_path1}")

    # --- Chart 2: AI repo language distribution pie ---
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

    # --- Chart 3: Scatter — commit activity (Hive/MySQL) vs AI adoption (BigQuery/GitHub API) ---
    activity = df.groupby("primary_language")["total_commits"].sum().reset_index()
    activity.columns = ["primary_language", "total_commits"]

    ai_adopt = lang_csv.groupby("primary_language")["ai_pr_count"].sum().reset_index()
    ai_adopt.columns = ["primary_language", "ai_pr_count"]

    merged = activity.merge(ai_adopt, on="primary_language", how="inner")
    merged = merged[(merged["total_commits"] > 0) & (merged["ai_pr_count"] > 0)]

    if not merged.empty:
        fig, ax = plt.subplots(figsize=(10, 7))
        ax.scatter(merged["total_commits"], merged["ai_pr_count"], s=90, color="steelblue", zorder=3)
        for _, row in merged.iterrows():
            ax.annotate(row["primary_language"],
                        xy=(row["total_commits"], row["ai_pr_count"]),
                        xytext=(5, 5), textcoords="offset points", fontsize=9)
        ax.set_xlabel("Total Commits — GH Archive (Hive Aggregated)", fontsize=11)
        ax.set_ylabel("AI-related PR Count — BigQuery / GitHub API", fontsize=11)
        ax.set_title("Language Activity vs AI Adoption", fontsize=14)
        ax.grid(True, linestyle="--", alpha=0.6)
        plt.tight_layout()
        plt.savefig(output_image_path3, bbox_inches="tight")
        plt.close()
        print(f"[Chart 3] Saved: {output_image_path3}")
    else:
        print("[Chart 3] No overlapping languages between datasets. Skipping.")

    # --- Chart 4: Language growth index (base = first available month = 100) ---
    pivot = monthly.pivot(index="date", columns="primary_language", values="share").sort_index()
    # Use languages that appear in the top 8 of Chart 1
    pivot = pivot[top_langs]
    # Divide each column by its first non-null value to get growth index
    base = pivot.apply(lambda col: col.dropna().iloc[0] if col.dropna().size > 0 else 1)
    index_df = (pivot / base * 100).dropna(how="all")

    fig, ax = plt.subplots(figsize=(14, 6))
    for lang in top_langs:
        if lang in index_df.columns:
            series = index_df[lang].dropna()
            ax.plot(series.index, series.values, marker="o", label=lang, linewidth=2, markersize=4)

    ax.axhline(100, color="gray", linestyle="--", linewidth=1, alpha=0.7)
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=6))
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    plt.xticks(rotation=45, ha="right")
    ax.set_xlabel("Timeline (Year-Month)", fontsize=12)
    ax.set_ylabel("Growth Index (Base = 100 at first month)", fontsize=12)
    ax.set_title("Language Commit Share Growth Index (2022 - 2026)", fontsize=14)
    ax.legend(title="Language", bbox_to_anchor=(1.01, 1), loc='upper left')
    ax.grid(True, linestyle="--", alpha=0.6)
    plt.tight_layout()
    plt.savefig(output_image_path4, bbox_inches="tight")
    plt.close()
    print(f"[Chart 4] Saved: {output_image_path4}")

if __name__ == "__main__":
    generate_trend_charts()
