# -*- coding: utf-8 -*-
import os
import sys
import glob
from pyspark.sql import SparkSession
from pyspark.sql.functions import col

# 윈도우 및 가상 인프라 환경에서 워커가 현재 파이썬을 사용하도록 강제 설정
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
    # [수정] 결과 저장 경로를 HDFS가 아닌 로컬 절대 경로로 명시
    output_path = f"file://{os.path.abspath('./data/processed')}"

    # 1. Raw 데이터 로드 구간 보정
    # 수집 폴더 내 파일 존재 여부는 기존 로컬 glob으로 체크하되
    local_raw_files = glob.glob(os.path.join(raw_dir, "*.json.gz"))
    if not local_raw_files:
        print("입력 데이터가 없습니다. 수집기를 먼저 실행하세요.")
        spark.stop()
        return

    # [수정] Spark 전용 네이티브 와일드카드 절대 경로 문자열 1줄로 생성
    raw_wildcard_path = f"file://{os.path.abspath(raw_dir)}/*.json.gz"
    print(f"압축 파일 {len(local_raw_files)}개 로드 중 (타겟 경로: {raw_wildcard_path})...")
    raw_df = spark.read.json(raw_wildcard_path)

    # 2. PushEvent 필터링
    push_df = raw_df.filter(col("type") == "PushEvent") \
                    .select(
                        col("id").alias("event_id"),
                        col("type").alias("event_type"),
                        col("repo.name").alias("repo_name"),
                        col("payload.head").alias("head_sha"),
                        col("created_at")
                    )

    # 3. 메타데이터 로드 구간 보정
    local_metadata_files = glob.glob("./data/metadata_master_*.json")
    if not local_metadata_files:
        print("메타데이터 파일이 존재하지 않아 빈 데이터프레임을 생성합니다.")
        meta_df = spark.createDataFrame([], schema="repo_name STRING, head_sha STRING, commit_message STRING, author_email STRING, primary_language STRING")
    else:
        # [수정] 메타데이터 로드도 Spark 전용 네이티브 와일드카드 절대 경로 문자열로 처리
        meta_wildcard_path = f"file://{os.path.abspath('./data')}/metadata_master_*.json"
        print(f"메타데이터 파일 로드 중: {meta_wildcard_path}")
        meta_df = spark.read.option("multiLine", "true").json(meta_wildcard_path) \
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
        enriched_df.write.mode("overwrite").csv(output_path, header=True, sep='\t')
        print("저장 완료")
    except Exception as e:
        print(f"파일 저장 실패: {e}")

    spark.stop()

if __name__ == "__main__":
    run_spark_etl()
