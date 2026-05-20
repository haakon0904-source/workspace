# AutoSeller - 요약 써머리 Session 6

날짜: 2026-05-20

---

## 이번 세션에서 한 것

### 1. Step 7 드랍쉬핑 주문 플로우 완성
- 쿠팡 주문 API 버그 3개 수정 (날짜 포맷, 범위, 필드명)
- 실제 쿠팡 주문으로 end-to-end 테스트: 동기화 → 도매꾹 주문 → ORDER_OK 확인
- `domeggook_pay_method`: `vaccount` → `emoney` 변경 (꾹페이 완전 자동화)

### 2. 텔레그램 주문 알림
- `tools/check_orders_notify.py` 신규 작성
- GitHub Actions 하루 3회 스케줄 (`.github/workflows/order_check.yml`)
- 로컬 테스트 성공 / GitHub Actions는 쿠팡 IP 차단으로 미동작 (보류)

### 3. 대시보드 주문 관리 UI
- 주문 테이블 체크박스 (pending만 활성화) + 전체선택
- 주문 실행 실시간 로그 (SSE 스트림)
- 선택한 주문만 step7 실행

---

## 현황

| 상태 | 개수 |
|---|---|
| 승인완료 (판매중) | 67개 |
| 승인반려 | 7개 |
| 임시저장 (상세X) | 44개 |

DB 주문:
| order_id | status |
|---|---|
| 29100191831524 | pending (리셋됨) |

---

## 다음 할 일

- [ ] 꾹페이 충전 후 emoney 방식 자동 주문 테스트 (핵심)
- [ ] 도매꾹 주문 완료 후 송장번호 자동 polling → 쿠팡 송장 등록 플로우 검증
- [ ] 승인반려 7개 WING 확인
- [ ] GitHub Actions + EC2 연동 (쿠팡 API IP 화이트리스트 해결)
- [ ] EC2 배포 + 이미지 호스팅 구축
