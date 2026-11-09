# 닥터펫 3번 / R6.3 — 18660 글자 깨짐 수집 경계 신규 조사
기준: 2026-11-09 KST | 읽기 전용 원인 추적 + 격리형 테스트 후보. **실제 수집기에 미설치.**

## 새로운 확인 사항
- FEED_DAILYGAEWON 기사 `idxno=18660` DB 제목에는 `U+FFFD`가 2개 저장됨.
- 같은 깨짐 제목이 `doctorpet_domestic_news.feeds.items->items` **RSS 정규화 캐시에도 존재**. 현재 캐시 50건 중 손상 1건, 링크 50개 모두 고유, 빈 제목 0.
- 캐시 SHA256 `09b95edae549d1f5d09bc242699827a1c7b9edb91d1f34892c77a61ca749a81b`, 실제 원문 데이터 내려받은 시점 2026-11-06 09:02:02 UTC. 최근 RSS `HTTP 304`는 원문 변경이 없다는 뜻이며 **새 기사 50건 수집이 아님**.
- `feeds` 컬럼은 `items` JSONB·content_sha256·etag·HTTP 상태 등이며, **원본 응답 bytes/Content-Type·charset는 직접 저장되지 않음**. 지금 증거만으로 손상 최초 원인이 발행사 RSS 바이트, charset 인식, HTML/XML 파싱 중 무엇인지 단정 불가.
- 실제 DB 함수 `doctorpet_domestic_news.apply_run`은 입력 제목 길이 1~500, 특수문자 일부, 출처·URL·ID·시간·수집 정책을 검사하지만 **U+FFFD 검사 없음**. `i->>'title'`을 그대로 insert/upsert하며, 캐시에는 `normalized.items`를 저장하는 구조.
- `cron.job` 활성 3건은 닥터펫 앱/배송정리/NEWS009 농식품부 검증이며 데일리개원 수집을 직접 명시하지 않음. 검토 대상 GitHub preview 저장소에서도 실제 RSS runner 진입 파일은 확인되지 않았음. **기존 외부 스케줄러 소스 확보 전 소유 코드 수정 금지**.

## 신규 품질경계 후보
- `vet-news/staging/r63-title-encoding-collector-preflight.cjs`
- `vet-news/staging/r63-title-encoding-collector-preflight.test.cjs`
- 실제 실행 증빙: https://github.com/doctorpetadmin7-maker/doctorpet-v1-dev-preview/actions/runs/42546759112 — **합성 8/8 PASS**. 도구는 오프라인이며 외부 사이트/DB/cron 읽기·쓰기 자체를 하지 않음.
- 바이트를 UTF-8로 읽을 때 `TextDecoder('utf-8',{fatal:true})`로 손실 변환을 차단. 단, 발행사가 다른 문자셋을 정식 표기하면 확인된 문자셋대로 디코딩한 뒤 검사.
- 제목 정규화 후 `U+FFFD`·제어문자·공백/길이 오류를 감지.
- `HTTP 200` 합성 50건 중 1건 손상 시 **손상 1건 검토 보류·정상 49건 유지**가 논리적으로 가능한 것을 시험.
- `HTTP 304` 합성 입력에서는 **기존 캐시 손상 1건 경고**와 `신규 수집 0건`만 보고, 기존 저장자료 변형 없음.
- 같은 제목이라도 URL이 다른 2건은 합치지 않음.

## 설치 전 해결할 중요한 계약 공백
- 이 파일은 `apply_run`의 **정식 실행 어댑터가 아닙니다**. 단순히 `safeNewItems`만 `apply_run`에 전달하거나 `200/304` 결과를 그대로 치환하지 마세요.
- `apply_run`은 `r.accepted === r.items.length`와 `normalized.items`, `cache.feeds`의 개수·출처·시간·해시 조건을 지킵니다. 최신 `304`에서도 기존 runner가 캐시 50건을 그대로 `r.items`로 처리하는 이력이 있어, 신규 0건과 처리 0건은 동의어가 아닙니다.
- 수집기 소유자가 실제 `200` 원본 수집→인코딩→정규화→`r.items`→`normalized.items`→`accepted`→`apply_run` 경계를 **동일 시점 runner 원본 및 테스트**로 확인해야 정상 49건을 지키면서 오류 1건만 검토 보류할 수 있습니다.
- 정상 304 캐시 오류 하나 때문에 예약 실행 전체가 실패하거나 보류 타이머가 재설정되는 부작용 금지. 단순 DB CHECK/lock/function 교체로 일괄 차단하면 50건 재처리와 충돌할 수 있으므로 **미승인 SQL/광범위 DDL 금지**.
- 원본 rss 응답의 Content-Type/charset/bytes 지문은 **기존 정식 실행 소유자 수단으로만** 확보. 여기서 새 출처 요청·수집/claim/DB 쓰기 금지.
- 실제 수집기에 연결했을 때만 신규 기사 입력 1건 / 비공개 매체 0건 / 원본 89건 무손상 / 200·304·실패 복구 / same-time rollback 검수로 PASS 판정.

## 구분
**R6.2**: 기존 18660 화면 제목 보정 실제 DEV API·브라우저 PASS, 공용 화면 미접합.
**R6.3**: 신규 기사 재발 차단 **독립 후보·합성 8/8 PASS**, 실제 수집기 설치/서버 검수 0회.
**보존**: 데일리개원 64건, 데일리벳 비공개 23건, 해피펫 비공개 2건. 데일리벳 paused=true, 기타 금지 소스 요청·공개 재개 없음. 운영·DEV DB·cron·공용 홈페이지 변경 없음.
