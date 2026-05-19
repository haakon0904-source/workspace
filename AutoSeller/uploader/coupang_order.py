"""
쿠팡 주문 조회 + 송장 등록
"""

import sqlite3
from pathlib import Path
from uploader.coupang import _request


def get_pending_orders(config: dict) -> list[dict]:
    """
    출고 대기 주문 조회.
    Returns: [{order_id, ordersheet_id, vendor_item_id, item_no, title,
               qty, buyer_name, buyer_phone, addr, addr_detail, zip}]
    """
    vendor_id = config["coupang_vendor_id"]
    from datetime import datetime, timedelta
    date_from = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    date_to = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")

    path = (
        f"/v2/providers/openapi/apis/api/v4/vendors/{vendor_id}/ordersheets"
        f"?status=ACCEPT&createdAtFrom={date_from}&createdAtTo={date_to}"
        f"&maxPerPage=50"
    )
    resp = _request("GET", path, config)
    if resp.status_code != 200:
        print(f"[coupang_order] 주문 조회 실패: {resp.status_code} {resp.text[:200]}")
        return []

    data = resp.json()
    if data.get("code") not in (200, "SUCCESS"):
        print(f"[coupang_order] 주문 조회 오류: {data.get('message')}")
        return []

    orders = []
    for sheet in data.get("data", []):
        for item in sheet.get("orderItems", []):
            orders.append({
                "order_id":       sheet.get("orderId"),
                "ordersheet_id":  sheet.get("shipmentBoxId"),
                "vendor_item_id": item.get("vendorItemId"),
                "item_no":        item.get("externalVendorSkuCode", "") or item.get("externalVendorSku", ""),
                "title":          item.get("vendorItemName", ""),
                "qty":            item.get("shippingCount", 1),
                "buyer_name":     sheet.get("receiver", {}).get("name", ""),
                "buyer_phone":    sheet.get("receiver", {}).get("safeNumber") or sheet.get("receiver", {}).get("mobile", ""),
                "addr":           sheet.get("receiver", {}).get("addr1", ""),
                "addr_detail":    sheet.get("receiver", {}).get("addr2", ""),
                "zip":            sheet.get("receiver", {}).get("postCode", ""),
            })
    print(f"[coupang_order] 출고대기 주문 {len(orders)}건")
    return orders


def register_tracking(order_id: str, ordersheet_id: str,
                      tracking_number: str, courier_code: str,
                      config: dict) -> bool:
    """쿠팡에 송장번호 등록."""
    vendor_id = config["coupang_vendor_id"]
    path = (
        f"/v2/providers/openapi/apis/api/v4/vendors/{vendor_id}"
        f"/orders/{order_id}/ordersheets/{ordersheet_id}/shipments"
    )
    body = {
        "deliveryCompanyCode": courier_code,
        "invoiceNumber": tracking_number,
    }
    resp = _request("POST", path, config, body=body)
    data = resp.json()
    if data.get("code") == "SUCCESS":
        print(f"[coupang_order] 송장 등록 완료: {tracking_number}")
        return True
    print(f"[coupang_order] 송장 등록 실패: {data.get('message')}")
    return False


def sync_orders_to_db(orders: list, config: dict):
    """주문 정보를 DB에 저장."""
    db_path = Path(config.get("db_path", "db/autoseller.db"))
    if not db_path.exists():
        return
    conn = sqlite3.connect(db_path)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id         TEXT NOT NULL,
            ordersheet_id    TEXT NOT NULL,
            item_no          TEXT,
            title            TEXT,
            qty              INTEGER DEFAULT 1,
            buyer_name       TEXT,
            buyer_phone      TEXT,
            addr             TEXT,
            addr_detail      TEXT,
            zip              TEXT,
            status           TEXT DEFAULT 'pending',  -- pending/ordered/shipped/done
            domeggook_order  TEXT,
            tracking_number  TEXT,
            courier_code     TEXT DEFAULT 'CJGLS',
            created_at       TEXT,
            updated_at       TEXT,
            UNIQUE(order_id, ordersheet_id)
        )
    """)
    conn.commit()
    from datetime import datetime
    now = datetime.now().isoformat()
    for o in orders:
        try:
            conn.execute("""
                INSERT INTO orders
                    (order_id, ordersheet_id, item_no, title, qty,
                     buyer_name, buyer_phone, addr, addr_detail, zip,
                     status, created_at, updated_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,'pending',?,?)
            """, (
                o["order_id"], o["ordersheet_id"], o["item_no"], o["title"], o["qty"],
                o["buyer_name"], o["buyer_phone"], o["addr"], o["addr_detail"], o["zip"],
                now, now,
            ))
        except sqlite3.IntegrityError:
            pass  # 이미 있는 주문
    conn.commit()
    conn.close()
