"""
도매꾹 자동 주문 (드랍쉬핑)
- 쿠팡 주문 정보를 받아 도매꾹에 자동 주문
- 수령인: 쿠팡 구매자 주소로 직접 배송
"""

import asyncio
import re
from playwright.async_api import async_playwright

UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)


async def _login(page, domeggook_id: str, domeggook_pw: str) -> bool:
    await page.goto(
        "https://domeggook.com/ssl/member/mem_loginForm.php",
        wait_until="domcontentloaded",
    )
    hidden = {}
    for inp in await page.query_selector_all("input[type='hidden']"):
        name = await inp.get_attribute("name")
        value = await inp.get_attribute("value") or ""
        if name:
            hidden[name] = value

    response = await page.request.post(
        "https://domeggook.com/main/member/mem_ing.php",
        form={**hidden, "id": domeggook_id, "pass": domeggook_pw},
    )
    raw = await response.body()
    body = raw.decode("cp949", errors="replace")
    if "로그아웃" in body or 'is_member: "y"' in body:
        return True

    await page.goto("https://domeggook.com/", wait_until="domcontentloaded")
    content = await page.content()
    return "로그아웃" in content or 'is_member: "y"' in content


async def _order_item(page, order: dict) -> dict:
    """
    도매꾹 상품 1건 주문.
    order 필드: item_no, qty, buyer_name, buyer_phone, addr, addr_detail, zip
    반환: {"success": bool, "domeggook_order": str, "error": str}
    """
    item_no = order["item_no"]
    qty = order.get("qty", 1)

    # 상품 페이지 이동
    await page.goto(f"https://domeggook.com/{item_no}", wait_until="domcontentloaded", timeout=60000)

    try:
        await page.wait_for_selector("#lThumbImg", timeout=10000)
    except Exception:
        return {"success": False, "domeggook_order": "", "error": "상품 페이지 로드 실패"}

    # 수량 설정
    qty_input = await page.query_selector("input[name='cnt']")
    if qty_input:
        await qty_input.triple_click()
        await qty_input.type(str(qty))

    # 바로구매 버튼
    buy_btn = await page.query_selector("#lBuyNow, .lBuyNow, a[onclick*='buyNow'], a[href*='buyNow']")
    if not buy_btn:
        # 대안: 장바구니 후 구매 시도
        buy_btn = await page.query_selector("#lCart, .btn_buy, a.lBuyBtn")
    if not buy_btn:
        return {"success": False, "domeggook_order": "", "error": "구매 버튼 없음"}

    await buy_btn.click()
    await page.wait_for_load_state("domcontentloaded")
    await asyncio.sleep(1)

    # 배송지 입력 폼 탐색
    current_url = page.url
    if "order" not in current_url and "cart" not in current_url and "buy" not in current_url:
        return {"success": False, "domeggook_order": "", "error": f"주문 페이지 미이동: {current_url}"}

    # 배송지 폼 채우기
    filled = await _fill_shipping_form(page, order)
    if not filled:
        return {"success": False, "domeggook_order": "", "error": "배송지 입력 실패"}

    # 결제 진행
    order_no = await _proceed_payment(page)
    if order_no:
        return {"success": True, "domeggook_order": order_no, "error": ""}
    return {"success": False, "domeggook_order": "", "error": "결제 완료 확인 실패"}


async def _fill_shipping_form(page, order: dict) -> bool:
    """배송지 정보 입력."""
    name = order.get("buyer_name", "")
    phone = order.get("buyer_phone", "").replace("-", "")
    addr = order.get("addr", "")
    addr_detail = order.get("addr_detail", "")
    zipcode = order.get("zip", "")

    # 이름
    for sel in ["input[name='rName']", "input[name='name']", "#rName"]:
        el = await page.query_selector(sel)
        if el:
            await el.triple_click()
            await el.type(name)
            break

    # 전화번호
    for sel in ["input[name='rPhone']", "input[name='phone']", "#rPhone", "input[name='mobile']"]:
        el = await page.query_selector(sel)
        if el:
            await el.triple_click()
            await el.type(phone)
            break

    # 우편번호 (다음 주소 API 팝업 대신 직접 입력 시도)
    for sel in ["input[name='rZip']", "input[name='zip']", "#rZip", "input[name='zipcode']"]:
        el = await page.query_selector(sel)
        if el:
            await el.triple_click()
            await el.type(zipcode)
            break

    # 주소
    for sel in ["input[name='rAddr1']", "input[name='addr1']", "#rAddr1"]:
        el = await page.query_selector(sel)
        if el:
            await el.triple_click()
            await el.type(addr)
            break

    # 상세주소
    for sel in ["input[name='rAddr2']", "input[name='addr2']", "#rAddr2"]:
        el = await page.query_selector(sel)
        if el:
            await el.triple_click()
            await el.type(addr_detail)
            break

    return True


async def _proceed_payment(page) -> str:
    """결제 버튼 클릭 후 주문번호 추출. 성공 시 주문번호 반환."""
    # 결제하기 버튼
    for sel in ["button[type='submit'].pay", "#payBtn", "input[value*='결제']",
                "a[onclick*='pay']", "button:has-text('결제')", ".btn_pay"]:
        btn = await page.query_selector(sel)
        if btn:
            await btn.click()
            break
    else:
        # 텍스트 기반 검색
        btns = await page.query_selector_all("button, input[type='submit'], input[type='button']")
        for btn in btns:
            text = await btn.inner_text() if await btn.get_attribute("type") != "hidden" else ""
            if "결제" in text or "주문" in text:
                await btn.click()
                break

    # 주문 완료 대기
    try:
        await page.wait_for_url(re.compile(r"(orderEnd|order_end|complete|done)"), timeout=15000)
    except Exception:
        await asyncio.sleep(3)

    # 주문번호 추출
    content = await page.content()
    m = re.search(r"주문번호[^\d]*(\d{6,20})", content)
    if m:
        return m.group(1)

    # URL에서도 시도
    url = page.url
    m = re.search(r"order[_]?no=(\d+)", url)
    if m:
        return m.group(1)

    # 주문완료 텍스트만 있어도 임시 번호 반환
    if "주문" in content and ("완료" in content or "감사" in content):
        return "UNKNOWN"

    return ""


async def _run_orders(orders: list[dict], config: dict) -> list[dict]:
    domeggook_id = config["domeggook_id"]
    domeggook_pw = config["domeggook_pw"]

    results = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(user_agent=UA)

        if not await _login(page, domeggook_id, domeggook_pw):
            raise RuntimeError("도매꾹 로그인 실패")
        print("[domeggook_order] 로그인 성공")

        for order in orders:
            print(f"[domeggook_order] 주문 시도: {order['item_no']} x{order.get('qty',1)} → {order.get('buyer_name')}")
            result = await _order_item(page, order)
            result["order_id"] = order.get("order_id")
            result["ordersheet_id"] = order.get("ordersheet_id")
            results.append(result)
            if result["success"]:
                print(f"[domeggook_order] 주문 완료: {result['domeggook_order']}")
            else:
                print(f"[domeggook_order] 주문 실패: {result['error']}")

        await browser.close()

    return results


def place_orders(orders: list[dict], config: dict) -> list[dict]:
    """
    도매꾹에 주문 일괄 실행.

    Args:
        orders: [{order_id, ordersheet_id, item_no, qty,
                  buyer_name, buyer_phone, addr, addr_detail, zip}]
        config: domeggook_id, domeggook_pw 포함

    Returns:
        [{order_id, ordersheet_id, success, domeggook_order, error}]
    """
    return asyncio.run(_run_orders(orders, config))
