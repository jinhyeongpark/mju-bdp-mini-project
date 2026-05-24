import os
import time
import requests

# 2025-12 ~ 2026-05, 월 2파일 (2일·16일 15시)
START_YEAR, START_MONTH = 2025, 12
END_YEAR,   END_MONTH   = 2026, 5
TARGET_DAYS = ["02", "09", "16", "23"]
TARGET_HOUR = "15"
OUTPUT_DIR  = "./data/raw_pr"


def iter_targets():
    year, month = START_YEAR, START_MONTH
    while (year, month) <= (END_YEAR, END_MONTH):
        for day in TARGET_DAYS:
            yield year, month, day
        month += 1
        if month > 12:
            month = 1
            year += 1


def download():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    for year, month, day in iter_targets():
        fname = f"{year}-{month:02d}-{day}-{TARGET_HOUR}.json.gz"
        url   = f"https://data.gharchive.org/{fname}"
        dest  = os.path.join(OUTPUT_DIR, fname)

        if os.path.exists(dest):
            print(f"[SKIP] {fname}")
            continue

        print(f"Downloading {fname} ...")
        try:
            with requests.get(url, stream=True, timeout=30) as r:
                if r.status_code == 200:
                    with open(dest, "wb") as f:
                        for chunk in r.iter_content(chunk_size=1024 * 1024):
                            if chunk:
                                f.write(chunk)
                    print(f"  Done: {fname}")
                    time.sleep(0.5)
                else:
                    print(f"  [WARN] HTTP {r.status_code}: {fname}")
        except Exception as e:
            print(f"  [ERROR] {fname}: {e}")

    print("Download complete.")


if __name__ == "__main__":
    download()
