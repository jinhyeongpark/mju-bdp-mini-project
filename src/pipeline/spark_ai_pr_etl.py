# -*- coding: utf-8 -*-
import os
import sys
import glob
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, lower, concat_ws, coalesce, lit, get_json_object

if 'PYSPARK_PYTHON' not in os.environ:
    os.environ['PYSPARK_PYTHON'] = sys.executable
if 'PYSPARK_DRIVER_PYTHON' not in os.environ:
    os.environ['PYSPARK_DRIVER_PYTHON'] = sys.executable

AI_PATTERN = "claude|copilot|gpt|openai|anthropic|gemini|codex"
INPUT_DIR   = "./data/raw_pr"
OUTPUT_CSV  = "./data/ai_repos_raw.csv"


def create_spark_session():
    return (SparkSession.builder
            .appName("MJU-BDP-AI-PR-Extractor")
            .config("spark.sql.session.timeZone", "UTC")
            .config("spark.python.worker.timeout", "120")
            .config("spark.python.worker.reuse", "true")
            .config("spark.driver.host", "127.0.0.1")
            .getOrCreate())


def run():
    if os.path.exists(OUTPUT_CSV):
        print("[SKIP] Already exists: %s" % OUTPUT_CSV)
        return

    local_files = glob.glob(os.path.join(INPUT_DIR, "*.json.gz"))
    if not local_files:
        print("No input files. Run collect_ai_pr_raw.py first.")
        return

    spark = create_spark_session()
    input_path = "file://%s/*.json.gz" % os.path.abspath(INPUT_DIR)
    print("Loading %d files from %s ..." % (len(local_files), input_path))

    # Read as text to avoid schema inference merging across event types
    raw_df = spark.read.text(input_path)

    pr_df = (raw_df
             .filter(get_json_object(col("value"), "$.type") == "PullRequestEvent")
             .select(
                 get_json_object(col("value"), "$.repo.name").alias("repo_name"),
                 coalesce(get_json_object(col("value"), "$.payload.pull_request.title"), lit("")).alias("title"),
                 coalesce(get_json_object(col("value"), "$.payload.pull_request.body"),  lit("")).alias("body"),
                 coalesce(get_json_object(col("value"), "$.payload.pull_request.head.ref"), lit("")).alias("head_ref"),
             ))

    text_col = lower(concat_ws(" ", col("title"), col("body"), col("head_ref")))
    ai_df = pr_df.filter(text_col.rlike(AI_PATTERN))

    result_df = (ai_df
                 .groupBy("repo_name")
                 .count()
                 .withColumnRenamed("count", "ai_pr_count")
                 .orderBy(col("ai_pr_count").desc()))

    result_pdf = result_df.toPandas()
    os.makedirs("./data", exist_ok=True)
    result_pdf.to_csv(OUTPUT_CSV, index=False)
    print("Saved %d repos to %s" % (len(result_pdf), OUTPUT_CSV))

    spark.stop()


if __name__ == "__main__":
    run()
