# AutoSeller - 요약 써머리 Session 3

날짜: 2026-05-11

---

## 이번 세션에서 한 것

### 도매꾹 크롤링 완성

- **페이지네이션**: `&pg=N` 파라미터 사용, `#lPage ol li[target]` 최대값으로 총 페이지 자동 파악
  - 10페이지 502개 수집 성공
  - `networkidle` → `domcontentloaded` + `wait_for_selector` 로 타임아웃 해소

- **상품 상세 크롤링** (`fetch_detail=True`):
  - 대표이미지: `#lThumbImg` src (`_img_760` 해상도)
  - 가격: `.lItemPrice`
  - 최소구매수량: `.lInfoItemContent` 텍스트에서 파싱
  - 배송정보: `.lInfoDeli .lInfoItemContent`

- **`pipeline/step3_product_search.py` 정리**:
  - 공개 API: `run(keywords: list, config: dict) -> list[dict]`
  - config: `domeggook_id`, `domeggook_pw`, `max_pages`, `fetch_detail`
  - 반환 필드: `source`, `keyword`, `item_no`, `title`, `price`, `min_qty`, `img_url`, `thumb_imgs`, `delivery`

## 방향 결정

- 오너클랜 배제, 도매꾹 기반으로 전체 파이프라인 end-to-end 흐름 먼저 완성
- step1/2 (키워드 수집/선정): 하드코딩 키워드로 스킵
- step5 하네스: stub으로 시작 (Claude API 불필요)
- **다음 블로커: 셀러 계정 확인** → 쿠팡/스마트스토어 중 어느 것이라도 있어야 step6 진행 가능

## 다음 할 일

- [ ] 셀러 계정 유무 확인 (쿠팡 / 스마트스토어)
- [ ] step4_margin.py (마진 계산)
- [ ] step5_register.py (DB 저장 + 하네스 stub)
- [ ] step6_upload.py (플랫폼 업로드)
- [ ] step7_verify.py (등록 검증)
- [ ] step8_notify.py (트위터 알림)

## 미확인 사항

- [ ] 쿠팡/스마트스토어 셀러 계정 ← **현재 블로커**
- [x] Claude API 키 (있음)
- [ ] Twitter 개발자 계정
- [ ] 각 플랫폼 API 승인 절차
