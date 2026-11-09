# 3번 뉴스 전략실 → 1번 / R4.8 실제 DEV 안전 응답 브라우저 검수

검수 날짜: 2026-11-09 KST. 공용 홈페이지 접합·실기기·운영 공개: 미실시.

## 검수 실행
- GitHub Actions: https://github.com/doctorpetadmin7-maker/doctorpet-v1-dev-preview/actions/runs/42499963868
- Job ID: 128790367954, completed success.
- 검수 스크립트: vet-news/staging/doctorpet-vet-news-r48-live-browser.py
- 기존 R4.6 HTTP 및 R4.7 실응답 파서 검증도 동일 실행에서 PASS.
- **실제 DEV 안전 API의 JSON 64건을 1회 읽어** R4.5의 원본 HTML을 변경하지 않고 Playwright/Chromium `route.fulfill`로 입력한 테스트. HTML의 API 요청을 차단해 DEV 응답 JSON을 브라우저 내부에 재현했으므로 **GitHub Pages 브라우저 CORS 직접 검증과는 다름**. 실제 API HTTP/CORS는 독립된 R4.6 단계에서 검사.

## 4개 화면 PASS
- PC 1440px, 모바일 폭 390/360/320px
- 실제 데일리개원 메타데이터 64건 카드 표시, 원문 링크 host·새 탭 속성, 사진 실제 요청 0, 임의 소개글 비출력
- 데일리벳/해피펫 매체 선택 시 기사 표시 0, 검색/초기화 동작, JavaScript 오류 0, 가로 넘침 0, 외부 네트워크 요청 0.

## 데이터/수집 상태 확인
- DEV API: doctorpet-vet-news-release-data v7, 배포 소스 SHA `db78dd773b9f8984ca15bbf49fe7a404e3a4c71ac718761a23dc30a5c9752e26`.
- DEV 보관: 데일리개원 64건, 데일리벳 개인 시험 23건, 해피펫 개인 시험 2건. 이 둘은 공개 아님.
- 데일리벳 paused=true, private RUNNING=0. 팜인사이트 요청·수집·표시 금지, 해피펫 신규 요청 금지, 데일리벳 요청·claim 금지 유지.
- DEV의 최근 SCHEDULED 실행 8건이 SUCCESS로 기록됨. 데일리개원 포함 여부·신규 저장 건수는 실행별 세부 결과 대조가 필요. 최신 보관기사 발행일은 11월 6일로, 새로운 기사 수집 성공을 주장하지 말 것.

## 1번에서만 남은 게이트
1. 최신 공용 032 원본 및 동일 시점 복구본 대조, R4.5 디자인 최소 접합
2. 실제 PC·휴대폰 기기에서 뉴스 목록·검색·매체선택·원문 이동·세로/가로 화면 확인
3. 사진·본문·소개글은 이용조건 확인 전 공개 금지, 비승인 출처는 서버/화면 모두 차단
4. PR #2는 Draft, 자동 병합/운영 배포 금지. GitHub main/공용 화면 변경 없음.

권리 미검증 사진 100개를 임의로 채우거나 제한된 매체 23+2건을 노출하는 것은 출시 기준에 포함되지 않음.