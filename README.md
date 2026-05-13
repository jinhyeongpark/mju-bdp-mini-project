# 깃허브 분석 기반 AI 에이전트 시대의 개발 영향 분석

본 프로젝트는 **명지대학교 빅데이터 프로그래밍(2026-1)** 기말 프로젝트로, AI 에이전트(Claude)의 등장이 오픈소스 생태계의 언어 및 기술 스택 선택에 미친 영향을 빅데이터 파이프라인을 통해 분석합니다.

---

## 1. 문제 정의 (Problem Definition)

### 분석 배경
AI 에이전트(Claude, Copilot 등)는 단순 도구와 페어 프로그래머를 넘어 새로운 업무 방식으로 자리 잡았습니다. 특히 에이전트가 코드를 생성하기 유리한 언어나 프레임워크(Python, TypeScript, NestJS 등)의 채택률 변화가 관찰되고 있습니다. 본 프로젝트는 **'AI와의 협업'**이 실제 오픈소스 생태계를 어떻게 바꾸고 있는지 데이터를 통해 분석합니다.

### Claude 감지 전략 (AI Identification)
단순한 작성자(Author) 매핑은 에이전트가 유저의 계정 설정을 빌려 쓰는 경우를 놓칠 수 있습니다. 따라서 본 프로젝트는 다음과 같은 **다중 필터링 정규표현식(RegEx)**을 통해 Claude의 활동을 정밀하게 식별합니다.

1.  **Commit Trailer 탐지:** 커밋 본문의 `Co-Authored-By: .* <noreply@anthropic.com>` 메타데이터 추적.
2.  **Commit Scope 분석:** Conventional Commits 패턴 중 `chore(claude):`, `feat(claude):`, `docs(claude):` 등 작업 범위 명시 확인.

---

## 2. 기술 스택 (Technical Stack)

| 분류 | 기술 도구 | 역할 |
| :--- | :--- | :--- |
| **Ingestion** | **Python, Bash** | GH Archive API 호출 및 주기적 데이터 샘플링 수집 자동화 |
| **Storage** | **HDFS** | 분산 파일 시스템 기반의 대용량 JSON Raw Data 적재 |
| **Processing** | **Apache Spark** | RegEx 기반 Claude 흔적 필터링 및 GitHub API 연동 메타데이터 보강(ETL) |
| **DW / Analyze** | **Apache Hive** | 분석용 데이터 웨어하우스 구축 및 시간대별/언어별 집계 분석 |
| **Visualization** | **Python (Seaborn)** | 일반 개발자 vs Claude 협업 프로젝트의 기술 스택 전후 비교 시각화 |

---

## 3. 구현 계획 (Implementation Plan)

데이터 수집부터 인사이트 도출까지 총 5단계의 자동화된 파이프라인으로 구성됩니다.

### Step 1: 데이터 수집 (Data Ingestion)
* Python 스크립트를 사용하여 `data.gharchive.org`에서 2022~2026년 기간의 시계열 데이터를 샘플링하여 수집합니다.
* 수집된 JSON 파일을 HDFS의 `/user/maria_dev/raw/` 경로로 적재하는 과정을 Shell 스크립트로 자동화합니다.

### Step 2: 클로드 흔적 필터링 (AI Identification)
* **Spark(PySpark)**를 활용하여 대용량 로그를 전수 조사합니다.
* 커밋 메시지 내 이메일 도메인(`@anthropic.com`)과 스코프 키워드(`claude`)를 매칭하여 AI 가담 이벤트를 분류합니다.

### Step 3: 메타데이터 보강 (Dynamic Enrichment)
* 식별된 레포지토리 리스트를 바탕으로 **GitHub REST API**를 호출하여 해당 프로젝트의 '주 언어(Primary Language)' 정보를 확보합니다.
* API 호출 최적화를 위해 로컬 캐싱(Cache-Aside) 전략을 도입하여 중복 호출을 방지하고 Rate Limit을 관리합니다.

### Step 4: 하이브 웨어하우스 구축 (Analysis)
* 정제된 데이터를 Hive 테이블로 로드하고, `year`, `month` 단위로 **Partitioning**을 적용하여 쿼리 성능을 최적화합니다.
* "Claude 가담 프로젝트의 언어 비중"과 "전체 프로젝트의 언어 비중"을 시계열로 비교하는 HiveQL을 수행합니다.

### Step 5: 결과 도출 (Visualization)
* 분석된 지표를 바탕으로 AI 에이전트 도입 전후의 언어별 성장률(Growth Rate)을 시각화하여 최종 리포트를 완성합니다.
