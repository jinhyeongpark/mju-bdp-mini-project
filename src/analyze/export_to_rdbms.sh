#!/bin/bash
set -e

DB_HOST="localhost"
DB_USER="root"
DB_PASS="hadoop" 
DB_NAME="mju_analytics"
TABLE_NAME="ai_agent_lang_trends"

LOCAL_DATA_DIR="$(pwd)/data/summary"
HDFS_TEMP_DIR="/user/maria_dev/temp_summary"

echo "=== [Sqoop Pipeline] Start exporting data to RDBMS ==="

mysql -h${DB_HOST} -u${DB_USER} -p${DB_PASS} -e "CREATE DATABASE IF NOT EXISTS ${DB_NAME};"

mysql -h${DB_HOST} -u${DB_USER} -p${DB_PASS} -D${DB_NAME} -e "
CREATE TABLE IF NOT EXISTS ${TABLE_NAME} (
    year VARCHAR(4) NOT NULL,
    month VARCHAR(2) NOT NULL,
    primary_language VARCHAR(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL, 
    total_commits INT,
    unique_repos INT,
    ai_commits INT,
    feat_commits INT,
    fix_commits INT,
    refactor_commits INT,
    docs_commits INT,
    chore_commits INT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (year, month, primary_language) 
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
"

mysql -h${DB_HOST} -u${DB_USER} -p${DB_PASS} -D${DB_NAME} -e "
ALTER TABLE ${TABLE_NAME}
  MODIFY COLUMN primary_language VARCHAR(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL;
"

mysql -h${DB_HOST} -u${DB_USER} -p${DB_PASS} -D${DB_NAME} -e "TRUNCATE TABLE ${TABLE_NAME};"

sed -i '/^$/d' ${LOCAL_DATA_DIR}/* 2>/dev/null || true

hdfs dfs -rm -r -f ${HDFS_TEMP_DIR}
hdfs dfs -mkdir -p ${HDFS_TEMP_DIR}
hdfs dfs -put ${LOCAL_DATA_DIR}/* ${HDFS_TEMP_DIR}/

rm -f ./${TABLE_NAME}.java ./${TABLE_NAME}.class ./${TABLE_NAME}.jar

sqoop export \
  --connect "jdbc:mysql://${DB_HOST}/${DB_NAME}?useSSL=false" \
  --username "${DB_USER}" \
  --password "${DB_PASS}" \
  --table "${TABLE_NAME}" \
  --columns "year,month,primary_language,total_commits,unique_repos,ai_commits,feat_commits,fix_commits,refactor_commits,docs_commits,chore_commits" \
  --export-dir "${HDFS_TEMP_DIR}" \
  --input-fields-terminated-by '\t' \
  --input-lines-terminated-by '\n' \
  --num-mappers 1

hdfs dfs -rm -r -f ${HDFS_TEMP_DIR}
echo "=== [Sqoop Pipeline] Data Export Successfully Completed! ==="