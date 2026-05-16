-- 1. 정제 데이터 적재를 위한 외부 테이블 생성
CREATE EXTERNAL TABLE IF NOT EXISTS default.github_enriched (
    repo_name STRING,
    event_id STRING,
    event_type STRING,
    head_sha STRING,
    created_at STRING,
    commit_message STRING,
    author_email STRING,
    primary_language STRING
)
ROW FORMAT DELIMITED
FIELDS TERMINATED BY ','
STORED AS TEXTFILE
LOCATION '/user/maria_dev/processed';

-- 2. 연월별 AI 에이전트 커밋 비중 집계 및 로컬 파일 저장
INSERT OVERWRITE LOCAL DIRECTORY './data/summary'
ROW FORMAT DELIMITED
FIELDS TERMINATED BY ','
SELECT 
    SUBSTR(created_at, 1, 4) AS year,
    SUBSTR(created_at, 6, 2) AS month,
    COUNT(1) AS total_commits,
    COUNT(DISTINCT repo_name) AS unique_repos,
    SUM(CASE 
        WHEN LOWER(commit_message) LIKE '%claude%' 
          OR LOWER(commit_message) LIKE '%copilot%'
          OR LOWER(commit_message) LIKE '%codex%'
          OR LOWER(commit_message) LIKE '%openclaw%'
          OR LOWER(author_email) LIKE '%anthropic%'
        THEN 1 ELSE 0 END) AS ai_commits
FROM default.github_enriched
WHERE primary_language IS NOT NULL AND primary_language != 'Unknown'
GROUP BY SUBSTR(created_at, 1, 4), SUBSTR(created_at, 6, 2)
ORDER BY year, month;