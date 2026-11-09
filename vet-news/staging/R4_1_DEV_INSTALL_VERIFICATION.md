# 닥터펫 3번 → 1번 / R4.1 DEV 설치·검증 결과 (2026-11-08 KST)

## 1. 변경된 실제 상태 (R4 기존 인계서보다 최신)
- Supabase **부모**: `clgpzcjmchuingefjqfy` / **개발 브랜치** `doctorpet-v1-dev`: `mabvxdcpmfdzrqlgkxqn` — `list_branches(parent)`에서 확인.
- **새 API만 설치됨**: `doctorpet-vet-news-public-safe-v1` v1, ACTIVE, `verify_jwt=false` (공개 조회용이지만 아래 코드 차단 적용).
- Supabase 배포 소스 지문 (ezbr SHA256): `3d5295ca990197fc171be51502d40023448bbdc0382726067d163d3fe45ccfa1`.
- 이 PR의 `doctorpet-vet-news-public-safe-v1.ts`는 **배포 후 서버에서 재조회한 동일한 소스**로 갱신.
- 새 API의 `COMPILE_TIME_RELEASE_ENABLED = false`가 **코드에 고정되어 있어**, 환경변수 `DPN_NEWS_RSS_METADATA_PUBLIC_OK=true`라도 기사 행 조회·반환으로 진입하지 않음. 별도 소스 코드 변경·권리 심사·승인 없이는 공개 전환 불가.
- DB 스키마·테이블·cron·수집기·Storage·공용 뉴스 홈페이지·GitHub `main`·Production **변경하지 않음**.
- 기존 `doctorpet-vet-news-release-data`는 v3 / ezbr `7558510249879a8d72f3a648e37ec1a5e86b2a36d1611ef7ddd6f1c5a0b086dc` 그대로 유지.

## 2. 검증 범위와 제한
- 실제 Supabase `get_edge_function`으로 배포 상태 ACTIVE, 버전, 코드의 하드 OFF·비공개 trial SELECT 금지·원문 사진 URL 미반환 구조를 **재조회 확인**.
- 로컬 TypeScript → JavaScript 실행 테스트 (Node.js + TypeScript transpile, `Deno.serve` 래핑): 6/6 PASS
  1. 허용 Origin GET: 200 / `REVIEW_PENDING` / `items:[]`
  2. Origin 없는 GET: 200 / 빈 기사
  3. 미허용 Origin: 403
  4. 허용 Origin OPTIONS: 204
  5. POST: 405
  6. 잘못된 경로: 404
- 테스트에서 환경변수를 **의도적으로 true로 고정**했지만 컴파일 시 OFF 단락 평가되어 환경변수 조회 **0회**, DB 연결 **0회**.
- R4 프런트의 기존 에뮬레이터/가상 데이터 4화면 검수는 이미 PASS. 201개 가상 기사와 사진 100칸을 **실제 기사/사진 공개로 보고하지 않음**.
- **실제 DEV 공개 URL HTTP 응답의 외부 호출은 검증하지 못함**: 작업 컨테이너 DNS 불가, 웹 읽기 도구의 해당 URL 접근 실패. 서버 코드 재조회/로컬 실행과 실제 HTTP 응답은 별개. 실제 PC/휴대폰 브라우저 검수가 남아 있음.

## 3. 읽기 전용 실제 DB 재조회
- `FEED_DAILYGAEWON` 보관 64건, `REF_DAILYVET` 비공개 시험 23건, `REF_HAPPYPET` 비공개 시험 2건 (신규 수집 아님, 변경 없음).
- 사진 URL 저장 17건은 **공개·사용 허락/화면 표시 17건이 아님**. 보관물 삭제·변경 0.
- 팜인사이트는 요청·수집·표시 금지; 뉴스1 해피펫 신규 요청 금지; 데일리벳 최신 실행본·DB 계약 확인 및 별도 전환 지시 전 수집 요청·claim 금지.

## 4. 1번 공용 화면 접합 전의 **필수 차단 게이트**
1. **기존 공개 API v3는 여전히 비공개 시험 기록과 원문 사진 URL을 응답할 수 있는 SQL 경로가 존재**한다. `verify_jwt=false`이며 코드상 해당 경로의 기사별 권리 확인이 없음. 이 함수는 아직 미수정이므로 단순히 신규 API를 설치했다고 해결되지 않음. 공개 중인 기존 소비자 목록 및 요청 로그를 조회해 **소유자와 협의한 최소 안전 차단 패치·복구본**이 필요하다.
2. 1번의 최신 GitHub `vet-news/index.html`/공용 032 정본·같은 시점 복구본 대조. 기존 `main` blob (`vet-news/index.html`) `d670e5d3fe1afe98072aca8b00718598acb2960d`였으나, 접합 직전 다시 확인.
3. 새 R4 UI를 소비하는 경우에는 *구 API 폴백 금지*; 서버에서 기사 권리 승인 후에만 코드 단계 `COMPILE_TIME_RELEASE_ENABLED` 변경 및 추가 심사. `DPN_NEWS_RSS_METADATA_PUBLIC_OK`를 단독 변경해도 기사 공개 불가.
4. PC·휴대폰 실기기에서 네트워크 응답(허용/불허 Origin, 빈 기사·권리 상태)와 검색·100건 페이지·원문 링크·화면 겹침 테스트. 현재 실제 공개 기사/사진 **0건**.
5. 기사 사진·본문·소개글 공개는 이용 조건 확인 전 계속 보류. 기사 제목/링크의 상업적 사용도 저작권/계약 검토 전 공개 자동 재개 금지.
6. 본 PR은 **Draft**로 유지, 1번의 공용 페이지 직접 병합/운영 배포/생산 DB 변경 금지.

## 5. 복구
- 신규 API v1 설치는 기존 API·화면에 연결되지 않은 독립 엔드포인트. 이상 발생 시 새 함수 URL 사용 중단 / 승인 코드 스위치 OFF 유지. 기존 서비스 원본을 교체하지 않았기 때문에 DB 롤백 불필요.
- 기존 API v3는 **현재 취약 경로가 남아 있는 별도 보안 작업**. 이 PR을 병합했다고 차단 완료로 보고하지 않는다.
