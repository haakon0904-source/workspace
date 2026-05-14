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

from flask import Flask, Response, jsonify, render_template

sys.path.insert(0, str(Path(__file__).parent.parent))

app = Flask(__name__)

ROOT = Path(__file__).parent.parent
DB_PATH = ROOT / "db" / "autoseller.db"

_status = {"running": False}
_log_queue = queue.Queue()


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


def _run_pipeline():
    _status["running"] = True
    old_stdout = sys.stdout
    sys.stdout = _Tee(old_stdout, _log_queue)
    try:
        from run_pipeline import CONFIG, KEYWORDS, _resolve_keyword_config
        from pipeline import step3_product_search, step4_margin, step5_register, step6_upload

        _log_queue.put("=" * 50)
        _log_queue.put("AutoSeller 파이프라인 시작")
        _log_queue.put("=" * 50)

        _log_queue.put("[Config] 카테고리별 수수료율 조회")
        commission_rates, display_categories = _resolve_keyword_config(CONFIG)
        CONFIG["keyword_commission_rates"] = commission_rates
        CONFIG["keyword_display_categories"] = display_categories

        products = step3_product_search.run(KEYWORDS, CONFIG)
        if not products:
            _log_queue.put("수집된 상품 없음. 종료.")
            return

        products = step4_margin.run(products, CONFIG)
        if not products:
            _log_queue.put("마진 기준 통과 상품 없음. 종료.")
            return

        products = step5_register.run(products, CONFIG)
        if not products:
            _log_queue.put("하네스 통과 상품 없음. 종료.")
            return

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


@app.route("/api/pipeline/run", methods=["POST"])
def api_run():
    if _status["running"]:
        return jsonify({"error": "이미 실행 중"}), 400
    while not _log_queue.empty():
        try:
            _log_queue.get_nowait()
        except queue.Empty:
            break
    threading.Thread(target=_run_pipeline, daemon=True).start()
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
               profit, margin_rate, status, created_at
        FROM products
        ORDER BY created_at DESC
    """)
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return jsonify(rows)


if __name__ == "__main__":
    print("AutoSeller 대시보드: http://localhost:5001")
    app.run(host="0.0.0.0", port=5001, debug=False, threaded=True)
