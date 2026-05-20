# AutoSeller - 요약 써머리 Session 10

날짜: 2026-05-20

---

## 이번 세션에서 한 것

### 1. pHash 기반 이미지 중복 제거 구현

- **문제**: 도매꾹에서 동일 실물 상품이 다른 item_no로 여러 개 등록됨 → 네이버에 중복 업로드
- **해결**: `pipeline/step4_margin.py`에 `_dedup_by_image()` 추가
  - `imagehash.phash()` 로 시각적 해시 계산
  - Hamming distance ≤ 8이면 동일 상품으로 판단
  - 중복 시 **판매가 낮은 것 유지** (마진율은 어차피 둘 다 기준 통과)
  - 이미지 다운로드 **ThreadPoolExecutor(max_workers=10)** 병렬 처리
  - User-Agent 헤더 필요 (도매꾹 CDN)
  - 다운로드 실패 시 None → 중복 판단 제외, 그냥 통과

- **검증**: TOROSS 핸디선풍기 동일 이미지 Hamming=0으로 정확 감지

### 2. 네이버 등록 상품 60개 전체 삭제

- Naver API로 일괄 삭제 후 DB naver_product_id NULL 초기화
- pHash 중복제거 적용 후 재테스트 목적

---

## 현황

| 상태 | 내용 |
|---|---|
| 쿠팡 판매중 | 기존 유지 |
| 네이버 | 전체 삭제, 재등록 대기 |
| pHash 중복제거 | step4에 적용 완료 |
| 파이프라인 | 정상 동작 확인 |

---

## 다음 할 일

- [ ] 파이프라인 실행 → 네이버 신규 등록 (pHash 중복제거 적용)
- [ ] 쿠팡 승인반려 7개 WING 확인
- [ ] 쿠팡 송장 등록 플로우 검증
- [ ] EC2 배포 (주문량 증가 시)
