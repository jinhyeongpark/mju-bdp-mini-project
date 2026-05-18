# 깃허브 분석 기반 AI 에이전트 시대의 개발 영향 분석

본 프로젝트는 **명지대학교 빅데이터 프로그래밍(2026-1)** 기말 프로젝트로, AI 에이전트(Claude, Copilot, OpenClaw 등)의 등장이 오픈소스 생태계의 프로그래밍 언어 선택 및 개발 프로세스 환경에 미친 영향을 엔드투엔드(End-to-End) 빅데이터 파이프라인을 통해 입체적으로 분석합니다.

---

## 1. 문제 정의 (Problem Definition)

### 분석 배경 및 핵심 질문
AI 에이전트는 단순한 자동완성 도구를 넘어 개발자의 고유 영역이었던 아키텍처 설계와 대규모 리팩토링까지 수행하는 수준으로 진화했습니다. 본 프로젝트는 대용량 오픈소스 생태계 로그 데이터를 전수 조사하여 **'AI와의 협업'이 가속화된 시점의 3가지 핵심 질문**에 답하고자 합니다.

1. **시계열 추이 분석**: 시간이 흐름에 따라 주요 프로그래밍 언어별 AI 에이전트 커밋 비중은 어떻게 변화하고 있는가?
2. **기술 스택 점유율 분석**: 전체 AI 가담 프로젝트 중 가장 압도적인 활용도를 보이는 프로그래밍 언어는 무엇인가?
3. **AI 작업 성격 분석**: AI 에이전트는 주로 어떤 성격의 작업(기능 구현, 버그 수정, 리팩토링, 문서 작성)에 집중적으로 투입되고 있는가?

### AI 에이전트 식별 전략 (AI Identification)
단순 작성자(Author) 이메일 기반 추적은 에이전트가 사용자의 로컬 Git 계정을 빌려 쓰는 경우 감지하지 못하는 한계가 있습니다. 이를 극복하기 위해 본 프로젝트는 다음과 같은 **다중 필터링 식별 전략**을 파이프라인에 주입합니다.

* **Commit Trailer 추적**: 커밋 본문의 `Co-Authored-By: .* <noreply@anthropic.com>` 등의 메타데이터 추적
* **Commit Scope 키워드 매칭**: 커밋 메시지 내부 및 작성자 이메일 도메인 내 `claude`, `copilot`, `codex`, `openclaw`, `anthropic` 매칭

---

## 2. 시스템 아키텍처 (System Architecture)

데이터의 수집(Ingestion), 분산 처리(Processing), 데이터 웨어하우징(DW), 서비스 서빙(Serving), 시각화(Visualization) 계층이 유기적으로 연결된 자동화 데이터 파이프라인 아키텍처입니다.

```text
[ Data Source ]        GH Archive API (JSON 시계열 데이터 수집)
      │
      ▼
[ Ingestion ]          Python / Bash 자동화 스크립트 기반 로컬 적재
      │
      ▼
[   Storage   ]        HDFS (분산 파일 시스템 파일 업로드 / 로컬 백업)
      │
      ▼
[ Processing  ]        Apache Spark (대용량 JSON 파싱 및 RegEx 기반 AI 식별)
      │
      ▼
[ DW / Master ]        Apache Hive (OpenCSVSerde 파싱 최적화, CTE 기반 다차원 집계 연산)
      │
      ▼
[ Data Transfer]       Apache Sqoop (HDFS 분산 통계 데이터를 RDBMS로 고속 전송)
      │
      ▼
[ Serving DB  ]        MySQL RDBMS (Serving용 마스터 테이블 구축 - 복합 PK 설계)
      │
      ▼
[Visualization]        Python (PyMySQL + Matplotlib를 활용한 3대 핵심 지표 차트 생성)