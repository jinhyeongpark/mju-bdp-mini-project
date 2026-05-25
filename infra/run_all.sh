#!/bin/bash
# 전체 데이터 파이프라인 통합 실행 스크립트

set -e

export LANG=en_US.UTF-8
export LC_ALL=en_US.UTF-8
export PYTHONIOENCODING=utf-8

echo "Starting data pipeline process..."

# 1. Pipeline B - GH Archive PR 데이터 수집 (raw_pr/)
echo "Downloading GH Archive PR raw files..."
python3.6 src/ingest/collect_ai_pr_raw.py

# 2. Pipeline B - Spark로 AI 키워드 PR 추출 → ai_repos_raw.csv
echo "Extracting AI repos from PR data via Spark..."
export PYSPARK_PYTHON=/usr/bin/python3.6
export PYSPARK_DRIVER_PYTHON=/usr/bin/python3.6
spark-submit --master local[*] src/pipeline/spark_ai_pr_etl.py

# 3. Pipeline B - GitHub API로 AI 레포 언어 수집 - ai_repos_with_lang.csv 존재 시 SKIP
echo "Fetching repository languages from GitHub API..."
python3.6 src/analyze/fetch_repo_languages.py

# 4. Pipeline A - Raw 데이터 수집 (GH Archive) - 파일별 SKIP 로직 내장
echo "Collecting GH Archive raw data..."
python3.6 src/ingest/collect_gharchive.py

# 5. Pipeline A - 외부 메타데이터 보강 (GitHub REST API) - 월별 SKIP 로직 내장
echo "Enriching metadata via GitHub API..."
python3.6 src/ingest/fetch_metadata.py

# 6. Pipeline A - 분산 정제 및 조인 (Apache Spark Job) - processed/ 존재 시 SKIP
export PYSPARK_PYTHON=/usr/bin/python3.6
export PYSPARK_DRIVER_PYTHON=/usr/bin/python3.6

if [ -z "$(ls -A ./data/processed/ 2>/dev/null)" ]; then
    echo "Executing Spark ETL processing..."
    spark-submit --master local[*] src/pipeline/spark_etl.py
else
    echo "[SKIP] Spark ETL: data/processed/ already exists."
fi

# 7. Pipeline A - HDFS 데이터 적재 (스파크 정제 결과물을 하둡으로 업로드)
if command -v hdfs &> /dev/null
then
    if [ -z "$(ls -A ./data/processed/ 2>/dev/null)" ]; then
        echo "Error: No processed data found in ./data/processed/. Spark ETL may have skipped writing."
        exit 1
    fi

    if hdfs dfs -test -e /user/maria_dev/processed 2>/dev/null; then
        echo "[SKIP] HDFS: /user/maria_dev/processed already exists."
    else
        echo "Uploading data to HDFS..."
        hdfs dfs -mkdir -p /user/maria_dev/processed
        hdfs dfs -put ./data/processed/* /user/maria_dev/processed/
        echo "HDFS data upload completed."
    fi
else
    echo "Warning: Hadoop/HDFS command not found. Skipping HDFS upload (Local simulation mode)."
fi

# 8. Pipeline A - 데이터 웨어하우스 적재 및 시계열 집계 (Apache Hive)
if command -v hive &> /dev/null
then
    if [ -n "$(ls -A ./data/summary/ 2>/dev/null)" ]; then
        echo "[SKIP] Hive: data/summary/ already exists."
    else
        echo "Executing Hive analysis..."
        if command -v hdfs &> /dev/null; then
            hdfs dfs -chmod -R 777 /user/maria_dev/processed
            hdfs dfs -rm -r -f /tmp/ai_project_summary || true
        fi
        hive -f src/analyze/hive_analysis.hql
        echo "Downloading Hive results from HDFS to local data/summary directory..."
        mkdir -p ./data/summary
        hdfs dfs -get /tmp/ai_project_summary/* ./data/summary/
    fi
else
    echo "Warning: Hive command not found. Skipping Hive execution."
fi

# 9. Pipeline A - Sqoop → MySQL
chmod +x src/analyze/export_to_rdbms.sh
SQOOP_ROWS=$(mysql -hlocalhost -uroot -phadoop -Dmju_analytics \
    -se "SELECT COUNT(*) FROM ai_agent_lang_trends;" 2>/dev/null || echo "0")
if [ "$SQOOP_ROWS" -gt "0" ]; then
    echo "[SKIP] Sqoop: MySQL table already has ${SQOOP_ROWS} rows."
else
    echo "Executing Sqoop pipeline to RDBMS..."
    ./src/analyze/export_to_rdbms.sh
fi

# 10. 최종 데이터 시각화 차트 생성 - 차트 4종 모두 존재 시 SKIP
echo "Generating trend visualization charts..."
python3.6 -m pip install pymysql --quiet 2>/dev/null || true
PYTHONIOENCODING=utf-8 python3.6 src/analyze/plot_trends.py

echo "Pipeline process completed successfully."
