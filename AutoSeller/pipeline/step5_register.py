"""
Step 5: 상품 등록 (DB 저장 + 하네스 검증)
- step4 통과 상품을 DB에 저장하고 하네스로 검증
- 하네스는 현재 stub (통과만 처리), 추후 Claude AI 검증 추가
- 실행: python pipeline/step5_register.py

config 필수 키:
    db_path   str  SQLite DB 경로 (기본 db/autoseller.db)
"""

import json
import sqlite3
from datetime import datetime
from pathlib import Path


def _init_db(conn: sqlite3.Connection):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id                 INTEGER PRIMARY KEY AUTOINCREMENT,
            source             TEXT NOT NULL,
            keyword            TEXT NOT NULL,
            item_no            TEXT NOT NULL,
            title              TEXT NOT NULL,
            buy_price          INTEGER NOT NULL,
            sell_price         INTEGER NOT NULL,
            profit             INTEGER NOT NULL,
            margin_rate        REAL NOT NULL,
            min_qty            INTEGER DEFAULT 1,
            img_url            TEXT,
            delivery           TEXT,
            status             TEXT DEFAULT 'pending',  -- pending / uploaded / upload_failed
            seller_product_id  TEXT,                   -- 쿠팡 sellerProductId
            coupang_status     TEXT,                   -- 쿠팡 실제 상태 (승인완료/임시저장 등)
            created_at         TEXT NOT NULL,
            updated_at         TEXT NOT NULL,
            UNIQUE(source, item_no)
        )
    """)
    # 기존 DB 컬럼 마이그레이션
    for col, definition in [
        ("seller_product_id", "TEXT"),
        ("coupang_status",    "TEXT"),
        ("detail_imgs",       "TEXT"),
    ]:
        try:
            conn.execute(f"ALTER TABLE products ADD COLUMN {col} {definition}")
        except Exception:
            pass
    conn.commit()


def _harness(product: dict) -> tuple[bool, str]:
    """
    하네스 검증 (현재 stub).
    추후 Claude AI로 상품명/가격/이미지 규약 검증.
    Returns: (통과여부, 사유)
    """
    # 기본 sanity check
    if not product.get("title"):
        return False, "상품명 없음"
    if not product.get("sell_price", 0) > 0:
        return False, "판매가 0원"
    if len(product.get("title", "")) < 5:
        return False, "상품명 너무 짧음"
    return True, "ok"


def run(products: list, config: dict) -> list:
    """
    상품 DB 저장 + 하네스 검증.

    Returns:
        list[dict]: 하네스 통과 + DB 저장 완료 상품
    """
    db_path = Path(config.get("db_path", "db/autoseller.db"))
    db_path.parent.mkdir(exist_ok=True)

    conn = sqlite3.connect(db_path)
    _init_db(conn)

    now = datetime.now().isoformat()
    passed = []
    skipped_harness = 0
    skipped_dup = 0

    for p in products:
        ok, reason = _harness(p)
        if not ok:
            print(f"[step5] 하네스 실패 [{p['item_no']}]: {reason}")
            skipped_harness += 1
            continue

        try:
            detail_imgs_json = json.dumps(p.get("detail_imgs") or [], ensure_ascii=False)
            conn.execute("""
                INSERT INTO products
                    (source, keyword, item_no, title, buy_price, sell_price,
                     profit, margin_rate, min_qty, img_url, detail_imgs, delivery, status, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?, ?)
            """, (
                p.get("source"), p.get("keyword"), p.get("item_no"),
                p.get("title"), p.get("price"), p.get("sell_price"),
                p.get("profit"), p.get("margin_rate"),
                p.get("min_qty", 1), p.get("img_url"), detail_imgs_json, p.get("delivery"),
                now, now,
            ))
            conn.commit()
            passed.append(p)
        except sqlite3.IntegrityError:
            # 이미 DB에 있는 상품 — 선택된 플랫폼 기준으로 미등록 여부 판단
            cols = {r[1] for r in conn.execute("PRAGMA table_info(products)")}
            if "naver_product_id" not in cols:
                conn.execute("ALTER TABLE products ADD COLUMN naver_product_id TEXT")
                conn.commit()
            row = conn.execute(
                "SELECT status, seller_product_id, naver_product_id FROM products WHERE source=? AND item_no=?",
                (p.get("source"), p.get("item_no")),
            ).fetchone()
            if row:
                status, seller_product_id, naver_product_id = row
                use_coupang = bool(config.get("coupang_access_key"))
                use_naver = bool(config.get("naver_commerce_client_id"))
                need_coupang = use_coupang and not seller_product_id
                need_naver = use_naver and not naver_product_id
                if need_coupang or need_naver:
                    conn.execute(
                        "UPDATE products SET status='pending', updated_at=? WHERE source=? AND item_no=?",
                        (now, p.get("source"), p.get("item_no")),
                    )
                    conn.commit()
                    passed.append(p)
                    targets = []
                    if need_coupang: targets.append("쿠팡")
                    if need_naver: targets.append("네이버")
                    print(f"[step5] 재업로드 대상 [{p['item_no']}] → {', '.join(targets)}")
                else:
                    skipped_dup += 1
            else:
                skipped_dup += 1

    conn.close()
    print(f"[step5] {len(products)}개 → 업로드대상 {len(passed)}개 "
          f"(하네스실패 {skipped_harness}, 이미업로드 {skipped_dup})")
    return passed


if __name__ == "__main__":
    # step4 결과 샘플로 테스트
    sample = [
        {
            "source": "domeggook", "keyword": "우산", "item_no": "10708086",
            "title": "카본 경량 우산 양산 양우산 미니 휴대용", "price": 8500,
            "sell_price": 21250, "profit": 7455, "margin_rate": 0.3508,
            "min_qty": 1, "img_url": "https://cdn1.domeggook.com/test.jpg",
            "delivery": "택배 / 3000원",
        },
        {
            "source": "domeggook", "keyword": "우산", "item_no": "99999",
            "title": "X", "price": 1000, "sell_price": 2500,
            "profit": 100, "margin_rate": 0.04,
        },
    ]
    _config = {"db_path": "db/autoseller.db"}
    result = run(sample, _config)
    print(f"통과: {[p['item_no'] for p in result]}")
