# AI 에이전트가 오픈소스 생태계에 미친 영향 분석

**명지대학교 빅데이터프로그래밍(2026-1) 기말 프로젝트**

---

## 1. 문제 정의 (Problem Definition)

### 분석 배경

Claude, GitHub Copilot, ChatGPT 등 AI 코딩 에이전트의 급격한 보급으로, AI가 실제 오픈소스 코드에 얼마나, 어떤 방식으로 개입하고 있는지 데이터로 검증할 필요가 생겼다.

### 핵심 질문

1. **언어 점유율**: AI 에이전트가 가담한 레포지토리는 어떤 프로그래밍 언어를 주로 사용하는가?
2. **시계열 추이**: 시간 흐름에 따라 주요 언어별 GitHub 커밋 수는 어떻게 변화하는가?
3. **작업 유형 분포**: AI 에이전트는 주로 어떤 성격의 작업(기능 구현, 버그 수정, 리팩토링 등)에 투입되는가?

### AI 에이전트 식별 전략

BigQuery의 `githubarchive.month.*` 데이터셋에서 `PullRequestEvent` 페이로드 내 아래 키워드를 포함한 레포지토리를 AI 연관 레포로 분류한다.

- PR 제목·본문·브랜치명 키워드: `claude`, `copilot`, `gpt`, `openai`, `anthropic`, `gemini`, `codex`

---

## 2. 데이터 (Data Sources)

| 소스 | 내용 | 규모 |
|------|------|------|
| **GH Archive** (gharchive.org) | GitHub PushEvent 로그 (커밋 기록) | 2022–2026 월별 JSON |
| **BigQuery** `githubarchive.month.*` | PullRequestEvent 페이로드 AI 키워드 검색 | 약 500GB 스캔 / 5,000건 추출 |
| **GitHub REST API** | 레포지토리 기본 정보 (primary_language) | 5,000건 API 호출 |

---

## 3. 기술 스택 (Tech Stack)

| 계층 | 도구 |
|------|------|
| 데이터 수집 | Python (requests), GH Archive, GitHub API |
| 빅데이터 쿼리 | Google BigQuery |
| 분산 스토리지 | Apache HDFS (Hadoop) |
| 분산 처리 | Apache Spark (PySpark) |
| 데이터 웨어하우스 | Apache Hive (HQL) |
| RDBMS 적재 | Apache Sqoop → MySQL |
| 시각화 | Python (Matplotlib, PyMySQL) |
| 인프라 | GCP VM, HDP Sandbox (Docker) |

---

## 4. 구현 계획 (Pipeline)

```
[BigQuery]
  PullRequestEvent 페이로드 AI 키워드 검색
  → repo_name + ai_pr_count (5,000건 CSV)
        │
        ▼
[GitHub REST API]
  레포별 primary_language 수집
  → data/ai_repos_with_lang.csv
        │
        ▼
[HDFS]
  ai_repos_with_lang.csv 업로드
        │
        ▼
[GH Archive + Python]
  월별 PushEvent JSON 수집 → 로컬 적재
        │
        ▼
[Apache Spark]
  JSON 파싱 + AI 키워드 필터링 + 메타데이터 조인
  → HDFS (탭 구분자 CSV)
        │
        ▼
[Apache Hive]
  외부 테이블 생성 + 언어별·월별 집계
        │
        ▼
[Apache Sqoop]
  Hive 집계 결과 → MySQL 전송
        │
        ▼
[Python Matplotlib]
  차트 1: 언어별 월간 커밋 추이 (선 그래프)
  차트 2: AI 가담 레포 언어 점유율 (파이 차트)
  차트 3: AI 에이전트 작업 유형 분포 (막대 그래프)
```

---

## 5. 실행 방법

### 사전 준비

```bash
# GitHub API 토큰 설정 (.env 파일)
GITHUB_API_KEY=ghp_xxxx

# Python 의존성
pip install pandas requests python-dotenv pymysql matplotlib
```

### GitHub API로 언어 수집

```bash
python src/analyze/fetch_repo_languages.py
```

### 전체 파이프라인 실행 (HDP Sandbox)

```bash
# Spark ETL
export PYSPARK_PYTHON=/usr/bin/python3.6
spark-submit --master local[*] src/pipeline/spark_etl.py

# Hive → Sqoop → MySQL → 시각화
bash infra/run_all.sh
```

---

## 6. 결과물

| 파일 | 내용 |
|------|------|
| `data/ai_repos_with_lang.csv` | AI 가담 레포 5,000건 + 주요 언어 |
| `data/ai_agent_lang_trend.png` | 언어별 커밋 추이 차트 |
| `data/ai_agent_share_pie.png` | AI 레포 언어 점유율 파이 차트 |
| `data/ai_agent_activity_vs_ai.png` | 언어별 커밋 활동량 vs AI 채택률 산점도 |
