# AutoSeller - 세션 기록 (Session 8)

날짜: 2026-05-20

---

## 멀티플랫폼 확장: 네이버 스마트스토어

### 신규 파일
- `uploader/naver.py`: OAuth 토큰 + 상품 등록
- `session/auto_seller_summary_session_8.md`

### 수정 파일
- `pipeline/step6_upload.py`: 멀티플랫폼 (coupang_access_key 있으면 쿠팡, naver_commerce_client_id 있으면 네이버)
- `pipeline/step4_margin.py`: naver_leaf_category_id 상품에 첨부
- `run_pipeline.py`: 네이버 커머스 설정, KEYWORD_CATEGORIES에 naver_leaf_category_id 추가
- `pw/pw.md`: 네이버 커머스 Client ID/Secret/CS전화번호 추가

### 네이버 커머스 API 인증 이슈

**증상**: `client_secret_sign` 항목이 유효하지 않습니다 (400)

**시도한 것**:
- base64 표준/urlsafe/노패딩
- timestamp ms/s
- key-message 순서 바꾸기
- type=SELF/PARTNER/없음
- Basic Auth

**현재 상태**: 미해결. 앱 등록 직후라 전파 대기 중.

### 네이버 스마트스토어 설정

- 스토어: 퓨어떠라 (pure_seola)
- 대표 카테고리: 생활/건강
- 가입심사 승인: 2026.05.20
- apicenter.commerce.naver.com 앱: AutoSeller
  - API 그룹 5개 (문의/상품/정산/주문판매자/판매자정보)
  - API호출 IP: 49.161.219.47
