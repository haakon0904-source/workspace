"""
FastAPI 백엔드 서버
Flutter 앱 ↔ 이 서버 ↔ 분석 모듈

실행: python3 api_server.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import asyncio
from concurrent.futures import ThreadPoolExecutor
from functools import partial
import json
from datetime import datetime

from analyzers.screener import get_stock_data, screen_all, WATCHLIST
from analyzers.earnings import get_earnings_data
from analyzers.etf import get_etf_data, ETF_LIST, get_exchange_rate
from analyzers.portfolio import load, calc_portfolio
from analyzers.notifier import send_message, is_connected

app = FastAPI(title="주식 분석 API", version="2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

executor = ThreadPoolExecutor(max_workers=4)

# ─────────────────────────────────────────────────────────
# 헬스체크
# ─────────────────────────────────────────────────────────
@app.get("/")
def root():
    return {"status": "ok", "time": datetime.now().isoformat()}


# ─────────────────────────────────────────────────────────
# 스크리닝
# ─────────────────────────────────────────────────────────
@app.get("/api/screener")
async def screener():
    """전체 워치리스트 스크리닝 결과"""
    loop = asyncio.get_event_loop()
    results = []
    for ticker in WATCHLIST:
        d = await loop.run_in_executor(executor, get_stock_data, ticker)
        if d:
            d.pop("hist", None)  # 히스토리 데이터는 제외 (용량)
            results.append(d)
    results.sort(key=lambda x: x.get("canslim_score", 0), reverse=True)
    return {"data": results, "updated": datetime.now().isoformat()}


@app.get("/api/stock/{ticker}")
async def stock_detail(ticker: str):
    """개별 종목 상세 분석"""
    ticker = ticker.upper()
    loop = asyncio.get_event_loop()

    d, ed = await asyncio.gather(
        loop.run_in_executor(executor, get_stock_data, ticker),
        loop.run_in_executor(executor, get_earnings_data, ticker),
    )

    if not d:
        raise HTTPException(status_code=404, detail=f"{ticker} 데이터 없음")

    hist = d.pop("hist", None)

    # 주가 히스토리 (최근 1년, 일봉)
    price_history = []
    if hist is not None and not hist.empty:
        h = hist.tail(252)
        price_history = [
            {
                "date": str(idx.date()),
                "open": round(float(row["Open"]), 2),
                "high": round(float(row["High"]), 2),
                "low":  round(float(row["Low"]), 2),
                "close":round(float(row["Close"]), 2),
                "volume": int(row["Volume"]),
            }
            for idx, row in h.iterrows()
        ]

    # 실적 데이터 정리
    ed_clean = {k: v for k, v in ed.items() if not isinstance(v, list)} if ed else {}
    quarterly_revenue = ed.get("quarterly_revenue", []) if ed else []
    surprise_history  = ed.get("surprise_history", []) if ed else []

    return {
        "stock": d,
        "earnings": ed_clean,
        "quarterly_revenue": quarterly_revenue,
        "surprise_history": surprise_history,
        "price_history": price_history,
        "updated": datetime.now().isoformat(),
    }


# ─────────────────────────────────────────────────────────
# ETF
# ─────────────────────────────────────────────────────────
@app.get("/api/etf")
async def etf_list():
    """주요 ETF 분석"""
    loop = asyncio.get_event_loop()
    tickers = list(ETF_LIST.keys())
    results = []
    for t in tickers:
        d = await loop.run_in_executor(executor, get_etf_data, t)
        if d:
            d.pop("hist", None)
            d["info"] = ETF_LIST.get(t, {})
            results.append({"ticker": t, **d})
    return {"data": results, "updated": datetime.now().isoformat()}


# ─────────────────────────────────────────────────────────
# 포트폴리오
# ─────────────────────────────────────────────────────────
@app.get("/api/portfolio")
async def portfolio():
    """포트폴리오 현황"""
    loop = asyncio.get_event_loop()
    trades = load()
    exrate = await loop.run_in_executor(executor, get_exchange_rate)

    if not trades:
        return {"holdings": [], "summary": {}, "exrate": exrate}

    holdings = []
    total_invested = 0
    total_value = 0

    for ticker, t_list in trades.items():
        d = await loop.run_in_executor(executor, get_stock_data, ticker)
        current = d.get("current", 0) if d else 0
        signal = d.get("signal", "") if d else ""
        sell_signal = d.get("sell_signal", "") if d else ""

        buy_trades = [t for t in t_list if t.get("type") == "buy"]
        total_qty = sum(t.get("qty", 0) for t in buy_trades)
        total_cost = sum(t.get("qty", 0) * t.get("price", 0) for t in buy_trades)
        avg_price = total_cost / total_qty if total_qty > 0 else 0
        value = total_qty * current
        pnl = value - total_cost
        pnl_pct = (pnl / total_cost * 100) if total_cost > 0 else 0

        holdings.append({
            "ticker": ticker,
            "qty": total_qty,
            "avg_price": round(avg_price, 2),
            "current": current,
            "value_usd": round(value, 2),
            "value_krw": round(value * exrate, 0),
            "pnl_usd": round(pnl, 2),
            "pnl_pct": round(pnl_pct, 1),
            "signal": signal,
            "sell_signal": sell_signal,
        })
        total_invested += total_cost
        total_value += value

    holdings.sort(key=lambda x: x["value_usd"], reverse=True)

    return {
        "holdings": holdings,
        "summary": {
            "total_invested_usd": round(total_invested, 2),
            "total_value_usd": round(total_value, 2),
            "total_pnl_usd": round(total_value - total_invested, 2),
            "total_pnl_pct": round((total_value / total_invested - 1) * 100, 1) if total_invested > 0 else 0,
            "total_value_krw": round(total_value * exrate, 0),
        },
        "exrate": exrate,
        "updated": datetime.now().isoformat(),
    }


# ─────────────────────────────────────────────────────────
# 알림
# ─────────────────────────────────────────────────────────
@app.get("/api/notification/status")
def notification_status():
    return {"connected": is_connected()}


class MessageBody(BaseModel):
    text: str

@app.post("/api/notification/send")
def notification_send(body: MessageBody):
    ok = send_message(body.text)
    return {"ok": ok}


# ─────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api_server:app", host="0.0.0.0", port=8000, reload=False)
