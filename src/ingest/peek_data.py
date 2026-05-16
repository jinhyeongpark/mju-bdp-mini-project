import gzip
import json

file_path = "./data/raw/2022-01-01-15.json.gz"

with gzip.open(file_path, 'rb') as f:
    for line in f:
        event_data = json.loads(line.decode('utf-8'))
        if event_data.get("type") == "PushEvent":
            print(json.dumps(event_data, indent=2, ensure_ascii=False))
            break
