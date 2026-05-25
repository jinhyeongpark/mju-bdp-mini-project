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
    output_path = f"file://{os.path.abspath('./data/processed')}"

    local_raw_files = glob.glob(os.path.join(raw_dir, "*.json.gz"))
    if not local_raw_files:
        print("No input data. Run the collector first.")
        spark.stop()
        return

    raw_wildcard_path = f"file://{os.path.abspath(raw_dir)}/*.json.gz"
    print(f"Loading {len(local_raw_files)} compressed files from {raw_wildcard_path}...")
    raw_df = spark.read.json(raw_wildcard_path)
    push_df = raw_df.filter(col("type") == "PushEvent") \
                    .select(
                        col("id").alias("event_id"),
                        col("type").alias("event_type"),
                        col("repo.name").alias("repo_name"),
                        col("payload.head").alias("head_sha"),
                        col("created_at")
                    )

    local_metadata_files = glob.glob("./data/metadata_master_*.json")
    if not local_metadata_files:
        print("No metadata files found. Using empty dataframe.")
        meta_df = spark.createDataFrame([], schema="repo_name STRING, head_sha STRING, commit_message STRING, author_email STRING, primary_language STRING")
    else:
        meta_wildcard_path = f"file://{os.path.abspath('./data')}/metadata_master_*.json"
        print(f"Loading metadata: {meta_wildcard_path}")
        meta_df = spark.read.option("multiLine", "true").json(meta_wildcard_path) \
                       .select("repo_name", "commit_message", "author_email", "primary_language")

    # JOIN
    enriched_df = push_df.join(meta_df, on="repo_name", how="left_outer")

    # 결과 확인 및 저장
    try:
        enriched_df.filter(col("commit_message").isNotNull()).show(5, truncate=False)
    except Exception as e:
        print(f"show() error: {e}")

    try:
        print(f"Saving results to: {output_path}")
        enriched_df.write.mode("overwrite").csv(output_path, header=True, sep='\t')
        print("Save complete")
    except Exception as e:
        print(f"Save failed: {e}")

    spark.stop()

if __name__ == "__main__":
    run_spark_etl()
