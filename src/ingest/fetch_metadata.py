import os
import re
import gzip
import json
import time
import random
import requests
from collections import defaultdict
from dotenv import load_dotenv

load_dotenv()
GITHUB_TOKEN = os.getenv("GITHUB_API_KEY")

HEADERS = {
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28"
}

def extract_unique_targets(raw_files):
    unique_targets = {}  # { "owner/repo": "head_sha" }

    for file_path in raw_files:
        with gzip.open(file_path, 'rb') as f:
            for line in f:
                try:
                    event = json.loads(line.decode('utf-8'))
                    if event.get("type") == "PushEvent":
                        repo_name = event["repo"]["name"]
                        head_sha = event["payload"].get("head")
                        if repo_name and head_sha:
                            unique_targets[repo_name] = head_sha
                except Exception:
                    continue

    print(f"Extracted {len(unique_targets)} unique repos")
    return unique_targets

def fetch_enrichment_data(repo_name, head_sha, repo_cache):
    commit_url = f"https://api.github.com/repos/{repo_name}/commits/{head_sha}"
    repo_url = f"https://api.github.com/repos/{repo_name}"

    result = {
        "repo_name": repo_name,
        "head_sha": head_sha,
        "commit_message": None,
        "author_email": None,
        "primary_language": "Unknown"
    }

    try:
        c_res = requests.get(commit_url, headers=HEADERS, timeout=5)
        if c_res.status_code == 200:
            c_data = c_res.json()
            result["commit_message"] = c_data["commit"]["message"]
            result["author_email"] = c_data["commit"]["author"]["email"]

        if repo_name in repo_cache:
            result["primary_language"] = repo_cache[repo_name]
        else:
            r_res = requests.get(repo_url, headers=HEADERS, timeout=5)
            if r_res.status_code == 200:
                lang = r_res.json().get("language")
                result["primary_language"] = lang if lang else "Unknown"
                repo_cache[repo_name] = result["primary_language"]

        return result
    except Exception as e:
        print(f"API error ({repo_name}): {e}")
        return None

def build_metadata_master(raw_dir="./data/raw"):
    # 파일명(예: 2026-04-02-15.json.gz)에서 연월을 추출해 월별로 그룹핑
    month_groups = defaultdict(list)
    for fname in os.listdir(raw_dir):
        if fname.endswith(".json.gz"):
            m = re.match(r'(\d{4})-(\d{2})-', fname)
            if m:
                yymm = m.group(1)[2:] + m.group(2)
                month_groups[yymm].append(os.path.join(raw_dir, fname))

    if not month_groups:
        print("No raw data. Run the collector first.")
        return

    for yymm, files in sorted(month_groups.items()):
        output_path = f"./data/metadata_master_{yymm}.json"
        if os.path.exists(output_path):
            print(f"[SKIP] Already exists: {output_path}")
            continue

        print(f"\nProcessing {yymm} ({len(files)} files)")
        targets = extract_unique_targets(files)
        if not targets:
            continue

        sample_targets = random.sample(list(targets.items()), min(100, len(targets)))
        master_data = []
        repo_cache = {}
        start_time = time.time()

        for idx, (repo_name, head_sha) in enumerate(sample_targets):
            print(f"  [{idx+1}/{len(sample_targets)}] {repo_name}")
            enriched = fetch_enrichment_data(repo_name, head_sha, repo_cache)
            if enriched:
                master_data.append(enriched)
            time.sleep(0.2)

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(master_data, f, indent=2, ensure_ascii=False)

        print(f"Saved: {output_path} ({len(master_data)} records, {time.time() - start_time:.1f}s)")

if __name__ == "__main__":
    build_metadata_master()
