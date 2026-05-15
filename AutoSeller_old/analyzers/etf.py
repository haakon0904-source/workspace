"""
ETF 분석 모듈
- 추천 ETF 목록 및 비교 분석
- 모멘텀 DCA 신호 (RSI 기반 매수량 조절)
"""
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta

ETF_LIST = {
    # 주식 ETF
    "QQQ":  {"name": "나스닥100",    "desc": "미국 빅테크·성장주 100종목. 핵심 추천.", "category": "주식"},
    "SPY":  {"name": "S&P500",       "desc": "미국 대형주 500종목. 가장 안정적.",      "category": "주식"},
    "SCHD": {"name": "배당성장",      "desc": "우량 배당성장주. 안정적 현금흐름.",       "category": "주식"},
    "VGT":  {"name": "IT섹터",        "desc": "미국 IT 전체. QQQ보다 기술주 집중.",    "category": "주식"},
    "SOXX": {"name": "반도체",        "desc": "엔비디아·TSMC 등 반도체 집중.",         "category": "주식"},
    "ARKK": {"name": "혁신성장",      "desc": "고위험·고수익 혁신기업. 변동성 큼.",     "category": "주식"},
    # 대안 자산
    "USO":  {"name": "원유",          "desc": "WTI 원유 가격 추종. 경기·지정학 민감.", "category": "원자재"},
    "GLD":  {"name": "금",            "desc": "금 가격 추종. 인플레·위기 헤지 수단.", "category": "원자재"},
    "EWY":  {"name": "코스피(한국)",   "desc": "MSCI 한국 지수 추종. 삼성·SK 포함.", "category": "해외주식"},
    "TLT":  {"name": "미국 장기채권",  "desc": "미국 20년+ 국채. 금리 하락 시 수익.", "category": "채권"},
}


def get_exchange_rate() -> float:
    """USD/KRW 환율 조회"""
    try:
        ticker = yf.Ticker("KRW=X")
        hist = ticker.history(period="1d")
        if not hist.empty:
            return float(hist["Close"].iloc[-1])
    except Exception:
        pass
    return 1350.0  # fallback


def calc_rsi(series: pd.Series, period: int = 14) -> float:
    """RSI 계산"""
    delta = series.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    rs = gain / loss.replace(0, 1e-9)
    rsi = 100 - (100 / (1 + rs))
    return round(float(rsi.iloc[-1]), 1)


def get_etf_data(ticker: str, period_years: int = 4) -> dict:
    """ETF 분석 데이터 수집"""
    try:
        tk = yf.Ticker(ticker)
        hist = tk.history(period=f"{period_years}y")
        if hist.empty:
            return {}

        current = float(hist["Close"].iloc[-1])
        price_1y_ago = float(hist["Close"].iloc[-252]) if len(hist) >= 252 else None
        price_3m_ago = float(hist["Close"].iloc[-63])  if len(hist) >= 63  else None
        price_1m_ago = float(hist["Close"].iloc[-21])  if len(hist) >= 21  else None

        rsi = calc_rsi(hist["Close"])

        # 이동평균
        ma50  = float(hist["Close"].rolling(50).mean().iloc[-1])
        ma200 = float(hist["Close"].rolling(200).mean().iloc[-1])

        # 수익률
        ret_1m  = (current / price_1m_ago  - 1) * 100 if price_1m_ago  else None
        ret_3m  = (current / price_3m_ago  - 1) * 100 if price_3m_ago  else None
        ret_1y  = (current / price_1y_ago  - 1) * 100 if price_1y_ago  else None
        ret_4y  = (current / float(hist["Close"].iloc[0]) - 1) * 100

        # 변동성 (연환산)
        daily_ret = hist["Close"].pct_change().dropna()
        volatility = float(daily_ret.std() * (252 ** 0.5) * 100)

        # 최고가 대비 현재가 (drawdown)
        peak = float(hist["Close"].rolling(252).max().iloc[-1])
        drawdown = (current / peak - 1) * 100

        # 모멘텀 DCA 신호
        signal, ratio = _dca_signal(rsi, current, ma50, ma200)

        info = tk.info
        expense_ratio = info.get("annualReportExpenseRatio") or info.get("totalExpenseRatio")

        return {
            "ticker": ticker,
            "current": current,
            "rsi": rsi,
            "ma50": round(ma50, 2),
            "ma200": round(ma200, 2),
            "ret_1m": round(ret_1m, 1)  if ret_1m  is not None else None,
            "ret_3m": round(ret_3m, 1)  if ret_3m  is not None else None,
            "ret_1y": round(ret_1y, 1)  if ret_1y  is not None else None,
            "ret_4y": round(ret_4y, 1),
            "volatility": round(volatility, 1),
            "drawdown": round(drawdown, 1),
            "expense_ratio": round(expense_ratio * 100, 2) if expense_ratio else None,
            "signal": signal,
            "dca_ratio": ratio,   # 기본 대비 매수 배율 (0.5x ~ 2.0x)
            "hist": hist,
        }
    except Exception as e:
        print(f"[WARN] {ticker} 데이터 수집 실패: {e}")
        return {}


def _dca_signal(rsi: float, price: float, ma50: float, ma200: float):
    """
    모멘텀 DCA 신호
    - RSI < 30: 과매도 → 2배 매수
    - RSI 30~45: 저평가 → 1.5배
    - RSI 45~60: 보통 → 1배 (기본)
    - RSI 60~75: 고평가 → 0.75배
    - RSI > 75: 과매수 → 0.5배
    """
    if rsi < 30:
        return "💚 강력매수 (2배)", 2.0
    elif rsi < 45:
        return "🟢 매수 (1.5배)", 1.5
    elif rsi < 60:
        return "🟡 정상매수 (1배)", 1.0
    elif rsi < 75:
        return "🟠 소량매수 (0.75배)", 0.75
    else:
        return "🔴 매수보류 (0.5배)", 0.5


def compare_etfs(tickers: list = None) -> pd.DataFrame:
    """ETF 비교표 생성"""
    if tickers is None:
        tickers = list(ETF_LIST.keys())

    rows = []
    for t in tickers:
        d = get_etf_data(t)
        if not d:
            continue
        info = ETF_LIST.get(t, {})
        rows.append({
            "티커": t,
            "이름": info.get("name", ""),
            "현재가($)": round(d["current"], 2),
            "RSI": d["rsi"],
            "1개월(%)": d["ret_1m"],
            "3개월(%)": d["ret_3m"],
            "1년(%)": d["ret_1y"],
            "4년(%)": d["ret_4y"],
            "변동성(%)": d["volatility"],
            "고점대비(%)": d["drawdown"],
            "비용(%)": d["expense_ratio"],
            "DCA신호": d["signal"],
        })
    return pd.DataFrame(rows)
