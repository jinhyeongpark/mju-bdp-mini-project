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
ROW FORMAT SERDE 'org.apache.hadoop.hive.serde2.OpenCSVSerde'
WITH SERDEPROPERTIES (
   "separatorChar" = ",",
   "quoteChar"     = "\""
)
STORED AS TEXTFILE
LOCATION '/user/maria_dev/processed';

WITH ai_classified_commits AS (
    SELECT
        SUBSTR(created_at, 1, 4) AS year,
        SUBSTR(created_at, 6, 2) AS month,
        primary_language,
        repo_name,
        CASE 
            WHEN LOWER(commit_message) LIKE '%claude%' 
              OR LOWER(commit_message) LIKE '%copilot%'
              OR LOWER(commit_message) LIKE '%codex%'
              OR LOWER(commit_message) LIKE '%openclaw%'
              OR LOWER(author_email) LIKE '%anthropic%'
            THEN 1 ELSE 0 
        END AS is_ai,
        CASE 
            WHEN LOWER(commit_message) LIKE '%feat%' OR LOWER(commit_message) LIKE '%add%' THEN 'feat'
            WHEN LOWER(commit_message) LIKE '%fix%' OR LOWER(commit_message) LIKE '%bug%' THEN 'fix'
            WHEN LOWER(commit_message) LIKE '%refactor%' THEN 'refactor'
            WHEN LOWER(commit_message) LIKE '%docs%' THEN 'docs'
            ELSE 'chore'
        END AS task_type
    FROM default.github_enriched
    WHERE primary_language IS NOT NULL AND primary_language != 'Unknown'
)
INSERT OVERWRITE LOCAL DIRECTORY '/home/maria_dev/mju-bdp-mini-project/data/summary'
ROW FORMAT DELIMITED
FIELDS TERMINATED BY ','
SELECT 
    year,
    month,
    primary_language,
    COUNT(1) AS total_commits,
    COUNT(DISTINCT repo_name) AS unique_repos,
    SUM(is_ai) AS ai_commits,
    SUM(CASE WHEN is_ai = 1 AND task_type = 'feat' THEN 1 ELSE 0 END) AS feat_commits,
    SUM(CASE WHEN is_ai = 1 AND task_type = 'fix' THEN 1 ELSE 0 END) AS fix_commits,
    SUM(CASE WHEN is_ai = 1 AND task_type = 'refactor' THEN 1 ELSE 0 END) AS refactor_commits,
    SUM(CASE WHEN is_ai = 1 AND task_type = 'docs' THEN 1 ELSE 0 END) AS docs_commits,
    SUM(CASE WHEN is_ai = 1 AND task_type = 'chore' THEN 1 ELSE 0 END) AS chore_commits
FROM ai_classified_commits
GROUP BY year, month, primary_language
ORDER BY year, month, ai_commits DESC;