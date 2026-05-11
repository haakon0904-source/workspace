"""
도매꾹 크롤링 POC
목적: 로그인 후 키워드 검색 → 상품 목록 수집 가능한지 검증
실행: python poc/domeggook_crawl.py
"""

import asyncio
import re
from urllib.parse import quote
from playwright.async_api import async_playwright


KEYWORD = "우산"
SEARCH_URL = f"https://domeggook.com/main/item/itemList.php?sw={quote(KEYWORD, encoding='euc-kr')}&sf=ttl"
ID = "haakon"
PW = "Pyjqwe12"


async def login(page):
    await page.goto("https://domeggook.com/ssl/member/mem_loginForm.php", wait_until="networkidle")
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
    await page.goto("https://domeggook.com/", wait_until="networkidle")
    content = await page.content()
    if "로그아웃" in content or 'is_member: "y"' in content:
        print("[성공] 로그인 완료")
        return True

    matches = re.findall(r'[가-힣\w]{0,10}(?:오류|실패|불일치|없|잘못|틀)[가-힣\w]{0,20}', body[:2000])
    print(f"[실패] 에러: {matches[:5]}")
    print(f"응답 앞부분: {body[:300]}")
    return False


async def search_products(page):
    print(f"\n검색: {SEARCH_URL}")

    # 네트워크 요청 모니터링 (AJAX 엔드포인트 찾기)
    api_calls = []
    page.on("request", lambda r: api_calls.append(r.url) if "item" in r.url.lower() or "search" in r.url.lower() else None)

    await page.goto(SEARCH_URL, wait_until="networkidle")
    await page.wait_for_timeout(5000)

    print(f"감지된 API 호출:")
    for url in api_calls:
        print(f"  {url[:120]}")

    html = await page.content()

    # li 1개 HTML 확인
    sample = await page.evaluate("() => document.querySelector('#lLst li')?.innerHTML || ''")
    print(f"\nSAMPLE LI HTML:\n{sample[:1000]}")

    # 상품 리스트 추출
    products = await page.evaluate("""
        () => {
            const items = document.querySelectorAll('#lLst li');
            const result = [];
            for (const item of items) {
                const links = item.querySelectorAll('a');
                let itemNo = '', title = '', price = '';
                // 상품번호: thumb 링크에서 추출
                const thumb = item.querySelector('a.thumb');
                if (thumb) {
                    const href = thumb.getAttribute('href') || '';
                    const m = href.match(/\\/(\\d{5,})/);
                    if (m) itemNo = m[1];
                }
                // 제목: a.title
                const titleEl = item.querySelector('a.title');
                if (titleEl) title = titleEl.innerText.trim().slice(0, 60);
                const priceEl = item.querySelector('div.amt b');
                if (priceEl) price = priceEl.innerText.trim();
                if (itemNo) result.push({itemNo, title, price});
            }
            return result;
        }
    """)
    print(f"\n=== 검색 결과 ({len(products)}개) ===")
    for p in products[:10]:
        print(f"  {p['itemNo']} | {p['title']} | {p['price']}원")


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(user_agent=(
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ))

        await login(page)
        await search_products(page)

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
