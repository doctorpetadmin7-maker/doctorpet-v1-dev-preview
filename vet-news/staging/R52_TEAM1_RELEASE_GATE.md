# 닥터펫 수의계 뉴스 R5.2 — 1번 접합·출시 판정표
작성: 2026-11-09 KST. **공개 승인 아님.** 공용 홈페이지는 1번 담당.

## 3번 완료 / 다시 하지 말 것
- DEV 뉴스 API v7 ACTIVE. 해시: db78dd773b9f8984ca15bbf49fe7a404e3a4c71ac718761a23dc30a5c9752e26.
- 실 HTTP/CORS+브라우저 R4.9 PASS: https://github.com/doctorpetadmin7-maker/doctorpet-v1-dev-preview/actions/runs/42500933130
- 금지 API 5개 HTTP 410, 내부 인증 2경로 HTTP 401 (R5.1 12/12 PASS): https://github.com/doctorpetadmin7-maker/doctorpet-v1-dev-preview/actions/runs/42502531513
- DB 저장: 데일리개원 64, 데일리벳 비공개 23, 해피펫 비공개 2. 데일리벳 paused=true, RUNNING=0.
- 검수한 화면: vet-news/staging/r4_5-rights-safe-ui.html. 실제 공개 및 실기기 검수는 미완료.

## 1번의 실제 출시 관문
1. 최신 032 공용 원본 + 동일 시점 복구본 대조 후 승인 R4.5 디자인을 최소 접합. GitHub main/vet-news/index.html의 이전 blob d670e5d3fe1afe98072aca8b00718598acb2960d, 작업 직전 재조회 필수.
2. 기존 main의 summaryFor(r) 합성 소개글 제거; 실제 기사 소개글이 없는 경우 '미제공/권리 확인 중'으로 표시. 사진을 연결된 것처럼 오인시키지 않음.
3. 실제 PC·휴대폰에서 로그인/진입, 뉴스 검색·초기화·매체 선택·원문 링크·최신순·100건 단위 페이지·CORS·뒤로가기·가로 넘침 검수.
4. 기존 홈·NEWS009·다른 서비스 회귀 검수, 안전 롤백 절차 및 적용 파일 SHA 기록.
5. 이용 조건 서면 확인: 데일리개원 제목·날짜·원문 링크의 상업적 표시 범위와 사진·본문·2줄 요약 각각의 권한·기간·출처 표시·비용. 발송 전 문의 초안: vet-news/staging/R50_DAILYGAEWON_RIGHTS_GATE_INQUIRY_DRAFT.md
6. 위 사항 통과 뒤 대표님의 **별도 외부 공개 승인**. 이 PR Draft·병합 보류 유지.

## 변하지 않는 제한
- 팜인사이트 요청·수집·표시 금지.
- 해피펫 신규 요청 금지.
- 데일리벳 별도 전환 승인 전 요청·claim 금지, paused=true 유지.
- 사진·본문·소개글 이용 조건 확인 전 공개 금지. 저장기록 89건은 공개된 기사 89건이 아님.
- 3번이 공용 홈페이지, 운영 서버, 수집기 또는 다른 서비스 변경하지 않음.

실제 DEV 응답 검수 PASS는 **출시 PASS/저작권 허락/실기기 검수와 별개**입니다.
