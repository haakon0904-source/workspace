"""
Step 4: 마진 계산
- step3 결과(상품 목록)를 받아 마진 계산 후 기준 미달 상품 제거
- 실행: python pipeline/step4_margin.py

config 필수 키:
    sell_price_multiplier  float  도매가 대비 판매가 배수 (예: 2.5 → 250%)
    commission_rate        float  플랫폼 수수료율 (예: 0.078 → 7.8%)
    delivery_fee           int    나의 배송비 (원, 예: 2500)
    vat_rate               float  부가세율 (기본 0.1 → 10%)
    min_margin_rate        float  최소 마진율 (예: 0.2 → 20%)
    min_profit             int    최소 순이익 (원, 예: 1000)

마진 공식 (돈버는하마 마진계산기 기준):
    수수료      = 판매가 × 수수료율
    세전이익    = 판매가 - 원가 - 배송비 - 수수료
    부가세      = 세전이익 × 부가세율(10%)
    순이익(마진) = 세전이익 - 부가세  (= 세전이익 × 0.9)
    마진율      = 순이익 / 판매가
"""


def _calc(product: dict, config: dict) -> dict:
    """상품 1개 마진 계산. 결과 필드 추가한 dict 반환."""
    buy_price = product["price"]           # 도매가
    multiplier = config["sell_price_multiplier"]
    delivery = config["delivery_fee"]
    vat_rate = config.get("vat_rate", 0.1)

    # 키워드별 수수료율·카테고리 코드
    keyword_rates = config.get("keyword_commission_rates", {})
    commission = keyword_rates.get(product.get("keyword"), config.get("commission_rate", 0.1))
    display_category = config.get("keyword_display_categories", {}).get(
        product.get("keyword"), config.get("coupang_display_category", 69884)
    )

    sell_price = int(buy_price * multiplier / 10) * 10  # 10원 단위 절사
    commission_fee = sell_price * commission
    pre_tax = sell_price - buy_price - delivery - commission_fee
    vat = pre_tax * vat_rate
    profit = pre_tax - vat                 # = pre_tax * (1 - vat_rate)
    margin_rate = profit / sell_price if sell_price > 0 else 0

    return {
        **product,
        "sell_price": sell_price,
        "display_category": display_category,
        "commission_rate": commission,
        "commission_fee": round(commission_fee),
        "delivery_fee": delivery,
        "vat": round(vat),
        "profit": round(profit),
        "margin_rate": round(margin_rate, 4),
    }


# 상품명에 포함 시 제외할 키워드 (브랜드/정품/가품 리스크)
_EXCLUDE_KEYWORDS = ["정품", "브랜드", "AS가능", "A/S", "공식", "인증", "특허"]

# 착불/배송비 관련 제외 패턴
_EXCLUDE_DELIVERY = ["착불", "화물"]


def _prefilter(products: list, config: dict) -> tuple[list, int]:
    """마진 계산 전 규칙 기반 필터링."""
    min_price = config.get("filter_min_price", 3000)
    max_price = config.get("filter_max_price", 30000)
    max_min_qty = config.get("filter_max_min_qty", 3)

    passed, excluded = [], 0
    for p in products:
        price = p.get("price", 0)
        min_qty = p.get("min_qty", 1)
        title = p.get("title", "")
        delivery = p.get("delivery", "") or ""
        img = p.get("img_url", "")

        # 이미지 없는 상품 제외
        if not img:
            excluded += 1; continue

        # 도매가 범위 필터
        if not (min_price <= price <= max_price):
            excluded += 1; continue

        # 최소구매수량 필터
        if min_qty > max_min_qty:
            excluded += 1; continue

        # 브랜드/정품 키워드 포함 상품 제외
        if any(kw in title for kw in _EXCLUDE_KEYWORDS):
            excluded += 1; continue

        # 착불 배송 제외
        if any(kw in delivery for kw in _EXCLUDE_DELIVERY):
            excluded += 1; continue

        passed.append(p)

    print(f"[step4] 프리필터: {len(products)}개 → {len(passed)}개 (제외 {excluded}개)")
    return passed, excluded


def run(products: list, config: dict) -> list:
    """
    마진 계산 후 기준 통과 상품만 반환.

    Returns:
        list[dict]: 기준 통과 상품 (sell_price, profit, margin_rate 필드 추가)
    """
    products, _ = _prefilter(products, config)

    min_margin = config.get("min_margin_rate", 0.2)
    min_profit = config.get("min_profit", 1000)

    result = []
    filtered = 0
    for p in products:
        if not p.get("price"):
            filtered += 1
            continue
        m = _calc(p, config)
        if m["margin_rate"] >= min_margin and m["profit"] >= min_profit:
            result.append(m)
        else:
            filtered += 1

    print(f"[step4] {len(products)}개 → 통과 {len(result)}개 (제외 {filtered}개)")
    return result


if __name__ == "__main__":
    import json

    # step3 결과 샘플로 테스트
    sample = [
        {"source": "domeggook", "keyword": "우산", "item_no": "13187678",
         "title": "우산 3단자동", "price": 2900, "min_qty": 2},
        {"source": "domeggook", "keyword": "우산", "item_no": "53554992",
         "title": "캡슐우산 5단", "price": 3600, "min_qty": 2},
        {"source": "domeggook", "keyword": "우산", "item_no": "10708086",
         "title": "카본 경량 우산", "price": 8500, "min_qty": 1},  # 통과 예상
        {"source": "domeggook", "keyword": "우산", "item_no": "99999999",
         "title": "초저가 우산", "price": 500, "min_qty": 10},
    ]
    _config = {
        "sell_price_multiplier": 2.5,
        "commission_rate": 0.108,   # 쿠팡 생활/잡화 평균
        "delivery_fee": 3000,
        "min_margin_rate": 0.2,
        "min_profit": 1000,
    }
    passed = run(sample, _config)
    for p in passed:
        print(json.dumps({
            k: p[k] for k in ("item_no", "title", "price", "sell_price", "profit", "margin_rate")
        }, ensure_ascii=False))
