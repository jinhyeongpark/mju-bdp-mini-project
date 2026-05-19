import os
import time
import requests
from datetime import datetime

def download_monthly_samples():
    target_dir = "./data/raw"
    if not os.path.exists(target_dir):
        os.makedirs(target_dir)

    current_year = 2026
    current_month = 5  # 2026년 5월 기말고사 시점 기준
    target_hour = "15" # UTC 15시 (한국 시간 자정)
    target_day = "02"  # 신년/휴일 노이즈 회피를 위한 2일 고정

    for year in range(2022, current_year + 1):
        # 2026년은 현재 월(5월)까지만 돌고, 나머지는 12월까지 순회
        end_month = current_month if year == current_year else 12
        
        for month in range(1, end_month + 1):
            month_str = f"{month:02d}"
            file_name = f"{year}-{month_str}-{target_day}-{target_hour}.json.gz"
            url = f"https://data.gharchive.org/{file_name}"
            output_path = os.path.join(target_dir, file_name)

            if os.path.exists(output_path):
                print(f"[SKIP] Already exists: {file_name}")
                continue

            print(f"Downloading: {file_name}")
            try:
                with requests.get(url, stream=True, timeout=30) as response:
                    if response.status_code == 200:
                        with open(output_path, 'wb') as f:
                            for chunk in response.iter_content(chunk_size=1024 * 1024):
                                if chunk:
                                    f.write(chunk)
                        print(f"Done: {file_name}")
                        time.sleep(0.5)
                    else:
                        print(f"[WARN] Not found (HTTP {response.status_code}): {file_name}")
            except Exception as e:
                print(f"[ERROR] Failed to fetch {file_name}: {e}")

    print("Collection complete")

if __name__ == "__main__":
    download_monthly_samples()
