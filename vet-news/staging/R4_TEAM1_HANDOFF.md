# 닥터펫 3번 수의계 뉴스 전략실 → 1번 공용 홈페이지 전략실
## R4 독립 출시접합 후보 / 권리 게이트 / 검수·복구 인계 (2026-11-08 KST)

### 1. 대표 승인 범위와 실제 완료
- 대표가 R3 디자인을 1차 승인하고 R4 마무리 작업을 승인함.
- **R3 미관·레이아웃을 유지한 R4 UI 연결 후보** 작성: `doctorpet_vet_news_R4_approved_ui_staging.html`.
- **기존 Edge Function을 건드리지 않는 새 안전 공개 데이터 함수 후보** 작성: `doctorpet_vet_news_R4_rights_gate_edge_staging.ts`.
- **로컬 브라우저 자동검수 통과**: PC 1440px / 모바일 에뮬레이터 390·360·320px. 검색, 출처별 선택, 100개 페이지 이동(201개 가상 데이터 → 100/100/1), 모바일 가로 넘침 없음, JS 오류 0. 외부 언론 사진 네트워크 0.
- 실제 서버 설치, 실기사 실조회, 언론 원문 클릭과 실물 휴대폰 검수는 **아직 미실시**. 기본 상태는 사진·소개글·본문 0건 공개. 검수용 201건은 *가상 데이터*이며 실제 뉴스 수치로 보고하지 않음.
- **GitHub main / 사이트 / 기존 API / DEV 데이터·Storage·cron / 운영 서버 변경 없음**. (별도 스테이징 PR이 생성되는 경우에도 `main` 미변경.)

### 2. 최신 정본 / 보존 / 복구 기준
- 공용 미리보기 저장소: `doctorpetadmin7-maker/doctorpet-v1-dev-preview`.
- 기존 실제 페이지 `vet-news/index.html` GitHub blob SHA: **`d670e5d3fe1afe98072aca8b00718598acb2960d`** (2026-11-08 23:xx KST 읽기 확인).
- 당시 main HEAD: `f5a59deb17665c0420121fa35d08582a5496d8f6` (2026-11-08 22:07 KST 커밋). 배포·접합 전 **반드시 그 시점 최신 정본과 복구본을 다시 확인**.
- 기존 DEV `doctorpet-vet-news-release-data` Edge Function **v3** / ezbr sha256 **`7558510249879a8d72f3a648e37ec1a5e86b2a36d1611ef7ddd6f1c5a0b086dc`**. 변경하지 않음.
- R4 UI SHA256 `79b294860ee9433ea242a0a3e7707184493c5912894220ae217a8b142614153c`.
- R4 Edge 후보 SHA256 `7121e0c3a22e5ded58b595f146c3b534e72ffa44bb93bce5e98f3de04b356d3f`.
- GitHub 브랜치에서 변경한다면 새 파일만 추가해 `vet-news/index.html`을 덮어쓰지 말 것. 나중에 1번이 접합할 때는 현재 원본의 blob SHA 및 변경 diff를 확인 후 최소 범위만 교체. 실패 시 해당 커밋 revert 또는 원본 blob 복구.

### 3. 읽기 전용 DEV 실사
- `doctorpet_domestic_news.articles` 데일리개원 **64건** 보관; RSS 출처 링크 기록 64건. **RSS 출처 기록 자체는 이미지/본문/소개글 이용 허락이 아님**.
- `private_reference_trials` 데일리벳 **23건**, 해피펫 **2건** 보관. 해당 행의 `publisher_permission_confirmed=true` **각 0건**.
- 저장된 사진 URL: 데일리개원 2, 데일리벳 13, 해피펫 2 → 총 **17 URL**. 사진 사용 승인·화면 성공·현재 권리 확인 17건을 의미하지 않음.
- 기존 공개 API v3의 코드가 **비공개 시험 행 및 사진 URL을 응답 구성에 포함**하며 기사별 권리 승인 필터가 없음. 프런트에서 CSS로 사진을 숨기기만 해서는 해결되지 않음. 이미 외부로 전달되었는지는 별도 실제 네트워크 검수 필요.

### 4. R4 기능 연결 방식 (fail closed)
- 신규 엔드포인트 후보: `doctorpet-vet-news-public-safe-v1` (동작 미설치). 기존 `doctorpet-vet-news-release-data`는 계속 읽지 않고 대체하거나 고치지도 않음.
- **서버 기본 OFF**: `DPN_NEWS_RSS_METADATA_PUBLIC_OK` 환경 변수가 명시적으로 `true`가 아니면 `{ schemaVersion:'NEWS_PUBLIC_SAFE_V1', rightsGate:'REVIEW_PENDING', items:[] }`만 응답. DB 조회도 하지 않음.
- 별도 이용 조건 확인·대표의 *콘텐츠 공개 전환 승인* 후에만 오직 `FEED_DAILYGAEWON` 승인된 RSS **제목/발행일/원문 링크**로 한정된 메타데이터 전송. `private_reference_trials`, 팜인사이트, 해피펫, 데일리벳, 이미지, 소개글, 기사 본문은 **절대 SELECT·전송하지 않음**.
- 프런트 역시 `NEWS_PUBLIC_SAFE_V1`의 정확한 응답 스키마, 허가 플래그, 출처, 안전한 `https://*.dailygaewon.com` 링크가 아니면 데이터 **전체 표시 거부**. 이미지 엘리먼트 0개 + CSP `img-src 'none'`.
- 유효한 메타데이터 전송 후 검색/최신순/100건 페이지/원문 새 탭, 출처 탭은 정상 작동. 권리 미확인 매체는 빈 목록·보류 안내만 노출.
- **게시 허용이 확인되기 전에는 모드만 바꾸거나 환경 변수를 켜지 않음**. 신구 API 응답을 합치거나 구 API 폴백하면 안 됨.

### 5. 제한 (변경 금지)
- **팜인사이트** 요청·수집·표시 금지.
- **뉴스1 해피펫** 신규 요청 금지. 기존 자료는 보존, 공개 전환도 별도 심사.
- **데일리벳** 최신 실행본과 DB 계약 검증 및 별도 전환 지시 전 요청·claim·재가동 금지.
- **기사 원문·사진·소개글** 원저작권자 이용 조건을 확인하기 전 공개 보류.
- 다른 뉴스 수집기·뉴스009·기존 공지·병원 검색·개인비서·회원 권한과 저장 상태 보존. 1번 공용 홈페이지 직접 동시 편집 금지.

### 6. 1번의 설치 전·후 게이트 (마무리 순서)
1. GitHub와 032 Site 최신 실제 원본/복구본을 같은 시각 읽기 확보, R4 diff 확인.
2. 현재 공개 `doctorpet-vet-news-release-data`가 허가 미확인 URL/시험 행을 응답하는 문제를 **서버 응답 자체**에서 차단하는 별도 패치 계획 결정. 서비스 의존성을 조사한 뒤 정확한 전환/복구 SQL 없이 기존 함수를 무작정 바꾸지 않음.
3. R4 신규 안전 API를 DEV에 **기본 OFF**로만 설치한다면 기능 경계·CORS·권한·실제 접근 로그를 검증. 다른 스키마·cron·Storage 정책 변경 없음.
4. 실물 PC·휴대폰에서 실제 승인 기사만 표시되는지 검수. 허가 없는 출처·사진·소개글/본문은 **응답과 화면에서 모두 0**이어야 함.
5. 기사/원문 이동·검색·새 탭 복귀, 100건 페이지 및 기존 사이트 기능 회귀 시험. 1번만 공용 최신 소스에 최소 접합.
6. 별도 공개 승인 전에 사진 100장/실제 뉴스 자동 게시 성공이라고 보고하지 않음. 문제가 있으면 R4 URL 사용을 중단하고 원본 blob/이전 API 설정을 유지, 신규 게이트 변수 OFF로 복원.

### 7. 검수 자료
- `doctorpet_vet_news_R4_test_report.json`: 4개 화면 크기 PASS / XSS 제목 이스케이프 PASS / 사진·요약·비승인 출처/URL 강제 입력 차단 PASS.
- `doctorpet_vet_news_R4_PC_firstfold.png`, `doctorpet_vet_news_R4_Mobile390_firstfold.png`, 360/320 px 화면. **스크린샷의 201개 기사는 테스트용 합성 자료**이며 실제 공개 0건.
- 기존 R3 인터랙션/사진 자리 100칸 독립 시안은 계속 보존하고 이미지 진짜 게시와 구분.