# AutoSeller - 세션 기록 (Session 6)

날짜: 2026-05-20

---

## Step 7: 드랍쉬핑 자동 주문 플로우 완성

### 쿠팡 주문 API 버그 3개 수정 (`uploader/coupang_order.py`)
1. 날짜 포맷: `T00:00:00` 제거 → `yyyy-MM-dd` 형식만 사용
2. `createdAtTo` 범위: 오늘까지 포함하려면 내일 날짜 사용 (`today + 1 day`)
3. 필드명 수정: `orderSheetId` → `shipmentBoxId`, `externalVendorSku` → `externalVendorSkuCode`
4. API 응답 코드 체크: `"SUCCESS"` 문자열 → `not in (200, "SUCCESS")`

### 실제 주문 테스트 성공
- 쿠팡 주문 동기화 → DB pending 저장 → 도매꾹 장바구니 담기 → ORDER_OK 반환 확인
- 단, 결제는 `vaccount`(가상계좌) 방식이라 수동 이체 필요 → `emoney`(꾹페이)로 전환 필요

---

## 텔레그램 주문 알림 구현 (`tools/check_orders_notify.py`)

- Twitter API 402 에러 (크레딧 없음) → 텔레그램 Bot API로 전환
- 쿠팡 최근 4시간 주문 조회 → 신규 주문만 텔레그램 메시지 전송
- 처리된 주문 ID는 `db/processed_order_ids.json`에 캐싱 (중복 알림 방지)
- 로컬 테스트 성공 (메시지 수신 확인)

### GitHub Actions 스케줄 (`.github/workflows/order_check.yml`)
- KST 9시 / 12시 / 15시 하루 3회 실행
- `workflow_dispatch`로 수동 실행 가능
- **Coupang API IP 차단 문제**: GitHub Actions IP가 쿠팡 API 화이트리스트에 없음 → 미해결, 추후 EC2 연동 시 해결

---

## 대시보드 주문 관리 UI 개선 (`web/templates/index.html`)

### 주문 테이블 체크박스 추가
- `pending` 상태 주문만 체크박스 활성화
- 전체선택 / 개별선택 지원
- "선택 주문 실행" 버튼 → 선택된 `order_ids`만 step7에 전달

### 주문 실행 실시간 로그
- SSE 스트림 재활용하여 주문 처리 과정 `orderLogBox`에 표시

### 백엔드 연동 (`web/app.py`, `pipeline/step7_order.py`)
- `api_orders_run()` → request body에서 `order_ids` 수신
- `run(config, order_ids=None)` + `_get_pending_from_db(db_path, order_ids=None)` 필터링 지원

---

## 설정 변경 (`run_pipeline.py`)
- `domeggook_pay_method`: `vaccount` → `emoney` (꾹페이 충전 후 완전 자동화 목적)
- `telegram_token`, `telegram_chat_id` 설정 추가 (pw.md에서 로드)
