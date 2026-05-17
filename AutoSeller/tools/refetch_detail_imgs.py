"""
기존 DB 상품들 detail_imgs 재수집
실행: python tools/refetch_detail_imgs.py [--all]
  --all: 이미 수집된 상품 포함 전체 재수집
"""

import asyncio
import json
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from pipeline.step3_product_search import _DETAIL_JS, _login, UA

DB_PATH = Path(__file__).parent.parent / "db" / "autoseller.db"
RELOGIN_INTERVAL = 30


def _migrate(conn: sqlite3.Connection):
    try:
        conn.execute("ALTER TABLE products ADD COLUMN detail_imgs TEXT")
        conn.commit()
        print("[DB] detail_imgs 컬럼 추가")
    except Exception:
        pass


async def _run(item_nos: list, config: dict, conn: sqlite3.Connection):
    from playwright.async_api import async_playwright

    total = len(item_nos)
    ok = 0

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(user_agent=UA)

        if not await _login(page, config["domeggook_id"], config["domeggook_pw"]):
            raise RuntimeError("도매꾹 로그인 실패")

        for i, item_no in enumerate(item_nos, 1):
            if i > 1 and (i - 1) % RELOGIN_INTERVAL == 0:
                print(f"  [재로그인] {i}/{total}...")
                await _login(page, config["domeggook_id"], config["domeggook_pw"])

            try:
                await page.goto(
                    f"https://domeggook.com/{item_no}",
                    wait_until="domcontentloaded",
                    timeout=30000,
                )
                await page.wait_for_selector("#lThumbImg", timeout=10000)
                more_btn = await page.query_selector("#lBtnItemContentsMore")
                if more_btn:
                    await more_btn.click()
                    await asyncio.sleep(0.3)
                detail = await page.evaluate(_DETAIL_JS)
                imgs = detail.get("detailImgs", [])
                print(f"  [{i}/{total}] {item_no}: {len(imgs)}개")
                if imgs:
                    ok += 1
            except Exception as e:
                print(f"  [{i}/{total}] {item_no}: 실패 ({e.__class__.__name__})")
                imgs = []

            conn.execute(
                "UPDATE products SET detail_imgs=?, updated_at=datetime('now') WHERE item_no=?",
                (json.dumps(imgs, ensure_ascii=False), item_no),
            )
            conn.commit()

        await browser.close()

    return ok


def main():
    force_all = "--all" in sys.argv
    from run_pipeline import CONFIG

    conn = sqlite3.connect(DB_PATH)
    _migrate(conn)

    if force_all:
        rows = conn.execute("SELECT item_no FROM products").fetchall()
    else:
        rows = conn.execute(
            "SELECT item_no FROM products "
            "WHERE detail_imgs IS NULL OR detail_imgs = '' OR detail_imgs = '[]'"
        ).fetchall()

    item_nos = [r[0] for r in rows]
    print(f"재수집 대상: {len(item_nos)}개" + (" (전체)" if force_all else ""))

    if not item_nos:
        print("없음. 종료.")
        conn.close()
        return

    ok = asyncio.run(_run(item_nos, CONFIG, conn))

    conn.close()
    total = len(item_nos)
    print(f"\n완료: {ok}/{total}개 이미지 수집 성공")
    fail = total - ok
    if fail:
        print(f"실패(이미지 0개): {fail}개 (상품 삭제됐거나 로딩 오류)")


if __name__ == "__main__":
    main()
