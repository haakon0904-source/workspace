"""
Step 6: 멀티플랫폼 동시 업로드
- 설정된 플랫폼에만 업로드 (config 키 존재 여부로 판단)
- 현재 지원: 쿠팡, 네이버 스마트스토어

config 판단 기준:
    coupang_access_key          → 쿠팡 업로드
    naver_commerce_client_id    → 네이버 업로드
"""

import sqlite3
from pathlib import Path

from uploader import coupang


def _update_db(results: list, config: dict):
    db_path = Path(config.get("db_path", "db/autoseller.db"))
    if not db_path.exists():
        return
    conn = sqlite3.connect(db_path)

    # naver_product_id 컬럼 없으면 추가
    cols = {r[1] for r in conn.execute("PRAGMA table_info(products)")}
    if "naver_product_id" not in cols:
        conn.execute("ALTER TABLE products ADD COLUMN naver_product_id TEXT")

    for r in results:
        platform = r.get("platform", "coupang")
        if platform == "naver":
            conn.execute(
                "UPDATE products SET naver_product_id=?, updated_at=datetime('now') WHERE item_no=?",
                (r.get("product_id") or None, r.get("item_no")),
            )
        else:
            status = "uploaded" if r.get("success") else "upload_failed"
            conn.execute(
                "UPDATE products SET status=?, seller_product_id=?, updated_at=datetime('now') WHERE item_no=?",
                (status, r.get("product_id") or None, r.get("item_no")),
            )
    conn.commit()
    conn.close()


def run(products: list, config: dict) -> list:
    print(f"[step6] 업로드 대상: {len(products)}개")
    all_results = []

    # 쿠팡
    if config.get("coupang_access_key"):
        results = coupang.run(products, config)
        _update_db(results, config)
        all_results.extend(results)

    # 네이버 스마트스토어
    if config.get("naver_commerce_client_id"):
        from uploader import naver
        results = naver.run(products, config)
        _update_db(results, config)
        all_results.extend(results)

    if not all_results:
        print("[step6] 업로드 플랫폼 미설정")
        return []

    success = [r for r in all_results if r.get("success")]
    print(f"[step6] 완료: {len(success)}/{len(all_results)}개 성공")
    return all_results
