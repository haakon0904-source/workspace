"""
도매꾹 자동 주문 (드랍쉬핑)
- 쿠팡 주문 정보를 받아 도매꾹에 자동 주문
- 수령인: 쿠팡 구매자 주소로 직접 배송

결제 방식 config 키:
    domeggook_pay_method: "emoney" (꾹페이) | "vaccount" (가상계좌)
    기본값: vaccount (가상계좌 - 수동 이체 필요)
    완전 자동화: emoney 선택 후 꾹페이 충전 필요
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


def _split_phone(phone: str) -> tuple[str, str, str]:
    """010-1234-5678 → ('010','1234','5678')"""
    digits = re.sub(r"\D", "", phone)
    if len(digits) == 11:  # 010-xxxx-xxxx
        return digits[:3], digits[3:7], digits[7:]
    if len(digits) == 10:  # 02-xxxx-xxxx
        return digits[:3], digits[3:6], digits[6:]
    return digits[:3], digits[3:7], digits[7:] if len(digits) >= 10 else ("010", "0000", "0000")


async def _select_option(page) -> bool:
    """첫 번째 구매 가능한 옵션 선택. 옵션 없으면 True 반환."""
    btn = await page.query_selector(".pOptSelectList .pSelectUIBtn button")
    if not btn:
        return True  # 옵션 없음

    await btn.click()
    await asyncio.sleep(0.3)

    first = await page.query_selector(
        ".pOptSelectList .pSelectUIMenu li:not(.pDisabled):not(.pTitleItem)"
    )
    if not first:
        return False

    text = await first.inner_text()
    print(f"[domeggook_order] 옵션 선택: {text.strip()[:40]}")
    await first.click()
    await asyncio.sleep(0.5)
    return True


async def _navigate_to_order_form(page, item_no: str) -> bool:
    """상품 페이지 → 옵션 선택 → 구매하기 → my_orderInfoForm.php 이동."""
    await page.goto(f"https://domeggook.com/{item_no}", wait_until="domcontentloaded", timeout=60000)

    try:
        await page.wait_for_selector("#lPayBtnBuy, #lOptBtnBuy", timeout=10000)
    except Exception:
        return False

    await asyncio.sleep(1)

    # dialog 처리
    page.on("dialog", lambda d: asyncio.ensure_future(d.accept()))

    # 옵션 선택
    ok = await _select_option(page)
    if not ok:
        print("[domeggook_order] 구매 가능한 옵션 없음")
        return False

    # 구매하기 (JS 직접 호출)
    await page.evaluate("lAddCart('ORDER')")

    try:
        await page.wait_for_url("**/my_orderInfoForm.php**", timeout=15000)
        await asyncio.sleep(1)
        return True
    except Exception:
        print(f"[domeggook_order] 주문 폼 이동 실패. 현재: {page.url}")
        return False


async def _fill_order_form(page, order: dict, pay_method: str = "vaccount", birth: str = ""):
    """배송지 입력 + 결제 방식 선택."""
    name = order.get("buyer_name", "")
    phone = order.get("buyer_phone", "").replace("-", "")
    addr = order.get("addr", "")
    addr_detail = order.get("addr_detail", "")
    zipcode = order.get("zip", "")

    m1, m2, m3 = _split_phone(phone)

    # 직접 입력 라디오 + 직접입력 허용 체크박스 (JS 클릭)
    await page.evaluate("""
        () => {
            const r = document.getElementById('addressBookSetWrite');
            if (r) r.click();
            const w = document.getElementById('lPayWritableAddress');
            if (w && !w.checked) w.click();
        }
    """)
    await asyncio.sleep(0.5)

    # JS로 직접 값 설정 (readonly 필드 우회)
    await page.evaluate(f"""
        () => {{
            function setVal(sel, val) {{
                const el = document.querySelector(sel);
                if (!el) return;
                el.removeAttribute('readonly');
                el.removeAttribute('disabled');
                el.value = val;
                el.dispatchEvent(new Event('change', {{bubbles: true}}));
                el.dispatchEvent(new Event('input', {{bubbles: true}}));
            }}
            setVal("input[name='get_name']", {repr(name)});
            setVal("input[name='get_zipcode']", {repr(zipcode)});
            setVal("input[name='get_address1']", {repr(addr)});
            setVal("input[name='get_address2']", {repr(addr_detail)});
            setVal("input[name='home_mobile2']", {repr(m2)});
            setVal("input[name='home_mobile3']", {repr(m3)});
        }}
    """)

    # 휴대폰 앞자리 select
    sel = await page.query_selector("select[name='home_mobile1']")
    if sel:
        try:
            await sel.select_option(m1)
        except Exception:
            await page.evaluate(f"document.querySelector(\"select[name='home_mobile1']\").value = '{m1}'")

    # 보증보험 생년월일 입력 (YYMMDD → 19XX 연도로 변환)
    if birth and len(birth) >= 6:
        yy = birth[:2]
        mm = birth[2:4]
        dd = birth[4:6]
        full_year = f"19{yy}" if int(yy) >= 0 else f"20{yy}"
        await page.evaluate(f"""
            () => {{
                function setVal(sel, val) {{
                    const el = document.querySelector(sel);
                    if (!el) return;
                    el.value = val;
                    el.dispatchEvent(new Event('change', {{bubbles: true}}));
                }}
                setVal("input[name='insuYear']", '{full_year}');
                setVal("input[name='insuName']", document.querySelector("input[name='get_name']")?.value || '');
            }}
        """)
        # select month/day
        try:
            await page.select_option("select[name='insuMonth']", mm.lstrip("0") or "1")
        except Exception:
            pass
        try:
            await page.select_option("select[name='insuDay']", dd.lstrip("0") or "1")
        except Exception:
            pass
        # 성별 (radio 첫번째 = 남성)
        await page.evaluate("""
            () => {
                const r = document.querySelector("input[name='insuSex']");
                if (r) r.click();
            }
        """)
    await asyncio.sleep(0.2)

    # 결제 방식 + 동의 체크박스 (JS 일괄 처리)
    method_map = {"vaccount": 0, "transfer": 1, "emoney": 2, "card": 3}
    method_idx = method_map.get(pay_method, 0)
    await page.evaluate(f"""
        () => {{
            // 결제 방식 선택
            const radios = document.querySelectorAll("input[name='method']");
            if (radios[{method_idx}]) radios[{method_idx}].click();

            // 동의 체크박스 전체 체크
            document.querySelectorAll("input[type='checkbox']").forEach(c => {{
                const n = c.name || c.id || '';
                if (n.includes('agree') || c.id === 'agreeChkInputId') {{
                    if (!c.checked) c.click();
                }}
            }});
        }}
    """)
    await asyncio.sleep(0.3)


async def _submit_and_get_order_no(page) -> str:
    """결제 버튼 클릭 후 주문번호 추출."""
    # JS 클릭 (visibility 무관)
    await page.evaluate("document.getElementById('paymentBtn').click()")
    await asyncio.sleep(3)

    # Toss Payments 가상계좌: 은행 선택 팝업 처리 (국민은행 선택)
    for attempt in range(10):
        await asyncio.sleep(1)
        # 은행 선택 버튼 탐색
        bank_btn = await page.query_selector("button:has-text('국민'), [class*='bank']:has-text('국민')")
        if not bank_btn:
            # 다른 방식으로 탐색
            btns = await page.query_selector_all("button")
            for btn in btns:
                try:
                    text = (await btn.inner_text()).strip()
                    if text in ("국민", "KB국민"):
                        bank_btn = btn
                        break
                except Exception:
                    pass
        if bank_btn:
            print("[domeggook_order] 가상계좌 은행 선택: 국민")
            await page.evaluate("el => el.click()", bank_btn)
            await asyncio.sleep(5)
            break
        # 이미 다음 페이지로 넘어갔으면 중단
        if "orderInfoForm" not in page.url:
            break

    try:
        await page.wait_for_url(
            re.compile(r"(orderEnd|order_end|orderIng|complete|done|result|myBuy/order(?!/my_order))"),
            timeout=20000,
        )
    except Exception:
        await asyncio.sleep(3)

    current_url = page.url
    content = await page.content()

    # 주문번호 추출 패턴
    for pattern in [r"주문번호[^\d]*(\d{6,20})", r"ordNo=(\d+)", r"ord_no=(\d+)",
                    r"orderNo[^0-9]*(\d+)"]:
        m = re.search(pattern, content)
        if m:
            return m.group(1)

    m = re.search(r"[?&](ord_no|ordNo|orderNo)=(\d+)", current_url)
    if m:
        return m.group(2)

    # 주문 완료 텍스트 확인
    if any(kw in content for kw in ["주문이 완료", "주문완료", "결제가 완료", "주문 접수", "가상계좌"]):
        return "ORDER_OK"

    return ""


async def _order_item(page, order: dict, pay_method: str, birth: str = "") -> dict:
    """도매꾹 상품 1건 주문."""
    item_no = order["item_no"]

    print(f"[domeggook_order]   상품 페이지 이동: {item_no}")
    ok = await _navigate_to_order_form(page, item_no)
    if not ok:
        return {"success": False, "domeggook_order": "", "error": "주문 폼 이동 실패"}

    print(f"[domeggook_order]   배송지 입력: {order.get('buyer_name')} / {order.get('addr','')[:30]}")
    await _fill_order_form(page, order, pay_method, birth)

    print("[domeggook_order]   결제 진행...")
    order_no = await _submit_and_get_order_no(page)
    if order_no:
        return {"success": True, "domeggook_order": order_no, "error": ""}
    return {"success": False, "domeggook_order": "", "error": "결제 완료 확인 실패"}


async def _run_orders(orders: list[dict], config: dict) -> list[dict]:
    domeggook_id = config["domeggook_id"]
    domeggook_pw = config["domeggook_pw"]
    pay_method = config.get("domeggook_pay_method", "vaccount")
    birth = config.get("domeggook_birth", "")

    results = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(user_agent=UA)

        if not await _login(page, domeggook_id, domeggook_pw):
            raise RuntimeError("도매꾹 로그인 실패")
        print("[domeggook_order] 로그인 성공")

        for order in orders:
            print(f"[domeggook_order] 주문: {order['item_no']} x{order.get('qty',1)}"
                  f" → {order.get('buyer_name')}")
            try:
                result = await _order_item(page, order, pay_method, birth)
            except Exception as e:
                result = {"success": False, "domeggook_order": "", "error": str(e)}

            result["order_id"] = order.get("order_id")
            result["ordersheet_id"] = order.get("ordersheet_id")
            results.append(result)

            if result["success"]:
                print(f"[domeggook_order] 완료: {result['domeggook_order']}")
            else:
                print(f"[domeggook_order] 실패: {result['error'][:120]}")

        await browser.close()

    return results


def place_orders(orders: list[dict], config: dict) -> list[dict]:
    """
    도매꾹에 주문 일괄 실행.

    Args:
        orders: [{order_id, ordersheet_id, item_no, qty,
                  buyer_name, buyer_phone, addr, addr_detail, zip}]
        config: domeggook_id, domeggook_pw, domeggook_pay_method 포함

    Returns:
        [{order_id, ordersheet_id, success, domeggook_order, error}]
    """
    return asyncio.run(_run_orders(orders, config))
