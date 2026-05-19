import os
import time
import pandas as pd
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from dotenv import load_dotenv

load_dotenv()
GITHUB_TOKEN = os.getenv("GITHUB_API_KEY")

HEADERS = {
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28"
}

INPUT_CSV = "./data/ai_repos_raw.csv"
OUTPUT_CSV = "./data/ai_repos_with_lang.csv"
TOP_N = 5000

TARGET_LANGUAGES = {
    "Python", "JavaScript", "TypeScript", "Java", "Go",
    "C#", "Kotlin", "Swift", "PHP", "Shell",
    "Ruby", "Rust", "C++", "Dart"
}

def get_languages_breakdown(repo_name):
    """레포의 전체 언어 목록을 바이트 수와 함께 반환."""
    url = f"https://api.github.com/repos/{repo_name}/languages"
    for _ in range(3):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=10)
            if resp.status_code == 200:
                return resp.json()
            if resp.status_code == 429:
                time.sleep(60)
                continue
            return {}
        except Exception:
            return {}
    return {}

def fetch_language(repo_name):
    url = f"https://api.github.com/repos/{repo_name}"
    for _ in range(3):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=10)
            if resp.status_code == 200:
                primary = resp.json().get("language") or ""
                if primary in TARGET_LANGUAGES:
                    return primary
                # primary가 목표 언어가 아니면 전체 언어 분포에서 찾기
                breakdown = get_languages_breakdown(repo_name)
                for lang, _ in sorted(breakdown.items(), key=lambda x: x[1], reverse=True):
                    if lang in TARGET_LANGUAGES:
                        return lang
                return "Other"
            if resp.status_code == 429:
                time.sleep(60)
                continue
            return "Other"
        except Exception:
            return "Other"
    return "Other"

def main():
    df = pd.read_csv(INPUT_CSV).head(TOP_N)
    print(f"Processing {len(df)} repos...")

    results = {}
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {
            executor.submit(fetch_language, row.repo_name): i
            for i, row in enumerate(df.itertuples(), 1)
        }
        for future in as_completed(futures):
            i = futures[future]
            results[i] = future.result()
            if i % 200 == 0:
                print(f"[{i}/{len(df)}] done")

    df["primary_language"] = [results[i] for i in range(1, len(df) + 1)]
    os.makedirs("./data", exist_ok=True)
    df.to_csv(OUTPUT_CSV, index=False)
    print(f"\nSaved: {OUTPUT_CSV}")

if __name__ == "__main__":
    main()
