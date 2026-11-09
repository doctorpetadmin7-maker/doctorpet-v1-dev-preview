# 3번 뉴스 전략실 → 1번 공용 홈페이지 전략실 / R4.3 최신 인계
**작성:** 2026-11-09 KST · **상태:** 개발 브랜치 적용만 완료, 화면 접합·공개는 보류

## 실제 DEV 변경
- Supabase 부모 프로젝트의 `doctorpet-v1-dev` 개발 브랜치: `mabvxdcpmfdzrqlgkxqn`.
- **기존** `doctorpet-vet-news-release-data` API를 v5→**v6**으로 좁게 패치. 현재 ACTIVE, 배포 ezbr SHA256 `db78dd773b9f8984ca15bbf49fe7a404e3a4c71ac718761a23dc30a5c9752e26`.
- 서버 SQL은 **데일리개원 RSS 보관기사 제목·날짜·원문 링크만** 반환, 비승인 데일리벳/해피펫 시험행 및 사진 메타데이터 조회 제거. 이미지는 null, 소개글은 null, 보류 상태로만 반환.
- 기존 API JSON `version:2`, `pageSize:100`, `groups/states/candidates` 계약 유지. 제한된 출처는 `groups` 빈 배열, `publicationStatus:WITHHELD_RIGHTS_PENDING`, `actualCount:0`.
- DEV DB 원본/수집기/cron/Storage/운영/공용 032/뉴스 페이지 GitHub main **변경하지 않음**. 재조회 보관 수량: 데일리개원 64, 데일리벳 23, 해피펫 2 (총 89, 신규 수집 0).
- 신규 `doctorpet-vet-news-public-safe-v1` 별도 API는 기존 **hard-OFF 상태 유지**.

## R4.3 새 화면 (이 PR의 별도 파일)
- `r4_3-dev-sanitized-metadata-ui.html`: R3/R4 기존 디자인 유지 + **기존 안전 패치 v6 API 단일 연결**.
- 수신 JSON에서 차단 매체 자료 1개라도 있거나 사진/소개글·권리 상태가 원래 계약과 다르면 **화면 전체 기사 목록 fail closed**. API 폴백/사진 외부 요청 없음.
- 제목 검색, 매체 선택, 주제 필터, 최신순, 100개/페이지, 새 탭 원문 이동. 사진은 권리 보류 안내 자리만.
- 사용자 화면은 `DEV RSS 제목·링크 검수`로 표시. **실제 퍼블리셔 이용 허락·공개 승인과 혼동 금지**.

## 검수
- API TypeScript 소스 문법 + 모의 응답 7/7 PASS, 실제 Supabase v6 배포 소스 재조회 일치.
- 실제 DEV DB에서 수정된 데일리개원 SELECT 별도 조회 성공.
- Chromium 에뮬레이션 1440/390/360/320px 4종 PASS. *가상* 기사 201개 → 페이지 100/100/1, 검색, 금지 출처 차단, 사진 요청 0회, JS 오류 0, 가로 넘침 0.
- **실제 API HTTP GET·실제 PC/휴대폰 실기기 연동은 아직 미검증**(이 실행 환경의 외부 네트워크 접근 차단).

## 1번에서 반드시 처리할 것
1. 기존 `main/vet-news/index.html` 화면에는 원문 요약이 없어도 **`summaryFor(r)`가 일반 소개문을 임의 생성**하는 버그가 남아 있음. 새 R4.3로 접합하거나 요약 생성 제거. 원문 사진/본문/소개글은 권리 확인 전 보류.
2. 최신 공용 원본·동일 시점 복구본 대조 후 **1번 소유자의 최소 접합**만 진행. 본 PR은 **Draft, 병합 보류**.
3. 실제 PC·휴대폰 네트워크 요청으로 v6 응답, 검색/원문 이동/페이지 전환, CORS 및 노출 차단을 확인. 권리·공개는 별도 승인.
4. **팜인사이트 요청·수집·표시 금지**, 해피펫 신규 요청 금지, 데일리벳 별도 승인 전 요청·claim 금지.
5. 이전 v5 API 버전은 **비승인 데이터 노출 위험이 있어 그대로 롤백 금지**. 문제 시 v6 동일 코드 유지 또는 별도 hard-OFF 차단으로 복구.

기존 뉴스 페이지 원본 blob: `d670e5d3fe1afe98072aca8b00718598acb2960d`. 최신 접합 직전에 다시 확인.
