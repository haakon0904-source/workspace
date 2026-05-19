"""
쿠팡 신규 주문 체크 + 텔레그램 알림
GitHub Actions에서 하루 3번 실행 (9시/12시/15시 KST)

환경변수 (GitHub Actions):
    COUPANG_ACCESS_KEY, COUPANG_SECRET_KEY, COUPANG_VENDOR_ID
    TELEGRAM_TOKEN, TELEGRAM_CHAT_ID

로컬 실행: python tools/check_orders_notify.py
"""

import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).parent.parent))


# ── config ───────────────────────────────────────────────────

def _get_config():
    if os.environ.get("COUPANG_ACCESS_KEY"):
        return {
            "coupang_access_key": os.environ["COUPANG_ACCESS_KEY"],
            "coupang_secret_key": os.environ["COUPANG_SECRET_KEY"],
            "coupang_vendor_id":  os.environ["COUPANG_VENDOR_ID"],
            "telegram_token":     os.environ["TELEGRAM_TOKEN"],
            "telegram_chat_id":   os.environ["TELEGRAM_CHAT_ID"],
        }
    from run_pipeline import CONFIG
    return CONFIG


# ── 쿠팡 주문 조회 ────────────────────────────────────────────

def fetch_recent_orders(config: dict, hours: int = 4) -> list[dict]:
    from uploader.coupang import _request
    vendor_id = config["coupang_vendor_id"]
    now = datetime.now()
    date_from = (now - timedelta(hours=hours)).strftime("%Y-%m-%d")
    date_to   = (now + timedelta(days=1)).strftime("%Y-%m-%d")

    path = (
        f"/v2/providers/openapi/apis/api/v4/vendors/{vendor_id}/ordersheets"
        f"?status=ACCEPT&createdAtFrom={date_from}&createdAtTo={date_to}&maxPerPage=50"
    )
    resp = _request("GET", path, config)
    data = resp.json()
    if data.get("code") not in (200, "SUCCESS"):
        print(f"[check_orders] 주문 조회 실패: {data.get('message')}")
        return []

    orders = []
    for sheet in data.get("data", []):
        paid_at = sheet.get("paidAt", "")
        if paid_at:
            try:
                if datetime.fromisoformat(paid_at) < now - timedelta(hours=hours):
                    continue
            except Exception:
                pass
        for item in sheet.get("orderItems", []):
            orders.append({
                "order_id":   str(sheet.get("orderId", "")),
                "item_no":    item.get("externalVendorSkuCode", "") or item.get("externalVendorSku", ""),
                "title":      item.get("sellerProductName", item.get("vendorItemName", "")),
                "qty":        item.get("shippingCount", 1),
                "sell_price": item.get("salesPrice", 0),
                "buyer_name": sheet.get("receiver", {}).get("name", ""),
                "paid_at":    paid_at,
            })
    return orders


# ── 처리된 주문 ID 관리 ───────────────────────────────────────

PROCESSED_FILE = Path(__file__).parent.parent / "db" / "processed_order_ids.json"


def load_processed() -> set:
    if PROCESSED_FILE.exists():
        try:
            return set(str(i) for i in json.loads(PROCESSED_FILE.read_text()))
        except Exception:
            pass
    return set()


def save_processed(ids: set):
    PROCESSED_FILE.parent.mkdir(parents=True, exist_ok=True)
    PROCESSED_FILE.write_text(json.dumps(sorted(ids)[-500:], ensure_ascii=False))


# ── 텔레그램 알림 ─────────────────────────────────────────────

def send_telegram(text: str, config: dict):
    token   = config["telegram_token"]
    chat_id = config["telegram_chat_id"]
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    resp = requests.post(url, json={"chat_id": chat_id, "text": text}, timeout=10)
    resp.raise_for_status()
    print(f"[telegram] 전송 완료")


def build_message(orders: list[dict]) -> str:
    now_str = datetime.now().strftime("%m/%d %H:%M")
    if len(orders) == 1:
        o = orders[0]
        return (
            f"🛒 새 주문 [{now_str}]\n"
            f"상품: {o['title'][:30]}...\n"
            f"수량: {o['qty']}개 / {o['sell_price']:,}원\n"
            f"구매자: {o['buyer_name']}"
        )
    total = sum(o["sell_price"] * o["qty"] for o in orders)
    lines = [f"🛒 새 주문 {len(orders)}건 [{now_str}]", f"합계: {total:,}원", ""]
    for o in orders:
        lines.append(f"• {o['title'][:20]}... x{o['qty']} ({o['sell_price']:,}원)")
    return "\n".join(lines)


# ── 메인 ─────────────────────────────────────────────────────

def main():
    config = _get_config()
    print(f"[check_orders] 주문 조회 시작 ({datetime.now().strftime('%Y-%m-%d %H:%M')})")

    orders = fetch_recent_orders(config, hours=4)
    print(f"[check_orders] 최근 4시간 주문: {len(orders)}건")

    if not orders:
        print("[check_orders] 새 주문 없음")
        return

    processed = load_processed()
    new_orders = [o for o in orders if o["order_id"] not in processed]
    print(f"[check_orders] 신규 주문: {len(new_orders)}건")

    if not new_orders:
        print("[check_orders] 알림 전송할 신규 주문 없음")
        return

    try:
        send_telegram(build_message(new_orders), config)
    except Exception as e:
        print(f"[telegram] 전송 실패: {e}")
        return

    for o in new_orders:
        processed.add(o["order_id"])
    save_processed(processed)
    print("[check_orders] 완료")


if __name__ == "__main__":
    main()
