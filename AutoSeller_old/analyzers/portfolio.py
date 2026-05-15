"""
포트폴리오 관리 모듈
- 매수내역 CRUD (JSON 저장)
- 평가손익 계산
- 4년 목표 달성률 추적
"""
import json
import os
from datetime import datetime
from typing import List, Dict
import yfinance as yf
import pandas as pd

DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "portfolio.json")

# 월 적립 계획
MONTHLY_KRW = {
    "부부": 1_000_000,
    "자녀": 500_000,
}
GOAL_RETURN_PCT = 100   # 4년 목표 수익률 %
GOAL_YEARS = 4


def load() -> List[Dict]:
    try:
        with open(DATA_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def save(data: List[Dict]):
    os.makedirs(os.path.dirname(DATA_PATH), exist_ok=True)
    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def add_trade(account: str, ticker: str, shares: float,
              price_usd: float, date: str, memo: str = "") -> Dict:
    """매수 내역 추가"""
    data = load()
    trade = {
        "id": int(datetime.now().timestamp() * 1000),
        "account": account,      # 부부 / 자녀
        "ticker": ticker.upper(),
        "shares": shares,
        "price_usd": price_usd,
        "date": date,
        "memo": memo,
    }
    data.append(trade)
    save(data)
    return trade


def delete_trade(trade_id: int):
    data = load()
    data = [d for d in data if d.get("id") != trade_id]
    save(data)


def get_current_prices(tickers: list) -> Dict[str, float]:
    """현재가 일괄 조회"""
    prices = {}
    if not tickers:
        return prices
    try:
        raw = yf.download(tickers, period="1d", auto_adjust=True, progress=False)
        if "Close" in raw.columns:
            close = raw["Close"]
            if isinstance(close, pd.Series):
                prices[tickers[0]] = float(close.iloc[-1])
            else:
                for t in tickers:
                    if t in close.columns:
                        prices[t] = float(close[t].iloc[-1])
        else:
            for t in tickers:
                tk = yf.Ticker(t)
                h = tk.history(period="1d")
                if not h.empty:
                    prices[t] = float(h["Close"].iloc[-1])
    except Exception as e:
        print(f"[WARN] 현재가 조회 실패: {e}")
    return prices


def get_exchange_rate() -> float:
    try:
        tk = yf.Ticker("KRW=X")
        h = tk.history(period="1d")
        return float(h["Close"].iloc[-1]) if not h.empty else 1350.0
    except Exception:
        return 1350.0


def calc_portfolio(account: str = None) -> Dict:
    """포트폴리오 평가 계산"""
    data = load()
    if account:
        data = [d for d in data if d["account"] == account]
    if not data:
        return {"trades": [], "summary": {}, "by_ticker": pd.DataFrame()}

    tickers = list({d["ticker"] for d in data})
    prices = get_current_prices(tickers)
    exrate = get_exchange_rate()

    rows = []
    total_cost = 0
    total_value = 0

    for d in data:
        t = d["ticker"]
        cur = prices.get(t, 0)
        cost_usd = d["shares"] * d["price_usd"]
        value_usd = d["shares"] * cur
        pnl_usd = value_usd - cost_usd
        pnl_pct = (value_usd / cost_usd - 1) * 100 if cost_usd > 0 else 0

        rows.append({
            "id": d["id"],
            "계좌": d["account"],
            "티커": t,
            "수량": d["shares"],
            "매수가($)": d["price_usd"],
            "현재가($)": round(cur, 2),
            "매수금($)": round(cost_usd, 2),
            "평가금($)": round(value_usd, 2),
            "손익($)": round(pnl_usd, 2),
            "손익(%)": round(pnl_pct, 1),
            "매수일": d["date"],
            "메모": d.get("memo", ""),
        })
        total_cost += cost_usd
        total_value += value_usd

    df = pd.DataFrame(rows)

    # 종목별 집계
    by_ticker = df.groupby("티커").agg(
        수량=("수량", "sum"),
        매수금=("매수금($)", "sum"),
        평가금=("평가금($)", "sum"),
    ).reset_index()
    by_ticker["손익($)"] = by_ticker["평가금"] - by_ticker["매수금"]
    by_ticker["손익(%)"] = ((by_ticker["평가금"] / by_ticker["매수금"]) - 1) * 100
    by_ticker["비중(%)"] = by_ticker["평가금"] / total_value * 100 if total_value > 0 else 0
    by_ticker = by_ticker.round(2)

    total_pnl = total_value - total_cost
    total_pnl_pct = (total_value / total_cost - 1) * 100 if total_cost > 0 else 0

    summary = {
        "총매수금($)": round(total_cost, 2),
        "총평가금($)": round(total_value, 2),
        "총손익($)": round(total_pnl, 2),
        "총손익(%)": round(total_pnl_pct, 1),
        "총매수금(원)": round(total_cost * exrate),
        "총평가금(원)": round(total_value * exrate),
        "환율": exrate,
        "목표달성률(%)": round(total_pnl_pct / GOAL_RETURN_PCT * 100, 1),
    }

    return {"trades": rows, "summary": summary, "by_ticker": by_ticker}


def calc_goal_progress(start_date: str = "2025-01-01") -> Dict:
    """4년 목표 진행률 계산"""
    start = datetime.strptime(start_date, "%Y-%m-%d")
    now = datetime.now()
    end = datetime(start.year + GOAL_YEARS, start.month, start.day)

    elapsed_months = (now.year - start.year) * 12 + (now.month - start.month)
    total_months = GOAL_YEARS * 12

    monthly_total = sum(MONTHLY_KRW.values())
    expected_principal = monthly_total * elapsed_months
    final_principal = monthly_total * total_months

    days_left = (end - now).days
    progress_pct = elapsed_months / total_months * 100

    return {
        "시작일": start_date,
        "종료목표일": end.strftime("%Y-%m-%d"),
        "경과개월": elapsed_months,
        "남은일수": max(days_left, 0),
        "진행률(%)": round(progress_pct, 1),
        "누적원금(원)": expected_principal,
        "최종원금(원)": final_principal,
        "목표수익(원)": final_principal,   # 100% = 원금 × 2
        "목표평가금(원)": final_principal * 2,
    }
