# Data Directory

본 디렉토리는 파이프라인이 생성하는 데이터 파일의 출처, 수집 전략, 스키마를 정의합니다.

대용량 raw 데이터(`*.json.gz`, `*.json`)와 중간 산출물(`*.csv` 대부분)은 `.gitignore`에 의해 커밋 대상에서 제외됩니다. Git에 포함되는 파일은 아래 목록을 참고하세요.

---

## 1. Git 추적 파일 목록

| 파일 | 출처 | 설명 |
|------|------|------|
| `ai_repos_raw.csv` | BigQuery | AI 가담 레포 5,000건 (`repo_name`, `ai_pr_count`) |
| `ai_repos_with_lang.csv` | BigQuery + GitHub API | `ai_repos_raw.csv`에 주요 언어 컬럼 추가 |
| `ai_agent_lang_trend.png` | GH Archive + GitHub API → Hive → MySQL | 언어별 월간 커밋 점유율 추이 차트 |
| `ai_agent_share_pie.png` | BigQuery + GitHub API | AI 레포 언어 점유율 파이 차트 |
| `ai_agent_activity_vs_ai.png` | MySQL × CSV 조인 | 언어별 활동량 vs AI 채택률 산점도 |
| `ai_agent_lang_growth_index.png` | GH Archive + GitHub API → Hive → MySQL | 언어별 커밋 점유율 성장 지수 차트 |

---

## 2. 데이터 소스별 상세

### [A] GH Archive

- **출처**: [data.gharchive.org](https://data.gharchive.org/)
- **형식**: 시간 단위 압축 JSON (`YYYY-MM-DD-HH.json.gz`)
- **수집 기간**: 2022년 1월 ~ 2026년 5월 (50개월)
- **샘플링**: 매월 2일 15:00 UTC 고정 — 신년·연휴 노이즈 회피 목적
- **사용 이벤트**: `PushEvent` (`repo.name`, `payload.head`, `created_at`)
- **수집 스크립트**: `src/ingest/collect_gharchive.py`

#### PushEvent 스키마 변경 이력

2025년 10월 GitHub Events API 경량화 이후 `payload.commits` 배열이 제거되었습니다.

| 필드 | 2025년 9월 이전 | 2025년 10월 이후 |
|------|----------------|----------------|
| `payload.head` | 존재 | 존재 |
| `payload.commits[].message` | 존재 | **제거됨** |
| `payload.commits[].author.email` | 존재 | **제거됨** |

→ 커밋 메시지·이메일은 `payload.head` SHA로 GitHub REST API를 통해 별도 수집

---

### [B] GitHub REST API

두 곳에서 독립적으로 사용됩니다.

**Pipeline A (GH Archive 보강)**
- 엔드포인트: `GET /repos/{owner}/{repo}/commits/{sha}`
- 목적: PushEvent의 `head_sha`로 커밋 메시지·author email 수집
- 엔드포인트: `GET /repos/{owner}/{repo}`
- 목적: 레포의 `primary_language` 수집
- 스크립트: `src/ingest/fetch_metadata.py`

**Pipeline B (AI 레포 언어 수집)**
- 엔드포인트: `GET /repos/{owner}/{repo}/languages`
- 목적: `ai_repos_raw.csv` 레포 5,000건의 주요 언어 확정 (바이트 기준 상위 언어 중 TARGET_LANGUAGES 첫 번째 매칭)
- 스크립트: `src/analyze/fetch_repo_languages.py`

---

### [C] BigQuery (`githubarchive.month.*`)

- **목적**: `PullRequestEvent` 페이로드에서 AI 관련 키워드를 포함한 레포 추출
- **키워드**: `claude`, `copilot`, `gpt`, `openai`, `anthropic`, `gemini`, `codex`
- **방식**: BigQuery 콘솔에서 `githubarchive.month.*` 테이블을 대상으로 PullRequestEvent 필터링 후 `repo_name`, `ai_pr_count` 집계 (약 500GB 스캔)
- **출력**: `data/ai_repos_raw.csv` (5,000건)

---

## 3. 파이프라인 흐름 요약

```
[Pipeline A]
GH Archive (PushEvent)
  + GitHub API (commit message, primary_language)
  → Spark ETL (repo_name 기준 JOIN)
  → HDFS → Hive (언어별·월별 집계)
  → Sqoop → MySQL: ai_agent_lang_trends

[Pipeline B]
BigQuery (PullRequestEvent, AI 키워드)
  → ai_repos_raw.csv
  + GitHub API (languages endpoint)
  → ai_repos_with_lang.csv

[Chart 3 조인]
MySQL.ai_agent_lang_trends (Pipeline A)
  × ai_repos_with_lang.csv (Pipeline B)
  → primary_language 기준 조인
```

---

## 4. TARGET_LANGUAGES

두 파이프라인 모두 아래 14개 언어를 기준으로 필터링합니다.

```
Python, JavaScript, TypeScript, Java, Go,
C#, Kotlin, Swift, PHP, Shell,
Ruby, Rust, C++, Dart
```

---

## 5. 디렉토리 구조

```
data/
├── README.md                       # 본 파일
├── ai_repos_raw.csv                # BigQuery 추출 결과 (Git 추적)
├── ai_repos_with_lang.csv          # 언어 수집 완료본 (Git 추적)
├── *.png                           # 생성된 차트 (Git 추적)
├── raw/                            # GH Archive 원본 (.gitignore)
│   ├── 2022-01-02-15.json.gz
│   └── ...
├── processed/                      # Spark ETL 출력 (.gitignore)
└── summary/                        # Hive 집계 결과 (.gitignore)
```
