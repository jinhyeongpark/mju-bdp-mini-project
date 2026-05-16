import os
import time
import requests
from datetime import datetime

def download_monthly_samples():
    """
    2022년부터 2026년 현재(5월)까지 매월 2일 15시(UTC)의 GH Archive 데이터를
    자동으로 순회하며 스트리밍 방식으로 다운로드합니다.
    """
    target_dir = "./data/raw"
    if not os.path.exists(target_dir):
        os.makedirs(target_dir)

    current_year = 2026
    current_month = 5  # 2026년 5월 기말고사 시점 기준
    target_hour = "15" # UTC 15시 (한국 시간 자정)
    target_day = "02"  # 신년/휴일 노이즈 회피를 위한 2일 고정

    print("==================================================")
    print("🚀 GH Archive 매월 2일 샘플링 파이프라인 가동")
    print("==================================================")

    for year in range(2022, current_year + 1):
        # 2026년은 현재 월(5월)까지만 돌고, 나머지는 12월까지 순회
        end_month = current_month if year == current_year else 12
        
        for month in range(1, end_month + 1):
            month_str = f"{month:02d}"
            file_name = f"{year}-{month_str}-{target_day}-{target_hour}.json.gz"
            url = f"https://data.gharchive.org/{file_name}"
            output_path = os.path.join(target_dir, file_name)

            # 이미 다운로드한 파일이 있다면 스킵 (네트워크 비용 절감 및 멱등성 보장)
            if os.path.exists(output_path):
                print(f"[SKIP] 이미 존재하는 파일입니다: {file_name}")
                continue

            print(f"[INGEST] 다운로드 중... ➔ {file_name}")
            try:
                with requests.get(url, stream=True, timeout=30) as response:
                    if response.status_code == 200:
                        with open(output_path, 'wb') as f:
                            for chunk in response.iter_content(chunk_size=1024 * 1024):
                                if chunk:
                                    f.write(chunk)
                        print(f"[SUCCESS] 적재 완료: {file_name}")
                        # 깃허브 아카이브 서버 디도스 방지 및 안정적인 수집을 위한 미세 딜레이
                        time.sleep(0.5)
                    else:
                        print(f"[WARN] 데이터를 찾을 수 없습니다 (HTTP {response.status_code}): {file_name}")
            except Exception as e:
                print(f"[ERROR] {file_name} 수집 중 장애 발생: {e}")

    print("\n[FINISHED] 모든 시점의 Raw 데이터 수집 작업이 완료되었습니다!")

if __name__ == "__main__":
    download_monthly_samples()