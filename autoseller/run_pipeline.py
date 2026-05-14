"""
AutoSeller 전체 파이프라인 실행
step3 → step4 → step5 → step6

실행: python run_pipeline.py
"""

import re
from pathlib import Path

from pipeline import (
    step3_product_search,
    step4_margin,
    step5_register,
    step6_upload,
)
from uploader.coupang_commission import get_rate


_ROOT = Path(__file__).parent


def _load_pw():
    text = open(_ROOT / "pw/pw.md").read()
    lines = text.splitlines()
    coupang_id = next((l.split(":",1)[1].strip() for l in lines if l.startswith("Access Key")), "")
    coupang_secret = next((l.split(":",1)[1].strip() for l in lines if l.startswith("Secret Key")), "")
    domeggook_id = lines[0].strip()
    domeggook_pw = lines[1].strip()
    return domeggook_id, domeggook_pw, coupang_id, coupang_secret


_dmk_id, _dmk_pw, _cpg_key, _cpg_secret = _load_pw()

CONFIG = {
    # 도매꾹
    "domeggook_id": _dmk_id,
    "domeggook_pw": _dmk_pw,
    "max_pages": 2,
    "fetch_detail": True,

    # 마진 (돈버는하마 마진계산기 기준)
    "sell_price_multiplier": 2.5,
    "commission_rate": 0.078,   # 쿠팡 수수료율
    "delivery_fee": 2500,       # 나의 배송비
    "vat_rate": 0.1,            # 부가세 10%
    "min_margin_rate": 0.2,
    "min_profit": 1000,

    # DB
    "db_path": str(_ROOT / "db/autoseller.db"),

    # 쿠팡
    "coupang_vendor_id": "A01686065",
    "coupang_access_key": _cpg_key,
    "coupang_secret_key": _cpg_secret,
    "coupang_vendor_user_id": "todaybd17",
    "coupang_outbound_place_code": 24710683,
    "coupang_return_center_code": "1002607180",
    "coupang_return_address": {
        "name": "반품 집",
        "phone": "010-7734-9987",
        "zip": "12915",
        "address": "경기도 하남시 미사강변서로 127",
        "address_detail": "1816-1501",
    },
    "coupang_display_category": 69884,
}

# 키워드 → 쿠팡 카테고리 매핑
# display_category: WING 상품등록 화면에서 확인
# commission: (대분류, 중분류, 소분류) — coupang_commission.get_rate() 인자
KEYWORD_CATEGORIES = {
    "우산": {
        "display_category": 69884,           # 남녀공용2단우산
        "commission": ("패션", "패션잡화"),   # 10.5%
    },
}

KEYWORDS = list(KEYWORD_CATEGORIES.keys())


def _resolve_keyword_config(config: dict) -> tuple[dict, dict]:
    """키워드별 수수료율·카테고리 코드 반환. ({keyword: rate}, {keyword: display_category})"""
    rates = {}
    categories = {}
    for keyword, info in KEYWORD_CATEGORIES.items():
        rate = get_rate(*info["commission"])
        rates[keyword] = rate
        categories[keyword] = info["display_category"]
        print(f"[config] {keyword}: 카테고리={info['display_category']}, 수수료={rate*100:.1f}%")
    return rates, categories


# 하위 호환 (web/app.py에서 사용)
def _resolve_commission_rates(config: dict) -> dict:
    rates, _ = _resolve_keyword_config(config)
    return rates


def main():
    print("=" * 50)
    print("AutoSeller 파이프라인 시작")
    print("=" * 50)

    # 키워드별 수수료율·카테고리 조회
    print("\n[Config] 카테고리별 수수료율 조회")
    commission_rates, display_categories = _resolve_keyword_config(CONFIG)
    CONFIG["keyword_commission_rates"] = commission_rates
    CONFIG["keyword_display_categories"] = display_categories

    # Step 3: 상품 서치
    print("\n[Step 3] 도매꾹 상품 수집")
    products = step3_product_search.run(KEYWORDS, CONFIG)
    if not products:
        print("수집된 상품 없음. 종료.")
        return

    # Step 4: 마진 계산
    print("\n[Step 4] 마진 계산")
    products = step4_margin.run(products, CONFIG)
    if not products:
        print("마진 기준 통과 상품 없음. 종료.")
        return

    # Step 5: DB 저장 + 하네스
    print("\n[Step 5] DB 저장 + 하네스 검증")
    products = step5_register.run(products, CONFIG)
    if not products:
        print("하네스 통과 상품 없음. 종료.")
        return

    # Step 6: 쿠팡 업로드
    print("\n[Step 6] 쿠팡 업로드")
    results = step6_upload.run(products, CONFIG)

    success = [r for r in results if r.get("success")]
    print(f"\n{'=' * 50}")
    print(f"파이프라인 완료: {len(success)}/{len(results)}개 등록 성공")
    print("=" * 50)


if __name__ == "__main__":
    main()
