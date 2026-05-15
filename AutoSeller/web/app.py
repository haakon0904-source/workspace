"""
AutoSeller 웹 모니터링 대시보드
실행: python3 web/app.py
접속: http://localhost:5000
"""

import json
import queue
import sqlite3
import sys
import threading
from pathlib import Path

from flask import Flask, Response, jsonify, render_template, request

sys.path.insert(0, str(Path(__file__).parent.parent))

app = Flask(__name__)

ROOT = Path(__file__).parent.parent
DB_PATH = ROOT / "db" / "autoseller.db"

_status = {"running": False}
_log_queue = queue.Queue()
_stop_event = threading.Event()


class _Tee:
    """print를 터미널 + 로그 큐 양쪽으로 전달."""
    def __init__(self, original, q):
        self._orig = original
        self._q = q

    def write(self, msg):
        self._orig.write(msg)
        self._orig.flush()
        line = msg.rstrip()
        if line:
            self._q.put(line)

    def flush(self):
        self._orig.flush()


def _run_pipeline(keywords=None, use_variations=True):
    _status["running"] = True
    old_stdout = sys.stdout
    sys.stdout = _Tee(old_stdout, _log_queue)
    try:
        from run_pipeline import CONFIG, KEYWORDS, KEYWORD_CATEGORIES, _resolve_keyword_config
        from pipeline import (
            step2_keyword_variations,
            step3_product_search, step4_margin, step5_register, step6_upload,
        )

        _log_queue.put("=" * 50)
        _log_queue.put("AutoSeller 파이프라인 시작")
        _log_queue.put("=" * 50)

        kws = keywords or KEYWORDS

        # KEYWORD_CATEGORIES에 없는 키워드 기본값 추가
        for kw in kws:
            if kw not in KEYWORD_CATEGORIES:
                KEYWORD_CATEGORIES[kw] = {
                    "display_category": CONFIG.get("coupang_display_category", 69884),
                    "commission": ("생활/건강",),
                }

        _log_queue.put("\n[Config] 카테고리별 수수료율 조회")
        commission_rates, display_categories = _resolve_keyword_config(CONFIG)
        CONFIG["keyword_commission_rates"] = commission_rates
        CONFIG["keyword_display_categories"] = display_categories

        _log_queue.put(f"\n[Step 3] 도매꾹 상품 수집 (원본 키워드 {len(kws)}개)")
        products = []
        for kw in kws:
            if _stop_event.is_set():
                _log_queue.put("[중단] 사용자 요청으로 크롤링 중단됨")
                break
            products.extend(step3_product_search.run([kw], CONFIG))
        if not products:
            _log_queue.put("수집된 상품 없음. 종료.")
            return

        # Step 2: 변형어를 쿠팡 검색태그로 생성 (크롤링 X)
        if use_variations and CONFIG.get("naver_client_id"):
            _log_queue.put(f"\n[Step 2] 변형어 검색태그 생성 ({len(kws)}개 키워드)")
            variation_tags = step2_keyword_variations.get_tags(kws, CONFIG)
            for p in products:
                p["search_tags"] = variation_tags.get(p.get("keyword", ""), [])
        else:
            reason = "변형어 확장 OFF" if not use_variations else "API 키 없음"
            _log_queue.put(f"\n[Step 2] 생략 ({reason})")

        before_margin = len(products)
        _log_queue.put(f"\n[Step 4] 마진 계산 ({before_margin}개 대상)")
        products = step4_margin.run(products, CONFIG)
        _log_queue.put(f"[Step 4] {before_margin}개 중 {len(products)}개 마진 통과 "
                       f"(제외 {before_margin - len(products)}개)")
        if not products:
            _log_queue.put("마진 기준 통과 상품 없음. 종료.")
            return

        _log_queue.put("\n[Step 5] DB 저장 + 하네스 검증")
        products = step5_register.run(products, CONFIG)
        if not products:
            _log_queue.put("하네스 통과 상품 없음. 종료.")
            return

        _log_queue.put("\n[Step 6] 쿠팡 업로드")
        results = step6_upload.run(products, CONFIG)
        success = [r for r in results if r.get("success")]
        _log_queue.put("=" * 50)
        _log_queue.put(f"완료: {len(success)}/{len(results)}개 등록 성공")
        _log_queue.put("=" * 50)

    except Exception as e:
        _log_queue.put(f"[오류] {e}")
    finally:
        sys.stdout = old_stdout
        _status["running"] = False
        _log_queue.put("__END__")


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/pipeline/trending", methods=["POST"])
def api_trending():
    """Step1: 트렌딩 키워드 분석 결과 반환 (JSON)."""
    try:
        from run_pipeline import CONFIG
        from pipeline.step1_trending_keywords import (
            SEED_KEYWORDS, _date_range, _query_shopping_insight, _chunk_list,
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    if not CONFIG.get("naver_client_id"):
        from run_pipeline import KEYWORDS
        return jsonify({
            "keywords": [{"keyword": kw, "ratio": 0, "score": 0, "trend": "─"} for kw in KEYWORDS],
            "top": KEYWORDS,
            "period": {"recent": "-", "prev": "-"},
            "no_api": True,
        })

    weeks = CONFIG.get("trend_weeks", 4)
    top_n = CONFIG.get("trend_top_n", 10)
    recent_start, recent_end = _date_range(0, weeks)
    prev_start, prev_end = _date_range(weeks, weeks)

    recent_ratios, prev_ratios = {}, {}
    kw_category = {}
    for cat_name, info in SEED_KEYWORDS.items():
        cat_code = info["category"]
        for kw in info["keywords"]:
            kw_category[kw] = cat_name
        for chunk in _chunk_list(info["keywords"], 5):
            try:
                recent_ratios.update(_query_shopping_insight(cat_code, chunk, recent_start, recent_end, CONFIG))
                prev_ratios.update(_query_shopping_insight(cat_code, chunk, prev_start, prev_end, CONFIG))
            except Exception:
                pass

    scores = {}
    for kw, recent in recent_ratios.items():
        prev = prev_ratios.get(kw, 0)
        scores[kw] = (recent - prev) / prev if prev > 0 else recent

    sorted_kws = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    keywords = []
    for kw, score in sorted_kws:
        ratio = recent_ratios.get(kw, 0)
        prev = prev_ratios.get(kw, 0)
        trend = "▲" if score > 0.05 else ("▼" if score < -0.05 else "─")
        keywords.append({
            "keyword": kw,
            "category": kw_category.get(kw, "-"),
            "ratio": round(ratio, 1),
            "prev_ratio": round(prev, 1),
            "score": round(score * 100, 1),
            "trend": trend,
        })

    categories = list(dict.fromkeys(kw_category[k["keyword"]] for k in keywords if k["keyword"] in kw_category))
    return jsonify({
        "keywords": keywords,
        "top": [k["keyword"] for k in keywords[:top_n]],
        "categories": categories,
        "period": {"recent": f"{recent_start} ~ {recent_end}", "prev": f"{prev_start} ~ {prev_end}"},
    })


@app.route("/api/pipeline/run", methods=["POST"])
def api_run():
    if _status["running"]:
        return jsonify({"error": "이미 실행 중"}), 400
    while not _log_queue.empty():
        try:
            _log_queue.get_nowait()
        except queue.Empty:
            break
    _stop_event.clear()
    data = request.get_json(silent=True) or {}
    keywords = data.get("keywords") or None
    use_variations = data.get("use_variations", True)
    threading.Thread(target=_run_pipeline, args=(keywords, use_variations), daemon=True).start()
    return jsonify({"ok": True})


@app.route("/api/pipeline/stop", methods=["POST"])
def api_stop():
    _stop_event.set()
    return jsonify({"ok": True})


@app.route("/api/pipeline/stream")
def api_stream():
    def generate():
        while True:
            try:
                msg = _log_queue.get(timeout=30)
                if msg == "__END__":
                    yield "data: __END__\n\n"
                    break
                yield f"data: {json.dumps(msg, ensure_ascii=False)}\n\n"
            except queue.Empty:
                yield "data: ping\n\n"
    return Response(
        generate(),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.route("/api/pipeline/status")
def api_status():
    return jsonify(_status)


@app.route("/api/products")
def api_products():
    if not DB_PATH.exists():
        return jsonify([])
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("""
        SELECT item_no, title, keyword, buy_price, sell_price,
               profit, margin_rate, status, seller_product_id, coupang_status, created_at
        FROM products
        ORDER BY created_at DESC
    """)
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return jsonify(rows)


@app.route("/api/coupang/sync", methods=["POST"])
def api_coupang_sync():
    """쿠팡 상품 상태를 DB에 동기화."""
    try:
        from run_pipeline import CONFIG
        from uploader.coupang import fetch_all_products
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    if not DB_PATH.exists():
        return jsonify({"error": "DB 없음"}), 400

    products = fetch_all_products(CONFIG)
    if not products:
        return jsonify({"updated": 0})

    conn = sqlite3.connect(DB_PATH)
    updated = 0
    for p in products:
        cur = conn.execute(
            "UPDATE products SET seller_product_id=?, coupang_status=?, updated_at=datetime('now') "
            "WHERE item_no=?",
            (str(p["seller_product_id"]), p["coupang_status"], p["item_no"]),
        )
        updated += cur.rowcount
    conn.commit()
    conn.close()
    return jsonify({"updated": updated, "total": len(products)})


@app.route("/api/coupang/stop-sale/<seller_product_id>", methods=["POST"])
def api_stop_sale(seller_product_id):
    """상품 판매중지."""
    try:
        from run_pipeline import CONFIG
        from uploader.coupang import stop_sale
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    result = stop_sale(int(seller_product_id), CONFIG)
    if result["success"] and DB_PATH.exists():
        conn = sqlite3.connect(DB_PATH)
        conn.execute(
            "UPDATE products SET coupang_status='임시저장', updated_at=datetime('now') "
            "WHERE seller_product_id=?",
            (seller_product_id,),
        )
        conn.commit()
        conn.close()
    return jsonify(result)


@app.route("/api/coupang/start-sale/<seller_product_id>", methods=["POST"])
def api_start_sale(seller_product_id):
    """상품 판매 재개 (임시저장 → 승인 요청)."""
    try:
        from run_pipeline import CONFIG
        from uploader.coupang import _request
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    path = f"/v2/providers/seller_api/apis/api/v1/marketplace/seller-products/{seller_product_id}"
    resp = _request("GET", path, CONFIG)
    data = resp.json()
    if data.get("code") != "SUCCESS":
        return jsonify({"success": False, "error": data.get("message", "조회 실패")})

    product = data["data"]
    for item in product.get("items", []):
        item["saleStatus"] = "ON_SALE"
    product["requested"] = True

    r2 = _request("PUT", "/v2/providers/seller_api/apis/api/v1/marketplace/seller-products", CONFIG, body=product)
    d2 = r2.json()
    if d2.get("code") == "SUCCESS":
        if DB_PATH.exists():
            conn = sqlite3.connect(DB_PATH)
            conn.execute(
                "UPDATE products SET coupang_status='승인완료', updated_at=datetime('now') "
                "WHERE seller_product_id=?",
                (seller_product_id,),
            )
            conn.commit()
            conn.close()
        return jsonify({"success": True, "error": ""})
    return jsonify({"success": False, "error": d2.get("message", "판매재개 실패")})


@app.route("/api/server/restart", methods=["POST"])
def api_restart():
    """현재 서버를 종료하고 새 프로세스로 재시작."""
    import os, signal, subprocess
    pid = os.getpid()
    script = (
        f"import time, subprocess, os, signal\n"
        f"os.kill({pid}, signal.SIGTERM)\n"
        f"time.sleep(2)\n"
        f"subprocess.Popen(['python3', '{ROOT / 'web/app.py'}'])\n"
    )
    subprocess.Popen(["python3", "-c", script])
    return jsonify({"ok": True})


@app.route("/api/server/status")
def api_server_status():
    return jsonify({"ok": True})


if __name__ == "__main__":
    print("AutoSeller 대시보드: http://localhost:5001")
    app.run(host="0.0.0.0", port=5001, debug=False, threaded=True)
