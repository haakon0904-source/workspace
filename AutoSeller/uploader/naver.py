"""
네이버 스마트스토어 상품 등록 업로더
- OAuth 2.0 인증 (HMAC-SHA256 서명)
- 상품 API: POST /v2/products

config 필수 키:
    naver_commerce_client_id      str  (커머스 API Client ID)
    naver_commerce_client_secret  str  (커머스 API Client Secret)
    naver_cs_phone                str  (A/S 연락처)
"""

import base64
import bcrypt
import time
import requests


BASE_URL = "https://api.commerce.naver.com/external"

_token_cache: dict = {}  # {"token": str, "expires_at": float}
_img_cache: dict = {}   # {original_url: naver_url}


def _get_token(config: dict) -> str:
    now = time.time()
    if _token_cache.get("token") and _token_cache.get("expires_at", 0) > now + 60:
        return _token_cache["token"]

    client_id = config["naver_commerce_client_id"]
    client_secret = config["naver_commerce_client_secret"]
    timestamp = int(now * 1000)

    password = f"{client_id}_{timestamp}"
    hashed = bcrypt.hashpw(password.encode("utf-8"), client_secret.encode("utf-8"))
    sign = base64.b64encode(hashed).decode("utf-8")

    resp = requests.post(
        f"{BASE_URL}/v1/oauth2/token",
        data={
            "grant_type": "client_credentials",
            "client_id": client_id,
            "timestamp": timestamp,
            "client_secret_sign": sign,
            "type": "SELF",
        },
        timeout=10,
    )
    data = resp.json()
    token = data.get("access_token")
    if not token:
        raise RuntimeError(f"네이버 커머스 토큰 발급 실패: {data}")

    _token_cache["token"] = token
    _token_cache["expires_at"] = now + data.get("expires_in", 3600)
    return token


def _request(method: str, path: str, token: str, body=None) -> requests.Response:
    return requests.request(
        method,
        BASE_URL + path,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        json=body,
        timeout=30,
    )


def _detect_mime(data: bytes) -> tuple[str, str]:
    """이미지 바이너리에서 MIME 타입과 확장자 감지."""
    if data[:2] == b"\xff\xd8":
        return "image/jpeg", "jpg"
    if data[:4] == b"\x89PNG":
        return "image/png", "png"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp", "webp"
    if data[:6] in (b"GIF87a", b"GIF89a"):
        return "image/gif", "gif"
    return "image/jpeg", "jpg"  # fallback


def _upload_image(url: str, token: str) -> str:
    """외부 이미지 URL → 네이버 서버에 업로드 후 naver URL 반환. 실패 시 원본 반환."""
    if not url:
        return url
    if url in _img_cache:
        return _img_cache[url]
    try:
        img_data = requests.get(url, timeout=15).content
        mime, ext = _detect_mime(img_data)
        resp = requests.post(
            BASE_URL + "/v1/product-images/upload",
            headers={"Authorization": f"Bearer {token}"},
            files={"imageFiles": (f"image.{ext}", img_data, mime)},
            timeout=30,
        )
        if resp.status_code == 200:
            naver_url = resp.json()["images"][0]["url"]
            _img_cache[url] = naver_url
            return naver_url
        print(f"[naver] 이미지 업로드 실패 {url[:60]}: {resp.status_code} {resp.text[:100]}")
    except Exception as e:
        print(f"[naver] 이미지 업로드 실패 {url[:60]}: {e}")
    return url


def _build_detail_html(product: dict) -> str:
    imgs = product.get("detail_imgs") or product.get("thumb_imgs") or []
    if not imgs and product.get("img_url"):
        imgs = [product["img_url"]]
    if imgs:
        return "\n".join(f'<img src="{u}" style="max-width:100%">' for u in imgs)
    return f'<p>{product.get("title", "상품")}</p>'


def _build_payload(product: dict, config: dict, token: str) -> dict:
    leaf_category_id = str(
        product.get("naver_leaf_category_id")
        or config.get("naver_leaf_category_id", "50000803")
    )
    sell_price = int(product.get("sell_price", 0))
    title = product["title"][:100]

    raw_imgs = product.get("thumb_imgs") or []
    if not raw_imgs and product.get("img_url"):
        raw_imgs = [product["img_url"]]
    imgs = [_upload_image(u, token) for u in raw_imgs[:5]]

    return {
        "originProduct": {
            "statusType": "SALE",
            "saleType": "NEW",
            "leafCategoryId": leaf_category_id,
            "name": title,
            "detailContent": _build_detail_html(product),
            "images": {
                "representativeImage": {"url": imgs[0]} if imgs else {"url": ""},
                "optionalImages": [{"url": u} for u in imgs[1:5]],
            },
            "salePrice": sell_price,
            "stockQuantity": 999,
            "deliveryInfo": {
                "deliveryType": "DELIVERY",
                "deliveryAttributeType": "NORMAL",
                "deliveryCompany": "CJGLS",
                "deliveryFee": {
                    "deliveryFeeType": "FREE",
                },
                "claimDeliveryInfo": {
                    "returnDeliveryCompanyPlatformType": "CJGLS",
                    "exchangeDeliveryCompanyPlatformType": "CJGLS",
                    "returnDeliveryFee": 3000,
                    "exchangeDeliveryFee": 6000,
                },
            },
            "detailAttribute": {
                "afterServiceInfo": {
                    "afterServiceTelephoneNumber": config.get("naver_cs_phone", "010-0000-0000"),
                    "afterServiceGuideContent": "제조사 A/S 기준을 따릅니다.",
                },
                "originAreaInfo": {
                    "originAreaCode": "0200037",
                    "content": "기타",
                    "importer": "해당없음",
                },
                "optionInfo": {
                    "simpleOptionSortType": "CREATE",
                    "optionCombinationGroupNames": {"optionGroupName1": "옵션"},
                    "optionCombinations": [
                        {
                            "optionName1": "기본",
                            "stockQuantity": 999,
                            "price": 0,
                            "usable": True,
                        }
                    ],
                },
                "minorPurchasable": True,
                "productInfoProvidedNotice": {
                    "productInfoProvidedNoticeType": "ETC",
                    "etc": {
                        "itemName": title[:50],
                        "modelName": "상품 상세페이지 참조",
                        "manufacturer": "상품 상세페이지 참조",
                        "returnCostReason": "상품 상세페이지 참조",
                        "noRefundReason": "상품 상세페이지 참조",
                        "qualityAssuranceStandard": "상품 상세페이지 참조",
                        "compensationProcedure": "상품 상세페이지 참조",
                        "troubleShootingContents": "상품 상세페이지 참조",
                        "afterServiceDirector": config.get("naver_cs_phone", "010-0000-0000"),
                    },
                },
            },
        },
        "smartstoreChannelProduct": {
            "naverShoppingRegistration": True,
            "channelProductDisplayStatusType": "ON",
        },
    }


def upload(product: dict, config: dict, token: str) -> dict:
    resp = _request("POST", "/v2/products", token, body=_build_payload(product, config, token))
    try:
        data = resp.json()
    except Exception:
        data = {}

    if resp.status_code in (200, 201):
        product_id = str(
            data.get("originProductNo")
            or data.get("smartstoreChannelProductNo", "")
        )
        return {"success": True, "product_id": product_id, "error": "", "platform": "naver"}

    msg = data.get("message") or resp.text[:300]
    return {"success": False, "product_id": "", "error": f"{resp.status_code}: {msg}", "platform": "naver"}


def run(products: list, config: dict) -> list:
    token = _get_token(config)
    results = []
    ok, fail = 0, 0

    for p in products:
        result = upload(p, config, token)
        results.append({**p, **result})
        if result["success"]:
            ok += 1
            print(f"[naver] ✓ {p['item_no']} | product_id={result['product_id']}")
        else:
            fail += 1
            print(f"[naver] ✗ {p['item_no']} | {result['error']}")
        time.sleep(0.3)

    print(f"[naver] 완료: 성공 {ok} / 실패 {fail}")
    return results
