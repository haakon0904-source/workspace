"""
쿠팡 WING 상품 등록 업로더
- HMAC-SHA256 인증
- 상품 API: POST /v2/providers/seller_api/apis/api/v1/marketplace/seller-products

config 필수 키:
    coupang_access_key   str
    coupang_secret_key   str
    coupang_vendor_id    str  (예: A01686065)
"""

import hashlib
import hmac
import json
import time
import requests
from datetime import datetime, timezone


BASE_URL = "https://api-gateway.coupang.com"


def _sign(method, path, access_key, secret_key):
    """HMAC-SHA256 서명 생성
    message = datetime + method + path_only + query_string (? 제외)
    """
    dt = datetime.now(timezone.utc).strftime("%y%m%dT%H%M%SZ")
    path_only, *q_parts = path.split("?")
    query = q_parts[0] if q_parts else ""
    message = dt + method + path_only + query
    signature = hmac.new(
        secret_key.encode("utf-8"),
        message.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    auth = f"CEA algorithm=HmacSHA256, access-key={access_key}, signed-date={dt}, signature={signature}"
    return auth


def _request(method, path, config, body=None):
    access_key = config["coupang_access_key"]
    secret_key = config["coupang_secret_key"]
    auth = _sign(method, path, access_key, secret_key)
    headers = {
        "Authorization": auth,
        "Content-Type": "application/json;charset=UTF-8",
    }
    url = BASE_URL + path
    resp = requests.request(method, url, headers=headers, json=body, timeout=30)
    return resp


def _build_contents(product: dict) -> list:
    """도매꾹 이미지를 쿠팡 상세설명(contents)으로 변환."""
    imgs = product.get("thumb_imgs") or []
    if not imgs and product.get("img_url"):
        imgs = [product["img_url"]]
    return [
        {
            "contentsType": "IMAGE_NO_SPACE",
            "contentDetails": [{"content": url, "detailType": "IMAGE"}],
        }
        for url in imgs
    ] if imgs else [
        {
            "contentsType": "TEXT",
            "contentDetails": [{"content": product.get("title", "상품"), "detailType": "TEXT"}],
        }
    ]


_NOTICES = [
    {"noticeCategoryName": "패션잡화(모자/벨트/액세서리 등)", "noticeCategoryDetailName": n, "content": "상품 상세페이지 참조"}
    for n in ["종류", "소재", "치수", "제조자(수입자)", "제조국", "취급시 주의사항", "품질보증기준", "A/S 책임자와 전화번호"]
]


def _build_product_payload(product: dict, config: dict) -> dict:
    """
    step5 통과 상품 → 쿠팡 상품 등록 payload 변환.

    config 추가 키:
        coupang_vendor_id           str
        coupang_vendor_user_id      str  (WING 로그인 아이디)
        coupang_outbound_place_code int  (출고지 코드)
        coupang_return_center_code  str  (반품지 코드)
        coupang_return_address      dict (반품지 주소 정보)
        coupang_display_category    int  (카테고리 코드, 기본 69884)
    """
    vendor_id = config["coupang_vendor_id"]
    vendor_user_id = config.get("coupang_vendor_user_id", vendor_id)
    outbound_code = config.get("coupang_outbound_place_code", 24710683)
    return_center = config.get("coupang_return_center_code", "1002607180")
    ra = config.get("coupang_return_address", {})
    category = product.get("display_category") or config.get("coupang_display_category", 69884)

    sell_price = product.get("sell_price", 0)
    free_ship = sell_price >= 30000

    images = []
    if product.get("img_url"):
        images = [{"imageOrder": 0, "imageType": "REPRESENTATION", "cdnPath": product["img_url"]}]

    return {
        "displayCategoryCode": category,
        "vendorId": vendor_id,
        "saleStartedAt": "2026-01-01T00:00:00",
        "saleEndedAt": "2099-12-31T00:00:00",
        "sellerProductName": product["title"][:100],
        "generalProductName": product["title"][:100],
        "productGroup": "일반상품",
        "deliveryMethod": "SEQUENCIAL",
        "deliveryCompanyCode": "CJGLS",
        "deliveryChargeType": "FREE" if free_ship else "NOT_FREE",
        "deliveryCharge": 0 if free_ship else 3000,
        "freeShipOverAmount": 30000,
        "deliveryChargeOnReturn": 3000,
        "unionDeliveryType": "NOT_UNION_DELIVERY",
        "remoteAreaDeliverable": "N",
        "outboundShippingPlaceCode": outbound_code,
        "returnCenterCode": return_center,
        "returnChargeName": ra.get("name", "반품지"),
        "companyContactNumber": ra.get("phone", ""),
        "returnZipCode": ra.get("zip", ""),
        "returnAddress": ra.get("address", ""),
        "returnAddressDetail": ra.get("address_detail", ""),
        "returnCharge": 3000,
        "requested": True,
        "vendorUserId": vendor_user_id,
        "items": [
            {
                "itemName": product["title"][:100],
                "originalPrice": sell_price,
                "salePrice": sell_price,
                "maximumBuyCount": 1000,
                "maximumBuyForPerson": 0,
                "maximumBuyForPersonPeriod": 1,
                "outboundShippingTimeDay": 2,
                "vendorItemName": product["title"][:100],
                "modelNo": product.get("item_no", ""),
                "externalVendorSku": product.get("item_no", ""),
                "adultOnly": "EVERYONE",
                "taxType": "TAX",
                "unitCount": 1,
                "overseasPurchased": "NOT_OVERSEAS_PURCHASED",
                "parallelImported": "NOT_PARALLEL_IMPORTED",
                "contents": _build_contents(product),
                "notices": _NOTICES,
                "attributes": [{"attributeTypeName": "색상", "attributeValueName": "기타"}],
                "images": images,
            }
        ],
    }


def upload(product: dict, config: dict) -> dict:
    """
    상품 1개 쿠팡 등록.

    Returns:
        {"success": bool, "product_id": str, "error": str}
    """
    path = "/v2/providers/seller_api/apis/api/v1/marketplace/seller-products"
    payload = _build_product_payload(product, config)

    resp = _request("POST", path, config, body=payload)

    try:
        data = resp.json() or {}
    except Exception:
        data = {}

    if resp.status_code in (200, 201) and data.get("code") == "SUCCESS":
        # data는 sellerProductId (int) 직접 반환
        product_id = str(data.get("data") or "")
        return {"success": True, "product_id": product_id, "error": "", "raw": resp.text[:300]}
    else:
        msg = data.get("message") or resp.text[:300]
        return {"success": False, "product_id": "", "error": f"{resp.status_code}: {msg}"}


def stop_sale(seller_product_id: int, config: dict) -> dict:
    """
    상품 판매중지.
    GET → items[].saleStatus = STOP_SELLING → PUT /seller-products
    Returns: {"success": bool, "error": str}
    """
    path = f"/v2/providers/seller_api/apis/api/v1/marketplace/seller-products/{seller_product_id}"
    resp = _request("GET", path, config)
    data = resp.json()
    if data.get("code") != "SUCCESS":
        return {"success": False, "error": data.get("message", "조회 실패")}

    product = data["data"]
    for item in product.get("items", []):
        item["saleStatus"] = "STOP_SELLING"

    put_path = "/v2/providers/seller_api/apis/api/v1/marketplace/seller-products"
    r2 = _request("PUT", put_path, config, body=product)
    d2 = r2.json()
    if d2.get("code") == "SUCCESS":
        return {"success": True, "error": ""}
    return {"success": False, "error": d2.get("message", "판매중지 실패")}


def fetch_all_products(config: dict) -> list:
    """
    쿠팡에 등록된 전체 상품 목록 조회.
    Returns: list of {sellerProductId, sellerProductName, statusName, externalVendorSku}
    """
    vendor_id = config["coupang_vendor_id"]
    result = []
    for status in ("APPROVED", "DRAFT", "UNDER_REVIEW"):
        path = (f"/v2/providers/seller_api/apis/api/v1/marketplace/seller-products"
                f"?vendorId={vendor_id}&maxPerPage=100&status={status}")
        resp = _request("GET", path, config)
        data = resp.json()
        if data.get("code") == "SUCCESS":
            for p in data.get("data", []):
                sku = ""
                if p.get("items"):
                    sku = p["items"][0].get("externalVendorSku", "")
                result.append({
                    "seller_product_id": p["sellerProductId"],
                    "coupang_status": p.get("statusName", ""),
                    "item_no": sku,
                })
    return result


def fetch_category_commission(category_code: int, config: dict) -> float:
    """
    쿠팡 카테고리 수수료율 조회.
    Returns: float (예: 0.108), 실패 시 config['commission_rate'] 반환
    """
    path = f"/v2/providers/seller_api/apis/api/v1/marketplace/meta/category-related-metas/display-categories/{category_code}"
    resp = _request("GET", path, config)
    try:
        data = resp.json()
        rate = data.get("data", {}).get("commissionRate")
        if rate is not None:
            return float(rate) / 100  # 퍼센트 → 소수
    except Exception:
        pass
    return config.get("commission_rate", 0.1)


def run(products: list, config: dict) -> list:
    """
    상품 목록 쿠팡 일괄 등록.

    Returns:
        list[dict]: 각 상품 등록 결과 (product + success/product_id/error)
    """
    results = []
    ok, fail = 0, 0

    for p in products:
        result = upload(p, config)
        results.append({**p, **result})
        if result["success"]:
            ok += 1
            print(f"[coupang] ✓ {p['item_no']} | product_id={result['product_id']}")
        else:
            fail += 1
            print(f"[coupang] ✗ {p['item_no']} | {result['error']}")
        time.sleep(0.5)  # API rate limit 대비

    print(f"[coupang] 완료: 성공 {ok} / 실패 {fail}")
    return results
