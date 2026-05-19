# Data Directory

대용량 raw 데이터(`*.json.gz`)와 중간 산출물은 `.gitignore`에 의해 커밋 대상에서 제외됩니다.

---

## 데이터 소스

### GH Archive

- **출처**: [data.gharchive.org](https://data.gharchive.org/)
- **수집 기간**: 2022년 1월 ~ 2026년 5월 (50개월)
- **샘플링**: 매월 2일 15:00 UTC 고정 — 신년·연휴 노이즈 회피 목적
- **사용 이벤트**: `PushEvent`
- **수집 스크립트**: `src/ingest/collect_gharchive.py`

**PushEvent 주요 필드**

| 필드 | 타입 | 설명 |
|------|------|------|
| `id` | String | 이벤트 고유 ID |
| `repo.name` | String | `owner/repo` 형식, GitHub API 연동 키 |
| `payload.head` | String | 최신 커밋 SHA |
| `created_at` | String | ISO 8601 타임스탬프, Hive 집계 시 year/month 추출 기준 |

**스키마 변경 이력**: 2025년 10월 GitHub Events API 경량화 이후 `payload.commits` 배열 제거됨

| 필드 | ~2025년 9월 | 2025년 10월~ |
|------|------------|-------------|
| `payload.commits[].message` | 존재 | **제거됨** |
| `payload.commits[].author.email` | 존재 | **제거됨** |

→ 커밋 메시지·이메일은 `payload.head` SHA로 GitHub API를 통해 별도 수집 (`src/ingest/fetch_metadata.py`)

---

### GitHub REST API

**커밋 메타데이터 수집** (`src/ingest/fetch_metadata.py`)

- `GET /repos/{owner}/{repo}/commits/{sha}` → 커밋 메시지, author email
- `GET /repos/{owner}/{repo}` → primary_language
- GH Archive PushEvent의 `repo.name` + `payload.head` 를 키로 사용

**AI 레포 언어 수집** (`src/analyze/fetch_repo_languages.py`)

- `GET /repos/{owner}/{repo}/languages` → 언어별 바이트 수 반환
- TARGET_LANGUAGES 중 바이트 수 1위 언어를 primary_language로 확정
- 대상: `ai_repos_raw.csv` 5,000건

---

### BigQuery (`githubarchive.month.*`)

- `PullRequestEvent` 페이로드에서 AI 관련 키워드 포함 레포를 집계
- 키워드: `claude`, `copilot`, `gpt`, `openai`, `anthropic`, `gemini`, `codex`
- BigQuery 콘솔에서 직접 실행 (약 500GB 스캔), 결과를 `ai_repos_raw.csv`로 저장
- 컬럼: `repo_name`, `ai_pr_count`

---

## TARGET_LANGUAGES

두 파이프라인 모두 아래 14개 언어 기준으로 필터링합니다.

```
Python, JavaScript, TypeScript, Java, Go,
C#, Kotlin, Swift, PHP, Shell,
Ruby, Rust, C++, Dart
```

---

## 디렉토리 구조

```
data/
├── README.md                    # 본 파일
├── ai_repos_raw.csv             # BigQuery 추출 결과 (Git 추적)
├── ai_repos_with_lang.csv       # 언어 수집 완료본 (Git 추적)
├── raw/                         # GH Archive 원본 (.gitignore)
├── processed/                   # Spark ETL 출력 (.gitignore)
└── summary/                     # Hive 집계 결과 (.gitignore)
```
