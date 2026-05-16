# -*- coding: utf-8 -*-
import os
import sys
import glob
from pyspark.sql import SparkSession
from pyspark.sql.functions import col

# 환경 변수가 없을 때만 폴백 처리
if 'PYSPARK_PYTHON' not in os.environ:
    os.environ['PYSPARK_PYTHON'] = sys.executable
if 'PYSPARK_DRIVER_PYTHON' not in os.environ:
    os.environ['PYSPARK_DRIVER_PYTHON'] = sys.executable

def create_spark_session():
    return (SparkSession.builder
            .appName("MJU-BDP-AI-Agent-Tracker")
            .config("spark.sql.session.timeZone", "UTC")
            .config("spark.python.worker.timeout", "120")
            .config("spark.python.worker.reuse", "true")
            .config("spark.driver.host", "127.0.0.1")
            .getOrCreate())

def run_spark_etl():
    spark = create_spark_session()

    raw_dir = "./data/raw"
    # output_path에 file:// 로컬 절대 경로 명시
    output_path = f"file://{os.path.abspath('./data/processed')}"

    # 1. Raw 데이터 로드 및 경로 보정
    local_raw_files = glob.glob(os.path.join(raw_dir, "*.json.gz"))
    if not local_raw_files:
        print("입력 데이터가 없습니다. 수집기를 먼저 실행하세요.")
        spark.stop()
        return

    # Spark가 HDFS가 아닌 로컬 디스크를 조준하도록 file:// 절대 경로 리스트 빌드
    raw_files = [f"file://{os.path.abspath(f)}" for f in local_raw_files]

    print(f"압축 파일 {len(raw_files)}개 로드 중...")
    raw_df = spark.read.json(raw_files)

    # 2. PushEvent 필터링
    push_df = raw_df.filter(col("type") == "PushEvent") \
                    .select(
                        col("id").alias("event_id"),
                        col("type").alias("event_type"),
                        col("repo.name").alias("repo_name"),
                        col("payload.head").alias("head_sha"),
                        col("created_at")
                    )

    # 3. 메타데이터 로드 및 경로 보정
    local_metadata_files = glob.glob("./data/metadata_master_*.json")
    if not local_metadata_files:
        print("메타데이터 파일이 존재하지 않아 빈 데이터프레임을 생성합니다.")
        meta_df = spark.createDataFrame([], schema="repo_name STRING, head_sha STRING, commit_message STRING, author_email STRING, primary_language STRING")
    else:
        # 메타데이터 읽기 경로도 file:// 로컬 절대 경로 명시
        metadata_files = [f"file://{os.path.abspath(f)}" for f in local_metadata_files]
        print(f"메타데이터 파일 로드 중: {metadata_files}")
        meta_df = spark.read.option("multiLine", "true").json(metadata_files) \
                       .select("repo_name", "commit_message", "author_email", "primary_language")

    # 4. JOIN
    enriched_df = push_df.join(meta_df, on="repo_name", how="left_outer")

    # 5. 결과 확인 및 저장
    try:
        enriched_df.filter(col("commit_message").isNotNull()).show(5, truncate=False)
    except Exception as e:
        print(f"show() 실행 중 오류: {e}")

    try:
        print(f"결과 저장 중: {output_path}")
        enriched_df.write.mode("overwrite").csv(output_path, header=True)
        print("저장 완료")
    except Exception as e:
        print(f"파일 저장 실패: {e}")

    spark.stop()

if __name__ == "__main__":
    run_spark_etl()
