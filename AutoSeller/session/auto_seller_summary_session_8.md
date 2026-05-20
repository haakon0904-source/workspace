# AutoSeller - 요약 써머리 Session 8

날짜: 2026-05-20

---

## 이번 세션에서 한 것

### 1. 네이버 스마트스토어 확장 시작

**멀티플랫폼 아키텍처 설계 및 구현**

- `uploader/naver.py` 신규 작성
  - OAuth 2.0 인증 (HMAC-SHA256 서명, 토큰 캐싱)
  - 상품 등록 API (`POST /v2/products`)
  - 도매꾹 상품 → 네이버 포맷 변환 (_build_payload)
  - 배송비 조건부 무료 설정, 원산지/A/S 정보 포함

- `pipeline/step6_upload.py` 멀티플랫폼화
  - 쿠팡 + 네이버 동시 업로드
  - config 키 존재 여부로 플랫폼 자동 판단
  - DB에 `naver_product_id` 컬럼 자동 추가

- `pipeline/step4_margin.py`
  - 상품에 `naver_leaf_category_id` 자동 첨부

- `run_pipeline.py`
  - 네이버 커머스 API 키 로드 추가
  - `KEYWORD_CATEGORIES`에 `naver_leaf_category_id` 추가 (우산: 50002168)

- `pw/pw.md`
  - 네이버 커머스 Client ID / Secret 추가

### 2. 네이버 스마트스토어 가입

- 스토어명: 퓨어떠라 (pure_seola)
- 2026.05.20 가입 심사 승인 완료
- apicenter.commerce.naver.com 앱 등록 완료
  - App ID: 7DOHHubNWZgEANR9oFupad
  - API 그룹: 문의/상품/정산/주문판매자/판매자정보 5개 추가
  - API호출 IP: 49.161.219.47 등록

### 3. 네이버 커머스 API 토큰 인증 이슈

- `client_secret_sign` 검증 실패 (400 BadRequest)
- 시크릿: `$2a$04$ZlnukP94tprJcksXNOEBCe` (29자, 전체값 확인)
- HMAC-SHA256 표준/URL-safe/패딩제거 등 모든 방식 시도 → 동일 에러
- **원인 미파악** → 앱 등록 후 전파 시간 필요 가능성 (10분 대기 후 재테스트 예정)

---

## 현황

| 상태 | 개수 |
|---|---|
| 쿠팡 승인완료 (판매중) | 67개 |
| 쿠팡 승인반려 | 7개 |
| 쿠팡 임시저장 (상세X) | 44개 |
| 네이버 스마트스토어 | 승인완료, API 인증 디버깅 중 |

---

## 다음 할 일

- [ ] 네이버 커머스 API 토큰 인증 해결 (10분 대기 후 재테스트)
- [ ] 네이버 상품 업로드 end-to-end 테스트
- [ ] 쿠팡 송장 등록 플로우 검증 (도매꾹 발송 후)
- [ ] 승인반려 7개 WING 확인
- [ ] headless=True 전환
- [ ] EC2 배포 (주문량 증가 시)
