# 닥터펫 3번 수의계 뉴스 / R7.1 — 사진 주소 **변경분만** 감지하는 수집기 접합 후보

작성 기준: **2026-11-09 KST**. 기존 완료된 R6.5 데일리개원 64개 사진 URL, R6.9 3장 브라우저 PASS, R7.0 나머지 60장+18647 최신 1장 브라우저 PASS, 89건/사진 URL 79건 통합 검수, 기존 PC·휴대폰·저장/회원 접근 검수 **재실행하지 않음**.

## 이번 신규 구현만
- **후보 코드:** `vet-news/staging/r71_photo_metadata_delta.py`
- **신규 단독 검수:** `vet-news/staging/test_r71_photo_metadata_delta.py`
- **GitHub Actions:** https://github.com/doctorpetadmin7-maker/doctorpet-v1-dev-preview/actions/runs/42570188557 — **합성 데이터 기반 14/14 PASS**, 외부 원문 요청/사진 다운로드/서버 DB·Storage 쓰기 없음.
- 소유 지점: 기존 승인된 **데일리개원 수집기**가 이미 취득한 기사 HTML에서 `og:image` 메타데이터만 해석하는 **순수 함수**. 기존 수집기가 확인되지 않았으므로 아직 호출부/운영 스케줄러에 **미연결**.
- 트리거는 오직 (1) `NEW_ARTICLE`: 새 기사 메타데이터가 원래 수집되고 기사 페이지 HTML이 승인된 경로로 이미 확보된 경우, 또는 (2) `BROKEN_IMAGE`: **정확한 해당 기사 이미지가 404나 브라우저 디코딩 실패**라는 신규 실패 영수증이 확보된 경우.
- `FEED_DAILYGAEWON`, 정확한 기사 원문 URL/idxno/썸네일 경로/파일명(기사번호)·HTTPS·출처 호스트가 일치해야 신규 후보 URL을 반환. 다른 매체·다른 기사·HTTP·SVG·복수 후보·잘못된 포트·알 수 없는 재수집 트리거 **차단**.
- 결과 상태는 `REVIEW_NEW_IMAGE_METADATA` / `REVIEW_REPAIRED_IMAGE_METADATA` / `HOLD_...` / `REJECT_...`. 후보에 `publishable:false`, `rightsStatus:PUBLISHER_PERMISSION_UNCONFIRMED` 포함. 실제 사진 **게재 허락이나 승인 상태를 부여하지 않음**.
- **재현용 실제 사례:** 기사 **18647** 기존 사진 URL `18647_26833_2154_v150.jpg` → 404; 원문 새 `og:image` `18647_26866_1322_v150.jpg` → HEAD 200 / Chromium 300×424 JPG 표시 PASS. 기존 63건은 교체/재검수하지 않았음.

## 정식 소유자가 인수할 때의 정확한 한 부분
1. **기존 runner의 소유자·원본 SHA·같은 시점 복구본·개별 기사 HTML 공급 지점**부터 확인. 기존 032 공용 화면/NEWS009/DEV 수집 기록과 병렬로 재설치하지 않음.
2. 이미 적법한 경로로 수신한 **해당 기사 HTML**을 `decoded_html`로 전달하며 최초 바이트 변환은 문자셋 근거에 따른 **엄격한 디코딩**을 유지(R6.3 글자 깨짐 게이트 재사용). 새 웹 요청·리다이렉트 우회·과도한 재시도 추가 금지.
3. 함수 결과는 **비공개 사진 URL 후보**이며, 단독으로 `doctorpet_domestic_news.article_images`의 `APPROVED` 행을 만들거나 공용 기사 UI로 공개하는 명령이 아님. 6번 소유자가 권리 근거와 동일시점 복구·권한 경계를 검증한 뒤 정식 저장 대상/검수 라우트를 결정.
4. 새 기사 1건 또는 404 기사 **1건의 후보 변환만** 추가 end-to-end로 확인. 기존 64/64 사진 브라우저 PASS·기존 검색/100건 페이지·PC/휴대폰·회원 A/B 시험 재실행하지 않음. 필요 시 새 URL 카드 onload/onerror 구간만 검사.
5. **데일리벳·해피펫** 기존 보관 기사·사진 주소는 이 파일 적용 범위가 아님. 기존 금지된 새 수집 및 미확인 권리 공개를 재개하지 않음.

## 구분·차단
- **이번 완료:** 실패한 한 기사와 새 기사 2개 흐름의 **사진 주소 후보 계산 코드**, 자체 안전 가드 14건 CI PASS.
- **아직 없음:** 실제 수집기 원본, DEV 실서버 호출부/DB 저장·게시, 1번 Site032 실제 적용 영수증, 사진 공개 사용 허락.
- **보존:** 기존 89건 기사, 데일리개원 64건 사진 디코딩 증빙, 데일리벳 23·해피펫 2 비공개, 사진 공개 0장, 운영/Production·DEV DB·cron·Storage·공용 홈페이지 변경 **0회**.

**한 줄 판정:** `R71_DELTA_LOGIC_PASS_14_OF_14 / COLLECTOR_INTEGRATION_NOT_DONE / PUBLISHING_OFF`.
