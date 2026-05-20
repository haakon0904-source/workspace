# AutoSeller History - Session 10

날짜: 2026-05-20

## 작업 내용

### 1. pHash 기반 이미지 중복 제거 구현 (step4_margin.py)

**배경**
- 도매꾹에서 동일한 실물 상품이 여러 판매자 계정으로 등록되어 있음
- 다른 item_no, 다른 가격이지만 같은 이미지인 경우 네이버에 중복 등록되는 문제

**구현**
- `_fetch_phash(url)`: 이미지 다운로드 후 perceptual hash 계산 (실패 시 None → 그냥 통과)
- `_dedup_by_image(products)`: O(n²) Hamming distance 비교, threshold=8
- 중복 판정 시 **판매가 낮은 것 유지** (소비자 기준, 마진율은 어차피 둘 다 통과한 상태)
- 이미지 다운로드 **병렬 처리** (ThreadPoolExecutor, max_workers=10)
- User-Agent 헤더 필요 (도매꾹 CDN 접근 시)

**위치**: `pipeline/step4_margin.py` — `run()` 끝에서 호출

**검증 결과**
- TOROSS 핸디선풍기 두 item_no(63619129, 14057475) → pHash Hamming=0 (완전 동일 이미지) → 정확히 중복 감지
- 3개 이미지 병렬 다운로드: 0.38초

### 2. 네이버 등록 상품 60개 전체 삭제

- Naver API `DELETE /v2/products/{originProductNo}` 일괄 호출
- DB `naver_product_id` NULL 초기화, `status='pending'` 복원
- 이유: pHash 중복제거 로직 적용 후 깨끗하게 재등록 테스트하기 위해

### 3. 도매꾹 429 차단 → 복구 확인

- 디버그 중 반복 요청으로 IP 일시 차단
- 대기 후 정상 복구, 파이프라인 정상 실행 확인

## 현황

| 상태 | 내용 |
|---|---|
| 쿠팡 | 기존 등록 상품 유지 |
| 네이버 | 전체 삭제 후 재등록 준비 완료 |
| pHash 중복제거 | step4에 적용 완료 |

## 다음 할 일

- [ ] 파이프라인 실행 → 네이버 신규 등록 (pHash 중복제거 적용)
- [ ] 쿠팡 승인반려 7개 WING 확인
- [ ] 쿠팡 송장 등록 플로우 검증
- [ ] headless=True 전환 (이미 True로 적용됨)
- [ ] EC2 배포 (주문량 증가 시)
