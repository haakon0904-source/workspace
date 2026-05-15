"""
Step 3: 상품 자동 서치
- 키워드 목록을 받아 도매꾹에서 상품 목록 + 상세 정보를 수집
- 실행: python pipeline/step3_product_search.py

config 필수 키:
    domeggook_id   str
    domeggook_pw   str
    max_pages      int   (기본 20, 안전 상한)
    fetch_detail   bool  (기본 False, True면 상세 크롤링 포함)
"""

import asyncio
import re
from urllib.parse import quote
from playwright.async_api import async_playwright

UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

_EXTRACT_JS = """
    () => {
        const items = document.querySelectorAll('#lLst li');
        const result = [];
        for (const item of items) {
            const thumb = item.querySelector('a.thumb');
            const href = thumb ? thumb.getAttribute('href') || '' : '';
            const m = href.match(/\\/(\\d{5,})/);
            const itemNo = m ? m[1] : '';
            const titleEl = item.querySelector('a.title');
            const title = titleEl ? titleEl.innerText.trim().slice(0, 60) : '';
            const priceEl = item.querySelector('div.amt b');
            const price = priceEl ? priceEl.innerText.trim() : '';
            if (itemNo) result.push({itemNo, title, price});
        }
        return result;
    }
"""

_TOTAL_PAGES_JS = """
    () => {
        const items = document.querySelectorAll('#lPage ol li');
        let maxPage = 1;
        for (const li of items) {
            const n = parseInt(li.getAttribute('target') || '');
            if (!isNaN(n) && n > maxPage) maxPage = n;
        }
        return maxPage;
    }
"""

_DETAIL_JS = """
    () => {
        const img = document.querySelector('#lThumbImg');
        const imgSrc = img ? img.src.replace(/_img_\\d+/, '_img_760') : '';

        const thumbImgs = Array.from(document.querySelectorAll('#lThumbImgWrap img[src*="upload/item"]'))
            .map(i => i.src.replace(/_img_\\d+/, '_img_760').replace(/_stt_\\d+\\.png/, '_img_760'));

        const priceEl = document.querySelector('.lItemPrice');
        const priceNum = parseInt((priceEl ? priceEl.innerText : '').replace(/[^\\d]/g, '')) || 0;

        const purchaseEl = document.querySelector('.lInfoItemContent');
        const purchaseText = purchaseEl ? purchaseEl.innerText : '';
        const minQtyMatch = purchaseText.match(/최소구매수량\\s*(\\d+)/);
        const minQty = minQtyMatch ? parseInt(minQtyMatch[1]) : 1;

        const deliEl = document.querySelector('.lInfoDeli .lInfoItemContent');
        const delivery = deliEl ? deliEl.innerText.trim().slice(0, 100) : '';

        const title = document.title.split('|')[0].trim();

        return { imgSrc, thumbImgs, priceNum, minQty, delivery, title };
    }
"""


async def _login(page, domeggook_id, domeggook_pw):
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


def _build_search_url(keyword, pg=1, sort="sale"):
    kw = quote(keyword, encoding="euc-kr")
    return f"https://domeggook.com/main/item/itemList.php?sw={kw}&sf=ttl&od={sort}&pg={pg}"


async def _fetch_list_page(page, keyword, pg):
    await page.goto(_build_search_url(keyword, pg), wait_until="domcontentloaded", timeout=60000)
    await page.wait_for_selector("#lLst li", timeout=10000)
    return await page.evaluate(_EXTRACT_JS)


async def _fetch_detail(page, item_no, retries=3):
    for attempt in range(retries):
        try:
            await page.goto(f"https://domeggook.com/{item_no}", wait_until="domcontentloaded", timeout=60000)
            await page.wait_for_selector("#lThumbImg", timeout=10000)
            detail = await page.evaluate(_DETAIL_JS)
            detail["itemNo"] = item_no
            return detail
        except Exception as e:
            if attempt < retries - 1:
                print(f"[step3]   재시도 {attempt+1}/{retries-1} ({item_no}): {e.__class__.__name__}")
                await asyncio.sleep(3)
            else:
                print(f"[step3]   실패 스킵 ({item_no}): {e.__class__.__name__}")
                return {"itemNo": item_no, "imgSrc": "", "thumbImgs": [], "priceNum": 0, "minQty": 1, "delivery": "", "title": ""}


async def _search_keyword(page, keyword, max_pages, fetch_detail):
    products = []
    total_pages = 1

    for pg in range(1, max_pages + 1):
        print(f"[step3]   목록 {pg}페이지 크롤링 중...")
        items = await _fetch_list_page(page, keyword, pg)

        if pg == 1:
            total_pages = await page.evaluate(_TOTAL_PAGES_JS)
            print(f"[step3]   총 {total_pages}페이지")

        if not items:
            break

        products.extend(items)
        print(f"[step3]   {pg}/{total_pages}p 완료 ({len(items)}개, 누적 {len(products)}개)")

        if pg >= total_pages:
            break

    # 중복 제거
    seen = set()
    unique = []
    for p in products:
        if p["itemNo"] not in seen:
            seen.add(p["itemNo"])
            unique.append(p)

    if not fetch_detail:
        return [
            {
                "source": "domeggook",
                "keyword": keyword,
                "item_no": p["itemNo"],
                "title": p["title"],
                "price": int(p["price"].replace(",", "").replace("원", "").strip() or 0),
            }
            for p in unique
        ]

    result = []
    total = len(unique)
    for i, p in enumerate(unique, 1):
        print(f"[step3]   상세 {i}/{total} ({p['itemNo']})...")
        detail = await _fetch_detail(page, p["itemNo"])
        result.append({
            "source": "domeggook",
            "keyword": keyword,
            "item_no": p["itemNo"],
            "title": detail["title"] or p["title"],
            "price": detail["priceNum"],
            "min_qty": detail["minQty"],
            "img_url": detail["imgSrc"],
            "thumb_imgs": detail["thumbImgs"],
            "delivery": detail["delivery"],
        })
    return result


async def _run(keywords, config):
    domeggook_id = config["domeggook_id"]
    domeggook_pw = config["domeggook_pw"]
    max_pages = config.get("max_pages", 20)
    fetch_detail = config.get("fetch_detail", False)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(user_agent=UA)

        if not await _login(page, domeggook_id, domeggook_pw):
            raise RuntimeError("도매꾹 로그인 실패")

        all_products = []
        for keyword in keywords:
            print(f"[step3] 검색: {keyword}")
            products = await _search_keyword(page, keyword, max_pages, fetch_detail)
            print(f"[step3]   → {len(products)}개 수집")
            all_products.extend(products)

        await browser.close()

    return all_products


def run(keywords: list, config: dict) -> list:
    """
    키워드 목록으로 도매꾹 상품 수집.

    Returns:
        list[dict]: 상품 목록
            - source, keyword, item_no, title, price
            - (fetch_detail=True 시) min_qty, img_url, thumb_imgs, delivery
    """
    return asyncio.run(_run(keywords, config))


if __name__ == "__main__":
    import json

    _config = {
        "domeggook_id": "haakon",
        "domeggook_pw": "Pyjqwe12",
        "max_pages": 2,
        "fetch_detail": True,
    }
    _keywords = ["우산"]
    products = run(_keywords, _config)
    print(f"\n총 {len(products)}개")
    for p in products[:3]:
        print(json.dumps(p, ensure_ascii=False, indent=2))
