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
    if len(digits) == 12:  # 050x-xxxx-xxxx (VoIP)
        return digits[:4], digits[4:8], digits[8:]
    if len(digits) == 10:  # 02-xxxx-xxxx
        return digits[:2], digits[2:6], digits[6:]
    if len(digits) >= 10:
        return digits[:3], digits[3:7], digits[7:]
    return "010", "0000", "0000"


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
    await asyncio.sleep(2)

    # 장바구니 페이지로 경유된 경우 → 하단 주문하기 버튼 클릭
    if "Cart" in page.url or "cart" in page.url.lower():
        print(f"[domeggook_order] 장바구니 경유 감지 ({page.url}) → 주문하기 클릭")
        try:
            btns = page.locator("a:has-text('주문하기'), button:has-text('주문하기')")
            count = await btns.count()
            print(f"[domeggook_order] 주문하기 버튼 {count}개 발견")
            if count > 0:
                await btns.last.click()
                await asyncio.sleep(1)
        except Exception as e:
            print(f"[domeggook_order] 주문하기 클릭 실패: {e}")

    try:
        await page.wait_for_url("**/my_orderInfoForm.php**", timeout=15000)
        await page.wait_for_load_state("networkidle", timeout=10000)
        await asyncio.sleep(2)
        return True
    except Exception:
        print(f"[domeggook_order] 주문 폼 이동 실패. 현재: {page.url}")
        return False


async def _fill_order_form(page, order: dict, pay_method: str = "vaccount", birth: str = "", biz_no: str = ""):
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

    # 이머니 전액사용 (결제방식 변경 전에 먼저 - 꾹페이 선택하면 이머니 섹션 사라짐)
    if pay_method == "emoney":
        try:
            result = await page.evaluate("""
                () => {
                    const types = ['emoney', 'cash', 'eMoney', 'EMONEY'];
                    for (const t of types) {
                        try {
                            if (typeof AssetManager !== 'undefined' && AssetManager.useAll) {
                                AssetManager.useAll(t);
                                return 'AssetManager.useAll(' + t + ')';
                            }
                        } catch(e) {}
                    }
                    const ths = Array.from(document.querySelectorAll('th'));
                    for (const th of ths) {
                        if (th.textContent.includes('이머니사용')) {
                            const img = th.closest('tr')?.querySelector('img[onclick]');
                            if (img) { img.click(); return 'IMG 클릭'; }
                        }
                    }
                    return null;
                }
            """)
            print(f"[domeggook_order] 이머니 전액사용: {result}")
            await asyncio.sleep(0.5)
        except Exception as e:
            print(f"[domeggook_order] 이머니 전액사용 실패: {e}")

    # 결제방식 선택 (emoney는 가상계좌 유지 - 이머니 전액사용으로 0원 처리)
    if pay_method != "emoney":
        pay_label = {"vaccount": "가상계좌", "transfer": "실시간", "card": "신용카드"}
        label_text = pay_label.get(pay_method, "가상계좌")
        try:
            await page.locator(f"label:has-text('{label_text}')").first.click(timeout=3000)
            print(f"[domeggook_order] 결제방식 선택: {label_text}")
        except Exception as e:
            print(f"[domeggook_order] 결제방식 선택 실패: {e}")
        await asyncio.sleep(0.5)

    # 현금영수증 사업자지출증빙
    if biz_no:
        biz_no_clean = biz_no.replace("-", "")
        try:
            await page.evaluate("""
                () => {
                    const r = document.querySelector("input[name='cashReceiptType'][value='2']");
                    if (r) r.click();
                }
            """)
            await asyncio.sleep(1)  # 동적 입력창 출현 대기

            # 사업자번호 3분할(XXX-XX-XXXXX) → cashReceiptComType 내 3개 입력 필드에 설정
            b1, b2, b3 = biz_no_clean[:3], biz_no_clean[3:5], biz_no_clean[5:]
            await page.evaluate(f"""
                () => {{
                    const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
                    const div = document.getElementById('cashReceiptComType');
                    if (div) {{
                        const active = Array.from(div.querySelectorAll("input[type='text']"))
                            .filter(i => !i.disabled);
                        ['{b1}', '{b2}', '{b3}'].forEach((v, idx) => {{
                            if (!active[idx]) return;
                            setter.call(active[idx], v);
                            ['input','change','blur'].forEach(ev =>
                                active[idx].dispatchEvent(new Event(ev, {{bubbles:true}}))
                            );
                        }});
                    }}
                    const hidden = document.querySelector("input[name='cashReceiptNum']");
                    if (hidden) {{
                        setter.call(hidden, '{biz_no_clean}');
                        hidden.dispatchEvent(new Event('change', {{bubbles:true}}));
                    }}
                }}
            """)
            print(f"[domeggook_order] 사업자지출증빙 설정 완료")
        except Exception as e:
            print(f"[domeggook_order] 사업자지출증빙 처리 실패: {e}")
    await asyncio.sleep(0.3)

    # 약관 동의 체크박스 - 보이는 것만
    try:
        checkboxes = page.locator("input[type='checkbox']")
        cnt = await checkboxes.count()
        checked = 0
        for i in range(cnt):
            cb = checkboxes.nth(i)
            if await cb.is_visible() and not await cb.is_checked():
                await cb.click()
                checked += 1
        print(f"[domeggook_order] 약관 체크박스 {checked}/{cnt}개 처리")
    except Exception as e:
        print(f"[domeggook_order] 약관 체크 실패: {e}")
    await asyncio.sleep(0.3)


async def _submit_and_get_order_no(page) -> str:
    """결제 버튼 클릭 후 주문번호 추출."""
    print(f"[domeggook_order] 결제 버튼 클릭 전 URL: {page.url}")

    # 결제 버튼 탐색 (ID → 텍스트 fallback)
    btn_info = await page.evaluate("""
        () => {
            const byId = document.getElementById('paymentBtn');
            if (byId) return {found: true, id: byId.id, text: byId.textContent.trim()};
            const all = Array.from(document.querySelectorAll('button, input[type=submit], a.btn'))
                .filter(el => /결제|주문완료|주문하기/.test(el.textContent));
            if (all.length) return {found: false, text: all[0].textContent.trim(), count: all.length};
            return {found: false, text: '', count: 0};
        }
    """)
    print(f"[domeggook_order] 결제버튼 탐색: {btn_info}")

    try:
        pay_btn = page.locator("button:has-text('결제하기'), a:has-text('결제하기'), #paymentBtn").first
        btn_text = await pay_btn.inner_text(timeout=3000)
        await pay_btn.click(timeout=5000)
        print(f"[domeggook_order] 결제하기 클릭: {btn_text.strip()}")
    except Exception as e:
        print(f"[domeggook_order] 결제하기 버튼 실패, JS fallback: {e}")
        await page.evaluate("document.getElementById('paymentBtn')?.click()")
    print("[domeggook_order] 결제 후 대기 중...")
    await asyncio.sleep(4)
    print(f"[domeggook_order] 결제 후 현재 URL: {page.url}")

    # 검증 에러 메시지 캡처
    errs = await page.evaluate("""
        () => {
            const sels = ['.error', '.alert', '.msg', '[class*=error]', '[class*=alert]', '[class*=warn]'];
            const found = [];
            for (const s of sels) {
                document.querySelectorAll(s).forEach(el => {
                    const t = el.innerText?.trim();
                    if (t && t.length > 0 && t.length < 200) found.push(t);
                });
            }
            return [...new Set(found)].slice(0, 5);
        }
    """)
    if errs:
        print(f"[domeggook_order] 페이지 에러: {errs}")

    # Toss Payments 가상계좌: iframe 내 은행 선택 (국민은행)
    bank_selected = False
    for attempt in range(15):
        await asyncio.sleep(1)
        # 이미 다음 페이지로 넘어갔으면 중단
        if "orderInfoForm" not in page.url:
            break
        # Toss iframe 탐색
        toss_frame = None
        for frame in page.frames:
            if "tosspayments.com" in frame.url:
                toss_frame = frame
                break
        if not toss_frame:
            continue
        # 국민은행 요소 클릭 (button이 아닌 div/li/span 등일 수 있어 text locator 사용)
        try:
            loc = toss_frame.locator("text=국민").first
            await loc.click(timeout=3000)
            print("[domeggook_order] 가상계좌 은행 선택: 국민")
            await asyncio.sleep(2)
            # 필수 체크박스 전체 체크
            await toss_frame.evaluate("""
                () => {
                    document.querySelectorAll("input[type='checkbox']").forEach(c => {
                        if (!c.checked) c.click();
                    });
                }
            """)
            await asyncio.sleep(0.5)
            # 확인 버튼 클릭
            confirm = toss_frame.locator("button", has_text="확인").first
            await confirm.click(timeout=5000)
            print("[domeggook_order] 가상계좌 확인 완료")
            bank_selected = True
            await asyncio.sleep(6)
        except Exception as e:
            print(f"[domeggook_order] 은행 선택/확인 오류: {e}")
        if bank_selected:
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

    # 주문 완료 텍스트 확인 (완료 페이지에서만 나오는 키워드만 사용)
    print(f"[domeggook_order] 결제 후 URL: {current_url}")
    if any(kw in content for kw in ["주문이 완료", "주문완료", "결제가 완료", "주문 접수"]):
        return "ORDER_OK"

    return ""


async def _order_item(page, order: dict, pay_method: str, birth: str = "", biz_no: str = "") -> dict:
    """도매꾹 상품 1건 주문."""
    item_no = order["item_no"]

    print(f"[domeggook_order]   상품 페이지 이동: {item_no}")
    ok = await _navigate_to_order_form(page, item_no)
    if not ok:
        return {"success": False, "domeggook_order": "", "error": "주문 폼 이동 실패"}

    # dialog(alert) 캡처
    _dialog_msgs = []
    async def _on_dialog(dialog):
        _dialog_msgs.append(dialog.message)
        try:
            await dialog.accept()
        except Exception:
            pass
    page.on("dialog", _on_dialog)

    print(f"[domeggook_order]   배송지 입력: {order.get('buyer_name')} / {order.get('addr','')[:30]}")
    await _fill_order_form(page, order, pay_method, birth, biz_no)

    print("[domeggook_order]   결제 진행...")
    order_no = await _submit_and_get_order_no(page)
    if _dialog_msgs:
        print(f"[domeggook_order] Alert 메시지: {_dialog_msgs}")
    if order_no:
        return {"success": True, "domeggook_order": order_no, "error": ""}
    return {"success": False, "domeggook_order": "", "error": "결제 완료 확인 실패"}


async def _run_orders(orders: list[dict], config: dict) -> list[dict]:
    domeggook_id = config["domeggook_id"]
    domeggook_pw = config["domeggook_pw"]
    pay_method = config.get("domeggook_pay_method", "vaccount")
    birth = config.get("domeggook_birth", "")
    biz_no = config.get("domeggook_biz_no", "")

    results = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, slow_mo=300)
        page = await browser.new_page(user_agent=UA)

        if not await _login(page, domeggook_id, domeggook_pw):
            raise RuntimeError("도매꾹 로그인 실패")
        print("[domeggook_order] 로그인 성공")

        for order in orders:
            print(f"[domeggook_order] 주문: {order['item_no']} x{order.get('qty',1)}"
                  f" → {order.get('buyer_name')}")
            try:
                result = await _order_item(page, order, pay_method, birth, biz_no)
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
