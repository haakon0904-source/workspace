# AutoSeller - 전체 세션 기록 (Session 3)

날짜: 2026-05-11

---

## 세션 시작

**User:** 오토셀러 기억복기
**Claude:** session_notes/autoseller_history_1.md + session/auto_seller_summary_session_2.md 읽어 컨텍스트 복원.

---

## 도매꾹 페이지네이션

**User:** 도매꾹 페이지네이션 추가해줘

- `&page=N` → 1페이지 반복 감지 (파라미터명 불일치)
- 네트워크/DOM 분석 결과: **`&pg=N`** 이 올바른 파라미터
- 총 페이지: `#lPage ol li[target]` 최대값
- `networkidle` → `domcontentloaded` + `wait_for_selector('#lLst li')` 로 타임아웃 해소
- 결과: 10페이지, 502개 수집 성공

---

## 다음 스텝 (상세 크롤링 + pipeline 정리)

**User:** 다음 스텝 진행해줘

### 상품 상세 크롤링

셀렉터 탐색 결과:
- 대표이미지: `#lThumbImg` (`_img_760` 해상도로 URL 정규화)
- 가격: `.lItemPrice`
- 최소구매수량: `.lInfoItemContent` → 정규식 `최소구매수량\s*(\d+)`
- 배송정보: `.lInfoDeli .lInfoItemContent`
- 상품명: `document.title.split('|')[0].trim()`

`poc/domeggook_crawl.py` 에 `DETAIL_JS`, `fetch_item_detail()` 추가.
실행 모드: `python poc/domeggook_crawl.py detail`

---

## pipeline/step3_product_search.py 정리

**User:** poc/ → pipeline/step3_product_search.py 정리해줘

변경사항:
- 하드코딩 제거 → `config` dict 인자
- 디버그 print 제거
- 죽은 코드(`TOTAL_JS`) 제거
- 공개 API: `run(keywords: list, config: dict) -> list[dict]`

```python
from pipeline.step3_product_search import run

products = run(
    keywords=["우산"],
    config={
        "domeggook_id": "...",
        "domeggook_pw": "...",
        "max_pages": 10,
        "fetch_detail": True,
    }
)
```

실행 결과: 2페이지 102개, 상세 포함 정상 수집.

---

## 방향 전환

**User:** 오너클랜은 일단 배제해. 도매꾹부터 시작해서 마지막 스텝까지 쭉 흘러가는지 해볼꺼야

- 오너클랜 배제, 도매꾹 기반 end-to-end 우선
- Claude API: 있음 → step5 하네스에 쓸 수 있으나 stub으로 시작 가능
- **현재 블로커: 셀러 계정** (쿠팡/스마트스토어) → 미확인

---

## 인증 정보

- 도매꾹 ID/PW: `pw/pw.md` 참고
- 세션 쿠키명: `ngm_sess`
