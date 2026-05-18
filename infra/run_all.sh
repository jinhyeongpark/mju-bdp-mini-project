#!/bin/bash
# 전체 데이터 파이프라인 통합 실행 스크립트

set -e

export LANG=en_US.UTF-8
export LC_ALL=en_US.UTF-8
export PYTHONIOENCODING=utf-8

echo "Starting data pipeline process..."

# 1. Raw 데이터 수집 (GH Archive) - 로컬 적재
# echo "Executing data ingestion..."
# python3.6 src/ingest/collect_gharchive.py

# 2. 외부 메타데이터 보강 (GitHub REST API) - 로컬 적재
# echo "Executing metadata enrichment..."
# python3.6 src/ingest/fetch_metadata.py

# 3. 분산 정제 및 조인 (Apache Spark Job) - 로컬 읽기 / 로컬 쓰기
# echo "Executing Spark ETL processing via spark-submit..."

# export PYSPARK_PYTHON=/usr/bin/python3.6
# export PYSPARK_DRIVER_PYTHON=/usr/bin/python3.6

# spark-submit --master local[*] src/pipeline/spark_etl.py

# 4. HDFS 데이터 적재 (스파크 정제 결과물을 하둡으로 업로드)
echo "Checking HDFS environment and uploading processed data..."
if command -v hdfs &> /dev/null
then
    echo "HDFS detected. Verifying processed data..."
    
    # 정제 결과 폴더가 비어있거나 존재하지 않는지 체크
    if [ -z "$(ls -A ./data/processed/ 2>/dev/null)" ]; then
        echo "Error: No processed data found in ./data/processed/. Spark ETL may have skipped writing."
        exit 1
    fi
    
    echo "Uploading data to HDFS..."
    hdfs dfs -mkdir -p /user/maria_dev/processed
    hdfs dfs -put -f ./data/processed/* /user/maria_dev/processed/
    echo "HDFS data upload completed."
else
    echo "Warning: Hadoop/HDFS command not found. Skipping HDFS upload (Local simulation mode)."
fi

# 5. 데이터 웨어하우스 적재 및 시계열 집계 (Apache Hive) - HDFS 데이터 읽기 / 로컬 summary 쓰기
echo "Executing Hive analysis..."

if command -v hdfs &> /dev/null
then
    hdfs dfs -chmod -R 777 /user/maria_dev/processed
fi

if command -v hive &> /dev/null
then
    hive -f src/analyze/hive_analysis.hql
else
    echo "Warning: Hive command not found. Skipping Hive execution."
fi

echo "Executing Sqoop pipeline to RDBMS..."
chmod +x src/analyze/export_to_rdbms.sh
./src/analyze/export_to_rdbms.sh

# 6. 최종 데이터 시각화 차트 생성 - 로컬 summary 읽기
echo "Generating trend visualization chart..."
python3.6 src/analyze/plot_trends.py

echo "Pipeline process completed successfully."
