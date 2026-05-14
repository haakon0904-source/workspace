# AutoSeller - 세션 기록 (Session 3)

날짜: 2026-05-14

---

## 마진 계산 개선 (돈버는하마 마진계산기 기준)

**변경 전 공식:**
```
순이익 = 판매가 - 원가 - 수수료 - 배송비
```

**변경 후 공식:**
```
수수료     = 판매가 × 수수료율
세전이익   = 판매가 - 원가 - 배송비 - 수수료
부가세     = 세전이익 × 10%
순이익     = 세전이익 - 부가세  (= 세전이익 × 0.9)
마진율     = 순이익 / 판매가
```

**파라미터 변경:**
- 수수료율: 0.108 → 카테고리별 자동 적용
- 배송비: 3000 → 2500 (나의 배송비 기준)
- vat_rate: 0.1 추가

파일: `pipeline/step4_margin.py`

---

## 쿠팡 카테고리별 수수료율 자동 적용

**신규 파일: `uploader/coupang_commission.py`**
- WING 수수료 안내 페이지 전체 테이블 하드코딩
- 대/중/소분류 → 폴백 순 조회
- `get_rate("패션", "패션잡화")` → 0.105

**`run_pipeline.py` 구조 변경:**
```python
KEYWORD_CATEGORIES = {
    "우산": {
        "display_category": 69884,           # WING에서 확인한 카테고리 코드
        "commission": ("패션", "패션잡화"),   # 10.5%
    },
    # 키워드 추가 시 여기에
}
```
- 파이프라인 시작 시 `_resolve_keyword_config()` 호출
- 키워드별 수수료율 + display_category 자동 결정
- step4에서 상품별 commission_rate, display_category 자동 부여
- coupang.py에서 product.display_category 우선 사용

---

## 웹 모니터링 대시보드

**신규 파일:**
- `web/app.py` - Flask 서버 (port 5001)
- `web/templates/index.html` - 대시보드 UI

**기능:**
- 파이프라인 탭: 실행 버튼, SSE 실시간 로그 스트리밍
- 마진/상품 탭: 요약 카드(전체/업로드/마진율/이익), 검색, 정렬, 상태 칩

**실행:**
```bash
python3 web/app.py
# http://localhost:5001
```

---

## 경로 버그 수정

`run_pipeline.py`에서 상대경로 → 절대경로:
```python
_ROOT = Path(__file__).parent
open(_ROOT / "pw/pw.md")
str(_ROOT / "db/autoseller.db")
```
web/app.py에서 실행 시 working directory 차이로 발생하던 오류 해결.

---

## 기타 도구

- `tools/find_category.py`: 카테고리 코드로 쿠팡 API 수수료율 조회 (참고용)

---

## 현황

| 단계 | 상태 |
|---|---|
| Step 3 도매꾹 크롤링 | 완료 |
| Step 4 마진 계산 | 완료 (부가세 반영, 카테고리별 수수료) |
| Step 5 DB 저장 | 완료 |
| Step 6 쿠팡 업로드 | 완료 |
| 웹 대시보드 | 완료 |
| Step 7 등록 검증 | 미구현 |
| Step 8 알림 | 미구현 |
| 카테고리 자동 매핑 | 미구현 |
| 서버 배포 (EC2) | 예정 |
