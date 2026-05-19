# AI 에이전트가 오픈소스 생태계에 미친 영향 분석

**명지대학교 빅데이터프로그래밍(2026-1) 기말 프로젝트**

---

## 1. 문제 정의 (Problem Definition)

### 분석 배경

Claude, GitHub Copilot, ChatGPT 등 AI 코딩 에이전트의 급격한 보급으로, AI가 실제 오픈소스 코드에 얼마나, 어떤 방식으로 개입하고 있는지 데이터로 검증할 필요가 생겼다.

### 핵심 질문

1. **시계열 추이**: 시간 흐름에 따라 주요 언어별 GitHub 커밋 점유율은 어떻게 변화했는가?
2. **AI 레포 언어 분포**: AI 에이전트가 가담한 레포지토리는 어떤 프로그래밍 언어를 주로 사용하는가?
3. **활동량 vs AI 채택률**: 전체 GitHub 커밋 활동량이 많은 언어일수록 AI 도구도 많이 채택하는가?

### AI 에이전트 식별 전략

BigQuery의 `githubarchive.month.*` 데이터셋에서 `PullRequestEvent` 페이로드 내 아래 키워드를 포함한 레포지토리를 AI 연관 레포로 분류한다.

- PR 제목·본문·브랜치명 키워드: `claude`, `copilot`, `gpt`, `openai`, `anthropic`, `gemini`, `codex`

---

## 2. 데이터 소스 (Data Sources)

| 소스 | 내용 | 규모 |
|------|------|------|
| **GH Archive** (gharchive.org) | GitHub PushEvent 로그 (커밋 기록) | 2022–2026 월별 JSON |
| **BigQuery** `githubarchive.month.*` | PullRequestEvent 페이로드 AI 키워드 검색 | 약 500GB 스캔 / 5,000건 추출 |
| **GitHub REST API** `/repos/{owner}/{repo}/languages` | 레포지토리 주요 언어 수집 | 두 파이프라인에서 각각 활용 |

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

## 4. 파이프라인 (Pipeline)

두 개의 독립 파이프라인이 Chart 3에서 교차 조인된다.

```
[Pipeline A] GH Archive + GitHub REST API
──────────────────────────────────────────
GH Archive (월별 PushEvent JSON)
  + GitHub REST API (repo 기본정보 → primary_language)
        │
        ▼ repo_name 기준 JOIN (Apache Spark)
        ▼
HDFS 적재 → Hive 집계 (언어별·월별 total_commits)
        │
        ▼ Sqoop
        ▼
MySQL: ai_agent_lang_trends
  → Chart 1 (언어 점유율 추이)
  → Chart 4 (언어 성장 지수)


[Pipeline B] BigQuery + GitHub REST API
──────────────────────────────────────────
BigQuery (PullRequestEvent AI 키워드 검색)
  → ai_repos_raw.csv (AI 가담 레포 5,000건)
        │
        ▼ GitHub REST API (언어 수집)
        ▼
data/ai_repos_with_lang.csv
  → Chart 2 (AI 레포 언어 분포 파이)


[Cross-Pipeline JOIN] Chart 3
──────────────────────────────
MySQL.ai_agent_lang_trends (Pipeline A)
  × ai_repos_with_lang.csv (Pipeline B)
  → primary_language 기준 조인
  → Chart 3 (활동량 vs AI 채택률 산점도)
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

### 전체 파이프라인 실행 (HDP Sandbox)

```bash
bash infra/run_all.sh
```

---

## 6. 결과물

| 파일 | 데이터 소스 | 내용 |
|------|------------|------|
| `data/ai_repos_with_lang.csv` | BigQuery + GitHub API | AI 가담 레포 5,000건 + 주요 언어 |
| `data/ai_agent_lang_trend.png` | GH Archive + GitHub API (Pipeline A) | 언어별 월간 커밋 점유율 추이 |
| `data/ai_agent_share_pie.png` | BigQuery + GitHub API (Pipeline B) | AI 레포 언어 점유율 파이 차트 |
| `data/ai_agent_activity_vs_ai.png` | Pipeline A × Pipeline B (조인) | 언어별 활동량 vs AI 채택률 산점도 |
| `data/ai_agent_lang_growth_index.png` | GH Archive + GitHub API (Pipeline A) | 언어별 커밋 점유율 성장 지수 |
