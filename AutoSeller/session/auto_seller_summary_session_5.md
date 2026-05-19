# AutoSeller - 요약 써머리 Session 5

날짜: 2026-05-19

---

## 이번 세션에서 한 것

### 1. (상세X) 상품 처리
- detail_imgs 없는 44개: 제목 + 노출상품명(`displayProductName`)에 `(상세X)` 접두사
- 전부 임시저장으로 전환 (판매 중단)
- `displayProductName` = 쿠팡 노출상품명 (별도 필드, sellerProductName과 다름)

### 2. 배송 위탁 고지 문구
- 드랍쉬핑 클레임 방지용 고지 문구 상세설명 마지막에 추가
- `_build_contents()` + `update_contents()` 양쪽에 `_SHIPPING_NOTICE` 적용
- 기존 74개 소급 적용 완료
- HTML detailType → 쿠팡 미지원 → TEXT 유지
- 향후 이미지로 교체 예정 (EC2 호스팅 시)

---

## 현황

| 상태 | 개수 |
|---|---|
| 승인완료 (판매중) | 67개 |
| 승인반려 | 7개 |
| 임시저장 (상세X) | 44개 |

---

## 다음 할 일

- [ ] 승인반려 7개 WING 확인
- [ ] EC2 배포 + 이미지 호스팅 구축
- [ ] 배송 고지 → 이미지로 교체
- [ ] Step 7: 등록 검증
- [ ] Step 8: 트위터 알림
