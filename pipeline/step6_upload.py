"""
Step 6: 전 플랫폼 동시 업로드
- 현재: 쿠팡만 지원 (추후 스마트스토어 등 추가)
- 실행: python pipeline/step6_upload.py

config 필수 키:
    coupang_access_key  str
    coupang_secret_key  str
    coupang_vendor_id   str
"""

import sqlite3
from pathlib import Path

from uploader import coupang


def _update_db(results: list, config: dict):
    """업로드 결과를 DB에 반영 (status, seller_product_id)."""
    db_path = Path(config.get("db_path", "db/autoseller.db"))
    if not db_path.exists():
        return
    conn = sqlite3.connect(db_path)
    for r in results:
        status = "uploaded" if r.get("success") else "upload_failed"
        conn.execute(
            "UPDATE products SET status=?, seller_product_id=?, updated_at=datetime('now') "
            "WHERE item_no=?",
            (status, r.get("product_id") or None, r.get("item_no")),
        )
    conn.commit()
    conn.close()


def run(products: list, config: dict) -> list:
    """
    step5 통과 상품을 플랫폼에 업로드.

    Returns:
        list[dict]: 업로드 결과 포함 상품 목록
    """
    print(f"[step6] 업로드 대상: {len(products)}개")
    results = coupang.run(products, config)
    _update_db(results, config)
    success = [r for r in results if r.get("success")]
    print(f"[step6] 완료: {len(success)}/{len(products)}개 성공")
    return results
