import os
import sys
import glob
from pyspark.sql import SparkSession
from pyspark.sql.functions import col

# 윈도우에서 PySpark 워커가 현재 파이썬을 사용하도록 설정
os.environ['PYSPARK_PYTHON'] = sys.executable
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
    metadata_files = glob.glob("./data/metadata_master_*.json")
    output_path = "./data/processed"

    # 1. Raw 데이터 로드
    raw_files = glob.glob(os.path.join(raw_dir, "*.json.gz"))
    if not raw_files:
        print("입력 데이터가 없습니다. 수집기를 먼저 실행하세요.")
        spark.stop()
        return

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

    # 3. 메타데이터 로드
    print(f"메타데이터 파일 로드 중: {metadata_files}")
    if not metadata_files:
        meta_df = spark.createDataFrame([], schema="repo_name STRING, head_sha STRING, commit_message STRING, author_email STRING, primary_language STRING")
    else:
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
