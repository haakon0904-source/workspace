# AutoSeller - 세션 기록 (Session 9)

날짜: 2026-05-20

---

## 네이버 커머스 API 인증 해결

### 원인
- HMAC-SHA256이 아닌 **bcrypt** 방식 사용
- `client_secret`은 bcrypt salt (`$2a$04$...` 형식)
- 서명 생성: `bcrypt.hashpw("{client_id}_{timestamp}".encode(), client_secret.encode())`
- 결과를 base64 인코딩 → `client_secret_sign`

### 수정 파일: `uploader/naver.py`
- `import hmac, hashlib` 제거 → `import bcrypt` 추가
- `_get_token()` 내 서명 생성 로직 교체

---

## 네이버 상품 업로드 end-to-end 완성

### 순차 해결한 오류들
1. `client_secret_sign` 400 → bcrypt 방식으로 해결
2. `minorPurchasable` NotNull → `True` 추가
3. `productInfoProvidedNotice.etc.modelName/manufacturer/itemName` NotNull → 추가
4. 이미지 URL 유효하지 않음 → 외부 URL 직접 불가, **네이버 서버에 업로드 후 URL 사용**
5. `deliveryCompany` 필수 → `"CJGLS"` 추가
6. `deliveryFeePayType` NotEmpty → `CONDITIONAL_FREE` 미지원 확인, `"FREE"` 타입으로 변경
7. `claimDeliveryInfo.returnDeliveryFee/exchangeDeliveryFee` 필수 → 추가
8. `originAreaInfo.importer` 필수 → `"해당없음"` 추가
9. `afterServiceDirector` 필수 → CS 전화번호 추가
10. `optionCombinations.id` 유효하지 않음 → `id` 필드 제거
11. `leafCategoryId` 사용 불가 → 카테고리 API로 정확한 코드 조회

### 올바른 카테고리 ID (API 직접 조회)
| 카테고리 | ID |
|---|---|
| 패션잡화>패션소품>우산>자동우산 | `50004018` |
| 패션잡화>패션소품>우산>수동우산 | `50004017` |
| 패션잡화>패션소품>우산>기타 | `50017381` |

- `run_pipeline.py` KEYWORD_CATEGORIES 우산 카테고리 수정: `50002168` → `50004018`
- CONFIG 기본 카테고리 수정: `50000803` → `50017381`

### 추가 기능: `_upload_image()`
- 외부 이미지 URL → `requests.get()` 다운로드 → `POST /v1/product-images/upload`
- 네이버 CDN URL 반환 + 세션 내 캐싱 (`_img_cache`)

### 최종 확인
- product_id `13495883445` 등록 성공 (테스트 후 판매자센터에서 삭제)

---

## 웹 대시보드 멀티플랫폼 개편

### `web/app.py`
- `_resolve_keyword_config` 반환값 2-tuple → 3-tuple 언팩 수정
- `CONFIG["keyword_naver_categories"]` 추가
- `api_products()`: `naver_product_id` 컬럼 포함, 없으면 자동 ALTER TABLE
- `api_orders()`: `orders.platform` 컬럼 없으면 자동 추가 (DEFAULT 'coupang')
- 파이프라인 Step 6 로그: "쿠팡 + 네이버 업로드"

### `web/templates/index.html`
- **상품 탭**: 
  - 플랫폼 필터 버튼 `전체 | 쿠팡 | 네이버` 추가
  - 요약 카드: 쿠팡 판매중 / 네이버 등록 카운트 분리
  - 테이블: 쿠팡 상태 + 네이버 상태 컬럼 분리
- **주문 탭**: 주문ID 아래 플랫폼 배지 (쿠팡/네이버)
- **파이프라인 탭**: Step 6 설명 "쿠팡 + 네이버 업로드"로 수정
