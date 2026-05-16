# 🗂️ Data Source & Schema Definition

본 디렉토리는 **GH Archive**로부터 수집된 오픈소스 타임라인 Raw 데이터의 출처, 샘플링 전략, 그리고 역사적 스키마 변경점(Schema Evolution)을 정의합니다. 
*주의: 대용량의 raw 데이터 파일(`*.json.gz`, `*.json`)은 프로젝트 루트의 `.gitignore` 설정에 의해 원격 저장소(GitHub) 커밋 대상에서 강제 제외됩니다.*

---

## 1. 데이터 출처 및 수집 전략 (Data Source & Sampling)

* **데이터 출처:** GH Archive ([data.gharchive.org](https://data.gharchive.org/))
* **데이터 성격:** GitHub API 공식 이벤트 스트림 아카이브 (매시간 단위 압축 백업)
* **샘플링 전략:** * **기간:** 2022년 1월 ~ 2026년 5월 (총 50여 개월)
    * **주기:** 매월 2일 15:00 UTC (한국 시간 기준 3일 자정)
    * **이유:** 신년/연휴 및 매월 초에 발생하는 개발 활동량의 노이즈(이상치)를 회피하고 트렌드의 일관성을 확보하기 위해 '2회차 일자' 데이터를 고정 샘플링함.

---

## 2. 깃허브 API 변경에 따른 스키마 이원화 (Schema Evolution)

본 프로젝트가 타겟으로 삼는 `PushEvent`는 **2025년 10월 7일 GitHub 본사의 Events API 경량화 패치**를 기점으로 데이터 구조가 완전히 이원화되었습니다. 분석 파이프라인(Spark ETL) 설계 시 이 점을 반드시 반영해야 합니다.

| 파싱 필드 경로 | 2025년 9월 이전 (황금기 데이터) | 2025년 10월 이후 ~ 2026년 현재 |
| :--- | :--- | :--- |
| `$.type` | `PushEvent` (정상 식별) | `PushEvent` (정상 식별) |
| `$.repo.name` | `owner/repo` (존재) | `owner/repo` (존재) |
| `$.payload.head` | `9b6500e...` (최신 커밋 SHA) | `202c546...` (최신 커밋 SHA) |
| **`$.payload.commits`** | **있음 (배열 구조)** <br>└─ `message`, `author.email` 포함 | **없음 (필드 유실)** <br>└─ 데이터 다이어트로 전격 삭제됨 |

---

## 3. 핵심 필드 상세 스키마 (Target Field Specification)

Spark 파이프라인에서 추출 및 정제하여 Hive 데이터 웨어하우스로 적재할 핵심 스키마 정의입니다.

### 1) 공통 메타데이터 (Common Execution Layer)
* **`id`** (String): 이벤트 고유 ID (예: `"19549810927"`)
* **`type`** (String): 이벤트 타입. 파이프라인 가동 시 `PushEvent`만 필터링하는 1차 인덱스로 활용.
* **`repo.name`** (String): `가장 핵심적인 결합 Key`. 중복 제거(Dedup) 후 주 언어(Language) 정보를 획득하기 위해 GitHub REST API 호출 시 사용.
* **`created_at`** (String): 이벤트 생성 타임스탬프 (ISO 8601 포맷: `YYYY-MM-DDTHH:MM:SSZ`). Hive 데이터 웨어하우스의 `year`, `month` 파티션 분할 기준으로 사용.

### 2) 페이로드 데이터 (Payload Content Layer)
* **`payload.head`** (String): 해당 푸시 이벤트의 최신 커밋 SHA 해시값. **2025년 10월 이후 데이터 복원을 위한 필수 식별자**이며, GitHub REST API 커밋 조회 엔드포인트(`GET /repos/{owner}/{repo}/commits/{head_sha}`)와 연동됨.
* **`payload.commits`** (Array[Object] / *2025년 9월 이전 한정*):
    * `commits[*].message` (String): 커밋 메시지 본문. AI 에이전트의 흔적인 정규표현식 컨벤션(`chore(claude):` 등) 및 트레일러 탐지 대상.
    * `commits[*].author.email` (String): 개발자 이메일. `noreply@anthropic.com` 등 AI 도메인 직접 매칭용.

---

## 4. 데이터 적재 디렉토리 구조 (Local Pipeline Directory)

```text
data/
├── README.md               # [현재 파일] 데이터 사양서
└── raw/                    # 수집 스크립트 실행 시 수집되는 공간 (.gitignore 대상)
    ├── 2022-01-02-15.json.gz
    ├── 2022-02-02-15.json.gz
    └── ...
    └── 2026-05