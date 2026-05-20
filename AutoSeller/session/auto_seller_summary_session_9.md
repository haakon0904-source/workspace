# AutoSeller - 요약 써머리 Session 9

날짜: 2026-05-20

---

## 이번 세션에서 한 것

### 1. 네이버 커머스 API 인증 해결

- **원인**: HMAC-SHA256이 아니라 bcrypt
- `client_secret`이 bcrypt salt로 사용되는 구조
- `bcrypt.hashpw("{client_id}_{timestamp}", client_secret)` → base64 → `client_secret_sign`
- 토큰 발급 200 성공

### 2. 네이버 상품 업로드 완성

- 이미지 외부 URL 불가 → `_upload_image()` 함수 구현 (네이버 서버 업로드 + 캐싱)
- 필수 필드 10개 순차 해결
- 올바른 카테고리 ID API 직접 조회 (`50004018` = 자동우산)
- `deliveryFeeType: "FREE"` 확정 (마진에 배송비 포함되어 있음)
- 상품 등록 end-to-end 성공 확인

### 3. 웹 대시보드 멀티플랫폼 개편

- 상품탭: 플랫폼 필터 버튼 + 쿠팡/네이버 배지 컬럼 분리
- 주문탭: 주문ID 옆 플랫폼 배지
- DB 자동 마이그레이션: `naver_product_id`, `orders.platform` 컬럼

---

## 현황

| 상태 | 내용 |
|---|---|
| 쿠팡 판매중 | 67개 |
| 쿠팡 반려 | 7개 |
| 쿠팡 임시저장(상세X) | 44개 |
| 네이버 | API 인증 + 업로드 완성, 실제 상품 미등록 |

---

## 다음 할 일

- [ ] 기존 DB 상품들 네이버 일괄 업로드 실행
- [ ] 승인반려 7개 쿠팡 WING 확인
- [ ] 쿠팡 송장 등록 플로우 검증 (도매꾹 발송 후)
- [ ] headless=True 전환
- [ ] EC2 배포 (주문량 증가 시)
