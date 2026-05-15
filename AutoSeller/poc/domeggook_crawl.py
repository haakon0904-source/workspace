"""
도매꾹 크롤링 POC
목적: 로그인 후 키워드 검색 → 상품 목록 수집 가능한지 검증
실행: python poc/domeggook_crawl.py
"""

import asyncio
import os
import re
import sys
from urllib.parse import quote
from playwright.async_api import async_playwright


import os

KEYWORD = "우산"
ID = os.environ.get("DOMEGGOOK_ID", "")
PW = os.environ.get("DOMEGGOOK_PW", "")
MAX_PAGES = 20  # 안전 상한


def build_search_url(keyword, page=1):
    kw = quote(keyword, encoding='euc-kr')
    return f"https://domeggook.com/main/item/itemList.php?sw={kw}&sf=ttl&pg={page}"


async def login(page):
    await page.goto("https://domeggook.com/ssl/member/mem_loginForm.php", wait_until="domcontentloaded")
    print(f"로그인 페이지: {page.url}")

    # hidden 필드 수집
    hidden = {}
    inputs = await page.query_selector_all("input[type='hidden']")
    for inp in inputs:
        name = await inp.get_attribute("name")
        value = await inp.get_attribute("value") or ""
        if name:
            hidden[name] = value
    print(f"Hidden fields: {hidden}")

    # Playwright API로 직접 POST (JS/봇감지 우회)
    response = await page.request.post(
        "https://domeggook.com/main/member/mem_ing.php",
        form={**hidden, "id": ID, "pass": PW}
    )
    raw = await response.body()
    body = raw.decode("cp949", errors="replace")
    print(f"POST 응답: status={response.status}, url={response.url}")

    # 응답에서 로그인 성공 여부 확인
    if "로그아웃" in body or 'is_member: "y"' in body:
        print("[성공] 로그인 완료")
        return True

    # 응답에 쿠키 설정 여부 확인
    cookies = await page.context.cookies()
    session_cookies = [c for c in cookies if "sess" in c["name"].lower() or "login" in c["name"].lower()]
    print(f"세션 쿠키: {session_cookies}")

    # 메인 페이지로 이동해서 로그인 상태 확인
    await page.goto("https://domeggook.com/", wait_until="domcontentloaded")
    content = await page.content()
    if "로그아웃" in content or 'is_member: "y"' in content:
        print("[성공] 로그인 완료")
        return True

    matches = re.findall(r'[가-힣\w]{0,10}(?:오류|실패|불일치|없|잘못|틀)[가-힣\w]{0,20}', body[:2000])
    print(f"[실패] 에러: {matches[:5]}")
    print(f"응답 앞부분: {body[:300]}")
    return False


EXTRACT_JS = """
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

TOTAL_JS = """
    () => {
        // 전체 건수: 페이지 내 'total' 류 텍스트에서 숫자 추출
        const el = document.querySelector('.totalCnt, .total_cnt, #totalCnt, .srch_total');
        if (el) {
            const m = el.innerText.match(/[\\d,]+/);
            if (m) return parseInt(m[0].replace(',', ''));
        }
        // 페이지네이션 마지막 번호로 추정
        const pages = document.querySelectorAll('.paging a, .paginate a, #paging a');
        let maxPage = 1;
        for (const a of pages) {
            const n = parseInt(a.innerText.trim());
            if (!isNaN(n) && n > maxPage) maxPage = n;
        }
        return maxPage > 1 ? maxPage : null;
    }
"""


async def fetch_page_products(page, keyword, page_num):
    url = build_search_url(keyword, page_num)
    await page.goto(url, wait_until="domcontentloaded", timeout=60000)
    await page.wait_for_selector('#lLst li', timeout=10000)
    return await page.evaluate(EXTRACT_JS)


GET_TOTAL_PAGES_JS = """
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


async def search_products(page):
    print(f"\n키워드: {KEYWORD}")

    all_products = []

    for page_num in range(1, MAX_PAGES + 1):
        print(f"  페이지 {page_num} 수집 중...", end=" ", flush=True)
        products = await fetch_page_products(page, KEYWORD, page_num)

        # 1페이지에서 총 페이지 수 파악
        if page_num == 1:
            total_pages = await page.evaluate(GET_TOTAL_PAGES_JS)
            print(f"{len(products)}개 (총 {total_pages}페이지)")
        else:
            print(f"{len(products)}개")

        if not products:
            print(f"  → 빈 페이지. 종료.")
            break

        all_products.extend(products)

        if page_num >= total_pages:
            break

    # 중복 제거 (상품번호 기준)
    seen = set()
    unique = []
    for p in all_products:
        if p['itemNo'] not in seen:
            seen.add(p['itemNo'])
            unique.append(p)

    print(f"\n=== 최종 수집: {len(unique)}개 ===")
    for p in unique[:20]:
        print(f"  {p['itemNo']} | {p['title']} | {p['price']}원")
    if len(unique) > 20:
        print(f"  ... 외 {len(unique) - 20}개")

    return unique


DETAIL_JS = """
    () => {
        // 대표이미지
        const img = document.querySelector('#lThumbImg');
        const imgSrc = img ? img.src.replace(/_img_\\d+/, '_img_760') : '';

        // 추가 이미지 (썸네일 목록)
        const thumbImgs = Array.from(document.querySelectorAll('#lThumbImgWrap img[src*="upload/item"]'))
            .map(i => i.src.replace(/_img_\\d+/, '_img_760').replace(/_stt_\\d+\\.png/, '_img_760'));

        // 가격
        const priceEl = document.querySelector('.lItemPrice');
        const priceText = priceEl ? priceEl.innerText.trim() : '';
        const priceNum = parseInt(priceText.replace(/[^\d]/g, '')) || 0;

        // 최소구매수량
        const purchaseEl = document.querySelector('.lInfoItemContent');
        const purchaseText = purchaseEl ? purchaseEl.innerText : '';
        const minQtyMatch = purchaseText.match(/최소구매수량\s*(\d+)/);
        const minQty = minQtyMatch ? parseInt(minQtyMatch[1]) : 1;

        // 배송정보
        const deliEl = document.querySelector('.lInfoDeli .lInfoItemContent');
        const deliText = deliEl ? deliEl.innerText.trim().slice(0, 100) : '';

        // 상품명
        const title = document.title.split('|')[0].trim();

        return { imgSrc, thumbImgs, priceNum, minQty, deliText, title };
    }
"""


async def fetch_item_detail(page, item_no):
    await page.goto(f"https://domeggook.com/{item_no}", wait_until="domcontentloaded", timeout=60000)
    await page.wait_for_selector('#lThumbImg', timeout=10000)
    detail = await page.evaluate(DETAIL_JS)
    detail['itemNo'] = item_no
    return detail


async def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "search"

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(user_agent=(
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ))

        if not await login(page):
            print("로그인 실패. 종료.")
            return

        if mode == "detail":
            # 상세 크롤링 테스트: 상위 3개 상품
            products = await search_products(page)
            print("\n=== 상세 크롤링 (상위 3개) ===")
            for prod in products[:3]:
                detail = await fetch_item_detail(page, prod['itemNo'])
                print(f"\n[{detail['itemNo']}] {detail['title'][:40]}")
                print(f"  가격: {detail['priceNum']}원")
                print(f"  최소수량: {detail['minQty']}개")
                print(f"  배송: {detail['deliText'][:60]}")
                print(f"  대표이미지: {detail['imgSrc'][:80]}")
                print(f"  추가이미지: {len(detail['thumbImgs'])}개")
        else:
            await search_products(page)

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
