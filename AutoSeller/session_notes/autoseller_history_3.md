# AutoSeller - 세션 기록 (Session 5)

날짜: 2026-05-19

---

## 노출상품명 (displayProductName) 필드 발견

`sellerProductName`, `generalProductName` 외에 `displayProductName` 별도 존재.
(상세X) 접두사 작업 시 이 필드도 함께 수정 필요.

---

## 상세X 상품 처리

detail_imgs 수집 실패한 44개 상품:
1. 제목 + 노출상품명에 `(상세X)` 접두사 추가
2. 임시저장으로 전환 (판매 불가 처리)

---

## 배송 위탁 고지 문구 추가

**배경:** 드랍쉬핑 구조상 도매꾹에서 직배송 → 고객 개인정보 위탁 클레임 방지

**추가 위치:** `_build_contents()` + `update_contents()` 마지막 항목

```python
_SHIPPING_NOTICE = {
    "contentsType": "TEXT",
    "contentDetails": [{"content": "본 상품은 제휴 물류센터에서 발송됩니다. 고객님의 개인정보(주소, 연락처)는 배송 목적으로만 활용됩니다.", "detailType": "TEXT"}],
}
```

- 신규 상품: 자동 적용
- 기존 74개: update_contents() PUT으로 소급 적용 완료
- HTML detailType 시도했으나 쿠팡 API 미지원 → TEXT 유지

**향후:** EC2 배포 시 이미지 호스팅 구축 후 이미지로 교체 예정

---

## 현황

| 상태 | 개수 | 비고 |
|---|---|---|
| 승인완료 (판매중) | 67개 | 배송 고지 문구 포함 |
| 승인반려 | 7개 | WING 확인 필요 |
| 임시저장 | 44개 | 상세X (도매꾹 삭제 상품) |
