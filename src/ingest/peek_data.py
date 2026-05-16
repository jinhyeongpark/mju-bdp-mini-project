import gzip
import json

file_path = "./data/raw/2022-01-02-15.json.gz"

print("[INFO] PushEvent 샘플 탐색 중...")

with gzip.open(file_path, 'rb') as f:
    for line in f:
        event_data = json.loads(line.decode('utf-8'))
        
        if event_data.get("type") == "PushEvent":
            print("[SUCCESS] PushEvent 발견! 구조를 출력합니다.\n")
            print(json.dumps(event_data, indent=2, ensure_ascii=False))
            break