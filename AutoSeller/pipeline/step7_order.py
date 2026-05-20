"""
Step 7: 드랍쉬핑 자동 처리
1. 쿠팡 출고대기 주문 조회
2. DB 저장
3. 도매꾹 자동 주문 (item_no 매핑 필요)
4. 쿠팡 송장 등록 (배송사 확인 후)

실행: python pipeline/step7_order.py
"""

import sqlite3
from pathlib import Path
from datetime import datetime

from uploader.coupang_order import get_pending_orders, sync_orders_to_db, register_tracking
from uploader.domeggook_order import place_orders


def _get_pending_from_db(db_path: str, order_ids: list = None) -> list[dict]:
    """DB에서 status='pending' 주문 조회. order_ids 지정 시 해당 주문만."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    if order_ids:
        placeholders = ",".join("?" * len(order_ids))
        rows = conn.execute(
            f"SELECT * FROM orders WHERE status='pending' AND order_id IN ({placeholders}) ORDER BY created_at",
            [str(i) for i in order_ids],
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM orders WHERE status='pending' ORDER BY created_at"
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def _resolve_item_no(order: dict, db_path: str) -> str:
    """
    쿠팡 vendorItemId → 도매꾹 item_no 매핑.
    products 테이블의 vendor_item_id 컬럼 참조.
    """
    vendor_item_id = str(order.get("vendor_item_id", ""))
    item_no = order.get("item_no", "")

    # orders.item_no에 이미 있으면 사용
    if item_no:
        return item_no

    # products 테이블에서 vendor_item_id로 역조회
    try:
        conn = sqlite3.connect(db_path)
        row = conn.execute(
            "SELECT item_no FROM products WHERE seller_product_id=? OR vendor_item_id=?",
            (vendor_item_id, vendor_item_id),
        ).fetchone()
        conn.close()
        if row:
            return row[0]
    except Exception:
        pass

    return ""


def _update_order_status(db_path: str, order_id: str, ordersheet_id: str,
                          status: str, domeggook_order: str = None,
                          tracking_number: str = None, courier_code: str = None):
    conn = sqlite3.connect(db_path)
    now = datetime.now().isoformat()
    conn.execute(
        """UPDATE orders SET status=?, domeggook_order=COALESCE(?,domeggook_order),
           tracking_number=COALESCE(?,tracking_number),
           courier_code=COALESCE(?,courier_code),
           updated_at=?
           WHERE order_id=? AND ordersheet_id=?""",
        (status, domeggook_order, tracking_number, courier_code,
         now, order_id, ordersheet_id),
    )
    conn.commit()
    conn.close()


def _get_shipped_orders(db_path: str) -> list[dict]:
    """도매꾹 주문은 됐으나 쿠팡 송장 미등록 건 조회."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        """SELECT * FROM orders
           WHERE status='ordered'
             AND tracking_number IS NOT NULL
             AND tracking_number != ''"""
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def run(config: dict, order_ids: list = None) -> dict:
    """
    드랍쉬핑 전체 플로우 실행.

    Returns:
        {"fetched": int, "ordered": int, "tracking_registered": int}
    """
    db_path = config.get("db_path", "db/autoseller.db")
    stats = {"fetched": 0, "ordered": 0, "tracking_registered": 0}

    # 1. 쿠팡 주문 조회 & DB 동기화
    print("[step7] 쿠팡 출고대기 주문 조회...")
    orders = get_pending_orders(config)
    stats["fetched"] = len(orders)
    if orders:
        sync_orders_to_db(orders, config)

    # 2. DB pending 주문 → 도매꾹 자동 주문
    pending = _get_pending_from_db(db_path, order_ids)
    print(f"[step7] 도매꾹 주문 대상: {len(pending)}건")

    if pending:
        # item_no 해결
        order_requests = []
        for o in pending:
            item_no = _resolve_item_no(o, db_path)
            if not item_no:
                print(f"[step7] item_no 미확인 스킵: order_id={o['order_id']}")
                continue
            order_requests.append({
                **o,
                "item_no": item_no,
            })

        if order_requests:
            results = place_orders(order_requests, config)
            for r in results:
                if r["success"]:
                    _update_order_status(
                        db_path, r["order_id"], r["ordersheet_id"],
                        status="ordered",
                        domeggook_order=r["domeggook_order"],
                    )
                    stats["ordered"] += 1
                else:
                    _update_order_status(
                        db_path, r["order_id"], r["ordersheet_id"],
                        status="order_failed",
                    )

    # 3. 송장번호 있는 건 쿠팡에 등록
    # (도매꾹 주문 후 배송사가 송장을 발행하면 tracking_number가 채워짐)
    # 현재는 수동 또는 별도 polling으로 채워지는 구조
    shipped = _get_shipped_orders(db_path)
    print(f"[step7] 쿠팡 송장 등록 대상: {len(shipped)}건")
    for o in shipped:
        ok = register_tracking(
            order_id=o["order_id"],
            ordersheet_id=o["ordersheet_id"],
            tracking_number=o["tracking_number"],
            courier_code=o.get("courier_code") or "CJGLS",
            config=config,
        )
        if ok:
            _update_order_status(
                db_path, o["order_id"], o["ordersheet_id"],
                status="shipped",
            )
            stats["tracking_registered"] += 1

    print(f"[step7] 완료: 조회={stats['fetched']}, 주문={stats['ordered']}, 송장등록={stats['tracking_registered']}")
    return stats


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from run_pipeline import CONFIG
    run(CONFIG)
