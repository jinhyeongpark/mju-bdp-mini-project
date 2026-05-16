import os
import gzip
import json
import time
import requests
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()
GITHUB_TOKEN = os.getenv("GITHUB_API_KEY")

HEADERS = {
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28"
}

def extract_unique_targets(raw_dir="./data/raw"):
    """
    [로컬 시뮬레이션용] 다운로드된 json.gz 파일들을 순회하며 
    중복 없는 레포지토리명과 최신 head SHA값을 추출합니다.
    """
    unique_targets = {} # { "owner/repo": "head_sha" }
    
    if not os.path.exists(raw_dir):
        print(f"[WARN] raw 데이터 디렉토리가 없습니다: {raw_dir}")
        return unique_targets

    print("[INFO] 로컬 파일에서 API 조회 대상(PushEvent) 추출 중...")
    for file_name in os.listdir(raw_dir):
        if file_name.endswith(".json.gz"):
            file_path = os.path.join(raw_dir, file_name)
            with gzip.open(file_path, 'rb') as f:
                for line in f:
                    try:
                        event = json.loads(line.decode('utf-8'))
                        if event.get("type") == "PushEvent":
                            repo_name = event["repo"]["name"]
                            head_sha = event["payload"].get("head")
                            if repo_name and head_sha:
                                # 가장 최신 이벤트의 SHA로 갱신되도록 적재
                                unique_targets[repo_name] = head_sha
                    except Exception:
                        continue
                        
    print(f"[SUCCESS] 총 {len(unique_targets)}개의 유니크한 레포지토리 타겟 확보 완료.")
    return unique_targets

def fetch_enrichment_data(repo_name, head_sha, repo_cache):
    """
    GitHub REST API를 호출하여 커밋 메시지와 해당 레포의 주 언어를 수집합니다.
    """
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
        # 1. 커밋 메시지 및 작성자 이메일 수집 (2026년 유실 데이터 복원용)
        c_res = requests.get(commit_url, headers=HEADERS, timeout=5)
        if c_res.status_code == 200:
            c_data = c_res.json()
            result["commit_message"] = c_data["commit"]["message"]
            result["author_email"] = c_data["commit"]["author"]["email"]
            
        # 2. 레포지토리 주 언어 수집 (Cache-Aside 패턴 적용하여 API 절약)
        if repo_name in repo_cache:
            result["primary_language"] = repo_cache[repo_name]
        else:
            r_res = requests.get(repo_url, headers=HEADERS, timeout=5)
            if r_res.status_code == 200:
                r_data = r_res.json()
                lang = r_data.get("language")
                result["primary_language"] = lang if lang else "Unknown"
                # 캐시에 저장
                repo_cache[repo_name] = result["primary_language"]
                
        return result
    except Exception as e:
        print(f"[WARN] API 호출 중 에러 발생 ({repo_name}): {e}")
        return None

def build_metadata_master():
    # 1. 대상 레포/SHA 추출
    targets = extract_unique_targets()
    if not targets:
        print("[ERROR] 조회할 타겟 데이터가 없습니다. 먼저 수집기를 실행하세요.")
        return

    sample_targets = list(targets.items())[:50]
    
    master_data = []
    repo_cache = {} # 언어 정보 중복 호출 방지용 캐시 딕셔너리
    
    print(f"[START] 총 {len(sample_targets)}개 샘플 레포지토리에 대한 깃허브 API 보강 시작...")
    
    start_time = time.time()
    for idx, (repo_name, head_sha) in enumerate(sample_targets):
        print(f"🔄 [{idx+1}/{len(sample_targets)}] API 조회 중: {repo_name}")
        
        enriched = fetch_enrichment_data(repo_name, head_sha, repo_cache)
        if enriched:
            master_data = master_data + [enriched]
            
        # 디도스 오해 방지 및 API 안정성을 위한 미세 딜레이 (초당 5회 수준)
        time.sleep(0.2)
        
    # 3. 최종 결과를 깨끗한 마스터 데이터 파일로 저장
    output_path = "./data/metadata_master.json"
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(master_data, f, indent=2, ensure_ascii=False)
        
    end_time = time.time()
    print(f"메타데이터 마스터 사전 구축 완료 ({end_time - start_time:.2f}초 소요)")
    print(f"저장 경로: {output_path}")

if __name__ == "__main__":
    build_metadata_master()