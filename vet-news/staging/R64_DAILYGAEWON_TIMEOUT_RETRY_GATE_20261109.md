# 닥터펫 3번 수의계 뉴스 — R6.4 신규 장애 기록 및 안전 재시도 게이트
작성: 2026-11-09 KST | 범위: **신규 FETCH_PROCESS_TIMEOUT 1건**, 기존 R4~R6.3 합격 시험 반복 금지
상태: **읽기 전용 조사·문서화**, 실제 수집기 수정·재실행·DB/cron/공용 사이트 변경 없음

## 새로 발견한 실행 장애
- DEV: Supabase project `mabvxdcpmfdzrqlgkxqn`, source `FEED_DAILYGAEWON` (데일리개원).
- 2026-11-09 **09:50:46 KST** 시작 예약 실행의 run ID `add7a55c-d7bc-426a-a74a-1326f7046b7a`는 **PARTIAL_FAILURE**.
- 실제 결과: `{"sourceId":"FEED_DAILYGAEWON","status":"FAILED","error":"FETCH_PROCESS_TIMEOUT","httpStatus":null}` (요약). 완료 09:51:29 KST, 총 **약 42.57초**.
- 해당 소스 상태: `status=FAILED`, `paused=false`, `consecutive_failures=1`, `last_error=FETCH_PROCESS_TIMEOUT`.
- 서버가 설정한 다음 시도: **2026-11-09 15:50:48 KST** (`next_attempt_at=2026-11-09T06:50:48.034Z`). 승인 없이 앞당기기, 수동 claim, 백오프 리셋 금지.
- 직전 09:31 KST 예약은 **SUCCESS**, 피드 HTTP 304, 기존 메타데이터 50개 재처리(새 기사 50건 아님).
- 최근 24시간 예약 완료: SUCCESS **66회**, PARTIAL_FAILURE **1회**. 성공 실행 평균 32.83초, 최소 23.74초, **최대 67.88초** / 실패 42.57초. 따라서 단순히 40초 초과가 원인이라는 주장은 증거 없음.
- 관련 함수 `doctorpet_domestic_news.apply_run`의 실패 분기는 기본 6시간 보류이며 짧은 재시도는 `FETCH_NETWORK_TIMEOUT`/`FETCH_DNS_FAILURE`/`FETCH_CONNECTION_FAILURE` 등 일부 명시 오류에만 적용. `FETCH_PROCESS_TIMEOUT`은 짧은 재시도 허용 목록에 없음.
- 기존 기사 `FEED_DAILYGAEWON` **64건 보존**, 마지막 발행일 2026-11-06; 다른 private source 보관물·일시정지 유지. 조회 시점 기사 수집 `RUNNING=0`.

## 수집기 원본 위치 조사 — 아직 미확정
- 연결된 GitHub 저장소 3개 main의 파일 구조/검색 확인:
  `doctorpet-platform`, `doctorpet-original-archive`, `doctorpet-v1-dev-preview`.
- `doctorpet-platform`의 루트 트리에는 기존 admin/referral Supabase 함수와 웹 파일만 있었고 RSS writer 진입 코드는 확인되지 않음.
- `doctorpet-original-archive`는 암호화 원본 백업이며 수집 실행 코드 경로가 확인되지 않음(암호화 백업 임의 복호화 금지).
- `doctorpet-v1-dev-preview` main은 정적 뉴스 보기 코드가 중심. 3번 PR의 `r63` 파일은 **미설치 검사 후보**로 실제 실행 runner가 아님.
- DEV DB의 활성 `pg_cron` 3개는 뉴스 데일리개원 수집을 명시적으로 호출하지 않음. 외부 Dot/Work/CI/별도 예약 실행부 가능성은 있으나 **소유·경로 미확정**.
- 저장 `doctorpet_domestic_news.feeds`에는 정규화 items + SHA만 있고 원본 RSS bytes/charset가 없으므로 첫 글자 손상 발생 단계도 확정하지 못함.

## 안전한 다음 동작 — 새 작업만
1. **15:50:48 KST 이전에는 재시도/백오프·예약을 바꾸지 않음**. 기존 수집 모니터링과 중복 자동화·cron 생성 금지.
2. 다음 정상 **기존 예약 실행이 실제 발생한 이후에만**, 다음 4가지를 읽기 전용으로 한 번 확인:
   - `sources.status,paused,next_attempt_at,last_error,consecutive_failures`
   - `runs.mode,status,started_at,completed_at,results`의 **새 run ID**
   - `articles` 64건 보존 여부, 새 기사와 기존 기사 분리
   - `private_refresh_state.REF_DAILYVET.paused=true`, 비공개 실행 RUNNING=0.
3. 다음 실행이 미발생이면 상태를 `기존 예약/runner 미발견`으로 구분하여 **실제 runner 소유자/실행 로그·원본 지문 확보**를 요청. 미승인 수집 명령, 사이트 직접 반복 요청, 관리자 권한 우회 금지.
4. runner 확보 후 **FETCH_PROCESS_TIMEOUT 원인**(전체 프로세스 예산, 외부 네트워크/파서, 요청 재시도, 프로세스 종료)과 **R6.3 U+FFFD 품질검사 삽입 위치**를 분리해 진단.
5. 정식 코드 변경은 별도 정확한 원본·변경 목록·동일시점 복구본/회귀 검수 후 기존 담당자가 수행. `apply_run`을 테이블 잠금 아래 교체하거나 광범위 DB DDL 설치 금지.

## 상태 구분
- R6.2: 18660 제목을 **화면에만 정상 표시**하는 검토 후보, 실제 DEV API·브라우저 PASS.
- R6.3: 새 데이터 재발 차단 **합성 8/8 PASS** 검토 후보, collector **미연결**.
- **R6.4: 09:50 KST 신규 process timeout 발견·원인 범위 조사**, 실제 복구 아직 미확인.
- **출시/권리/실기기:** 이번 조사로 상태 변화 없음. 사진·소개글 사용 허락 및 1번 공용 접합과 구분.
