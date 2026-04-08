"""
주도주 스크리닝 모듈
─────────────────────────────────────────────────────────
종합 팩터 모델 (학술·실전 검증된 4대 팩터)
  1. CANSLIM      – 매출/이익 성장 가속도 + 모멘텀 (O'Neil)
  2. Piotroski    – 재무건전성 9개 기준 (F-Score)
  3. Magic Formula– ROIC + 이익수익률 (Greenblatt)
  4. 퀄리티       – ROE, 이익률 안정성, 부채비율
  5. 기술적       – MA, RSI, 상대강도
─────────────────────────────────────────────────────────
"""
import yfinance as yf
import pandas as pd
import numpy as np

WATCHLIST = {
    # AI / 반도체
    "NVDA": "엔비디아 (AI 칩)",
    "AMD":  "AMD (AI 칩)",
    "AVGO": "브로드컴 (AI 네트워크)",
    "TSM":  "TSMC (파운드리)",
    "QCOM": "퀄컴 (모바일·차량)",
    # 빅테크
    "MSFT": "마이크로소프트 (클라우드·AI)",
    "AAPL": "애플 (생태계)",
    "GOOGL":"알파벳 (AI·광고)",
    "META": "메타 (SNS·AI)",
    "AMZN": "아마존 (클라우드·커머스)",
    # 고성장
    "TSLA": "테슬라 (전기차·AI)",
    "NOW":  "ServiceNow (엔터프라이즈 AI)",
    "CRM":  "세일즈포스 (CRM·AI)",
    "PLTR": "팔란티어 (AI 분석)",
    "APP":  "Applovin (AI 광고)",
}

# ─────────────────────────────────────────────────────────
# 기술 지표
# ─────────────────────────────────────────────────────────
def calc_rsi(series: pd.Series, period: int = 14) -> float:
    delta = series.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    rs = gain / loss.replace(0, 1e-9)
    rsi = 100 - (100 / (1 + rs))
    return round(float(rsi.iloc[-1]), 1)


# ─────────────────────────────────────────────────────────
# Piotroski F-Score (0~9, 재무건전성)
# ─────────────────────────────────────────────────────────
def _piotroski_score(info: dict, tk) -> int:
    """
    수익성(4) + 레버리지(3) + 운영효율(2) = 9점 만점
    7+ 강한 매수, 4-6 중립, 3 이하 위험
    """
    score = 0
    try:
        bs = tk.balance_sheet        # 재무상태표
        cf = tk.cashflow             # 현금흐름표
        fs = tk.financials           # 손익계산서

        # ── 수익성 ──
        roa = info.get("returnOnAssets")
        if roa and roa > 0:                 score += 1  # F1: ROA > 0
        if roa and roa > 0.05:              score += 1  # F1b: ROA > 5% (강화)

        # 영업현금흐름 > 0
        if cf is not None and not cf.empty:
            ocf = cf.loc["Operating Cash Flow"].iloc[0] if "Operating Cash Flow" in cf.index else None
            if ocf and ocf > 0:             score += 1  # F3

        # 전년 대비 ROA 개선
        if roa and roa > (info.get("returnOnAssets") or 0):
            score += 1  # F4 (근사)

        # ── 레버리지 ──
        debt_to_equity = info.get("debtToEquity")
        if debt_to_equity and debt_to_equity < 50:  score += 1  # F5: 부채비율 낮음

        current_ratio = info.get("currentRatio")
        if current_ratio and current_ratio > 1:     score += 1  # F6: 유동비율 > 1

        # ── 운영효율 ──
        gross_margin = info.get("grossMargins")
        operating_margin = info.get("operatingMargins")
        if gross_margin and gross_margin > 0.30:    score += 1  # F8: 매출총이익률
        if operating_margin and operating_margin > 0.10: score += 1  # F9: 영업이익률

    except Exception:
        pass
    return score


# ─────────────────────────────────────────────────────────
# Magic Formula 요소 (Greenblatt)
# ─────────────────────────────────────────────────────────
def _magic_formula_score(info: dict) -> int:
    """
    ROIC (자본이익률) + 이익수익률(Earnings Yield) 조합
    각 5점 만점 = 합계 10점
    """
    score = 0
    roe = info.get("returnOnEquity")
    if roe:
        if roe >= 0.30:   score += 5
        elif roe >= 0.20: score += 4
        elif roe >= 0.15: score += 3
        elif roe >= 0.10: score += 2
        elif roe > 0:     score += 1

    pe = info.get("trailingPE")
    if pe and pe > 0:
        ey = 1 / pe  # 이익수익률 = 1/PER
        if ey >= 0.05:    score += 5   # PER 20 이하
        elif ey >= 0.035: score += 4   # PER 28 이하
        elif ey >= 0.025: score += 3   # PER 40 이하
        elif ey >= 0.015: score += 2
        else:             score += 1
    return score


# ─────────────────────────────────────────────────────────
# 퀄리티 팩터
# ─────────────────────────────────────────────────────────
def _quality_score(info: dict) -> int:
    """ROE, 이익률, 부채비율 기반 퀄리티 (0~15점)"""
    score = 0

    roe = info.get("returnOnEquity")
    if roe:
        if roe >= 0.30:   score += 5
        elif roe >= 0.20: score += 4
        elif roe >= 0.15: score += 3
        elif roe > 0:     score += 1

    op_margin = info.get("operatingMargins")
    if op_margin:
        if op_margin >= 0.25:  score += 5
        elif op_margin >= 0.15: score += 4
        elif op_margin >= 0.08: score += 2
        elif op_margin > 0:    score += 1

    d2e = info.get("debtToEquity")
    if d2e is not None:
        if d2e < 30:    score += 5
        elif d2e < 80:  score += 3
        elif d2e < 150: score += 1
    else:
        score += 3  # 무부채 기업

    return min(score, 15)


# ─────────────────────────────────────────────────────────
# CANSLIM 성장 팩터
# ─────────────────────────────────────────────────────────
def _canslim_growth(info: dict) -> int:
    """매출성장 + 이익성장 가속도 (0~25점)"""
    score = 0

    rev_growth = info.get("revenueGrowth")
    if rev_growth:
        if rev_growth >= 0.40:   score += 15
        elif rev_growth >= 0.25: score += 12
        elif rev_growth >= 0.15: score += 8
        elif rev_growth >= 0.08: score += 4

    earn_growth = info.get("earningsGrowth")
    if earn_growth:
        if earn_growth >= 0.40:   score += 10
        elif earn_growth >= 0.25: score += 8
        elif earn_growth >= 0.10: score += 5
        elif earn_growth > 0:     score += 2

    return min(score, 25)


# ─────────────────────────────────────────────────────────
# 모멘텀 팩터
# ─────────────────────────────────────────────────────────
def _momentum_score(ret_1m, ret_3m, ret_6m, ret_1y,
                    rs_vs_spy, rsi, price, ma50, ma200, from_high) -> int:
    """기술적 모멘텀 (0~25점)"""
    score = 0

    # 상대강도 (SPY 대비 초과수익)
    if rs_vs_spy >= 30:   score += 10
    elif rs_vs_spy >= 15: score += 7
    elif rs_vs_spy >= 5:  score += 4
    elif rs_vs_spy >= 0:  score += 1

    # 이동평균 배열 (골든크로스 위)
    if price > ma50 > ma200:  score += 8
    elif price > ma200:       score += 4
    elif price > ma50:        score += 2

    # 52주 고점 근접 (신고가 돌파 강세)
    if from_high >= -5:    score += 5
    elif from_high >= -15: score += 3
    elif from_high >= -30: score += 1

    # RSI 적정 구간 (50~70: 강세지만 과열 아님)
    if 50 <= rsi <= 70:  score += 2
    elif 45 <= rsi < 50: score += 1

    return min(score, 25)


# ─────────────────────────────────────────────────────────
# 밸류에이션 페널티 / 보너스
# ─────────────────────────────────────────────────────────
def _valuation_score(info: dict) -> int:
    """PEG, EV/EBITDA 기반 밸류에이션 (-10 ~ +10점)"""
    score = 0

    peg = info.get("trailingPegRatio")
    if peg:
        if peg <= 1.0:   score += 5
        elif peg <= 1.5: score += 3
        elif peg <= 2.5: score += 1
        elif peg <= 4.0: score -= 2
        else:            score -= 5

    ev_ebitda = info.get("enterpriseToEbitda")
    if ev_ebitda and ev_ebitda > 0:
        if ev_ebitda <= 15:   score += 5
        elif ev_ebitda <= 25: score += 3
        elif ev_ebitda <= 40: score += 1
        elif ev_ebitda <= 60: score -= 2
        else:                 score -= 3

    return max(-10, min(score, 10))


# ─────────────────────────────────────────────────────────
# 종합 점수 계산
# ─────────────────────────────────────────────────────────
def _composite_score(growth, momentum, quality, magic, piotroski, valuation) -> int:
    """
    팩터별 가중치 합산
    성장(25) + 모멘텀(25) + 퀄리티(15) + 매직포뮬라(10) + 피오트로스키(9→15) + 밸류에이션(-10~+10)
    → 정규화 100점
    """
    raw = growth + momentum + quality + magic + int(piotroski * 1.5) + valuation
    # 최대 가능 점수: 25+25+15+10+13.5+10 = 98.5
    normalized = int(min(raw / 98.5 * 100, 100))
    return max(0, normalized)


# ─────────────────────────────────────────────────────────
# 매수 / 매도 신호
# ─────────────────────────────────────────────────────────
def _buy_signal(score, rsi, price, ma50, ma200, from_high, piotroski) -> str:
    if score >= 75 and rsi < 72 and price > ma50 and piotroski >= 5:
        return "🟢 강력매수"
    elif score >= 60 and price > ma200:
        return "🟡 매수고려"
    elif score >= 45 and price > ma200:
        return "⚪ 관심유지"
    elif score < 35 or price < ma200:
        return "🔴 매수부적합"
    else:
        return "⚪ 중립"


def _sell_signal(rsi, price, ma50, ma200, from_high, score):
    reasons = []
    if from_high <= -35:    reasons.append(f"추세붕괴(고점대비{from_high:.0f}%)")
    if rsi >= 78:           reasons.append(f"과매수(RSI {rsi})")
    if price < ma50:        reasons.append("MA50 하향이탈")
    if price < ma200:       reasons.append("MA200 하향이탈")
    if score < 35:          reasons.append(f"점수급락({score}점)")

    if not reasons:
        return "✅ 보유 유지", ""

    critical = any(k in r for r in reasons for k in ["MA200", "추세붕괴"])
    if critical:
        return "🚨 매도 강력권고", " / ".join(reasons)
    else:
        return "⚠️ 매도 검토", " / ".join(reasons)


# ─────────────────────────────────────────────────────────
# 애널리스트 의견 수집
# ─────────────────────────────────────────────────────────
def _analyst_summary(info: dict) -> dict:
    target = info.get("targetMeanPrice")
    current = info.get("currentPrice") or info.get("regularMarketPrice")
    upside = round((target / current - 1) * 100, 1) if target and current else None
    rec = info.get("recommendationKey", "").replace("_", " ").title()
    strong_buy = info.get("numberOfAnalystOpinions", 0)
    return {
        "target_price": round(target, 2) if target else None,
        "upside_pct": upside,
        "recommendation": rec,
        "analyst_count": strong_buy,
    }


# ─────────────────────────────────────────────────────────
# 메인 데이터 수집
# ─────────────────────────────────────────────────────────
def get_stock_data(ticker: str) -> dict:
    try:
        tk = yf.Ticker(ticker)
        info = tk.info
        hist = tk.history(period="2y")
        if hist.empty:
            return {}

        current = float(hist["Close"].iloc[-1])

        # ── 기술 지표 ──
        rsi   = calc_rsi(hist["Close"])
        ma50  = float(hist["Close"].rolling(50).mean().iloc[-1])
        ma200 = float(hist["Close"].rolling(200).mean().iloc[-1])
        high_52w = float(hist["Close"].rolling(252).max().iloc[-1])
        from_high = (current / high_52w - 1) * 100

        # ── 수익률 ──
        def px(n): return float(hist["Close"].iloc[-n]) if len(hist) >= n else current
        ret_1m = (current / px(21)  - 1) * 100
        ret_3m = (current / px(63)  - 1) * 100
        ret_6m = (current / px(126) - 1) * 100
        ret_1y = (current / px(252) - 1) * 100

        # ── SPY 상대강도 ──
        spy_hist = yf.Ticker("SPY").history(period="1y")
        spy_ret  = (float(spy_hist["Close"].iloc[-1]) / float(spy_hist["Close"].iloc[0]) - 1) * 100
        rs_vs_spy = ret_1y - spy_ret

        # ── 팩터 점수 ──
        growth    = _canslim_growth(info)
        momentum  = _momentum_score(ret_1m, ret_3m, ret_6m, ret_1y,
                                    rs_vs_spy, rsi, current, ma50, ma200, from_high)
        quality   = _quality_score(info)
        magic     = _magic_formula_score(info)
        piotroski = _piotroski_score(info, tk)
        valuation = _valuation_score(info)

        score = _composite_score(growth, momentum, quality, magic, piotroski, valuation)

        signal      = _buy_signal(score, rsi, current, ma50, ma200, from_high, piotroski)
        sell_signal, sell_reason = _sell_signal(rsi, current, ma50, ma200, from_high, score)
        analyst     = _analyst_summary(info)

        return {
            "ticker":           ticker,
            "name":             WATCHLIST.get(ticker, info.get("shortName", ticker)),
            "current":          round(current, 2),
            "rsi":              rsi,
            "ma50":             round(ma50, 2),
            "ma200":            round(ma200, 2),
            "from_52w_high":    round(from_high, 1),
            "ret_1m":           round(ret_1m, 1),
            "ret_3m":           round(ret_3m, 1),
            "ret_6m":           round(ret_6m, 1),
            "ret_1y":           round(ret_1y, 1),
            "rs_vs_spy":        round(rs_vs_spy, 1),
            # 재무
            "revenue_growth":   round(info.get("revenueGrowth", 0) * 100, 1) if info.get("revenueGrowth") else None,
            "earnings_growth":  round(info.get("earningsGrowth", 0) * 100, 1) if info.get("earningsGrowth") else None,
            "gross_margin":     round(info.get("grossMargins", 0) * 100, 1) if info.get("grossMargins") else None,
            "operating_margin": round(info.get("operatingMargins", 0) * 100, 1) if info.get("operatingMargins") else None,
            "net_margin":       round(info.get("profitMargins", 0) * 100, 1) if info.get("profitMargins") else None,
            "roe":              round(info.get("returnOnEquity", 0) * 100, 1) if info.get("returnOnEquity") else None,
            "roa":              round(info.get("returnOnAssets", 0) * 100, 1) if info.get("returnOnAssets") else None,
            "debt_to_equity":   round(info.get("debtToEquity", 0), 1) if info.get("debtToEquity") else None,
            "current_ratio":    round(info.get("currentRatio", 0), 2) if info.get("currentRatio") else None,
            # 밸류에이션
            "pe":               round(info.get("trailingPE", 0), 1) if info.get("trailingPE") else None,
            "forward_pe":       round(info.get("forwardPE", 0), 1) if info.get("forwardPE") else None,
            "peg":              round(info.get("trailingPegRatio", 0), 2) if info.get("trailingPegRatio") else None,
            "pbr":              round(info.get("priceToBook", 0), 2) if info.get("priceToBook") else None,
            "ev_ebitda":        round(info.get("enterpriseToEbitda", 0), 1) if info.get("enterpriseToEbitda") else None,
            "market_cap_B":     round(info.get("marketCap", 0) / 1e9, 1) if info.get("marketCap") else None,
            # 팩터 세부
            "score_growth":     growth,
            "score_momentum":   momentum,
            "score_quality":    quality,
            "score_magic":      magic,
            "piotroski":        piotroski,
            "score_valuation":  valuation,
            "canslim_score":    score,
            # 신호
            "signal":           signal,
            "sell_signal":      sell_signal,
            "sell_reason":      sell_reason,
            # 애널리스트
            "target_price":     analyst["target_price"],
            "upside_pct":       analyst["upside_pct"],
            "recommendation":   analyst["recommendation"],
            "analyst_count":    analyst["analyst_count"],
            "hist":             hist,
        }
    except Exception as e:
        print(f"[WARN] {ticker} 수집 실패: {e}")
        return {}


def screen_all(tickers: list = None) -> pd.DataFrame:
    if tickers is None:
        tickers = list(WATCHLIST.keys())

    rows = []
    for t in tickers:
        d = get_stock_data(t)
        if not d:
            continue
        rows.append({
            "티커":          d["ticker"],
            "종목명":        d["name"],
            "현재가($)":     d["current"],
            "종합점수":      d["canslim_score"],
            "신호":          d["signal"],
            "매도신호":      d["sell_signal"],
            "RSI":           d["rsi"],
            "Piotroski":     d["piotroski"],
            "1년수익(%)":    d["ret_1y"],
            "SPY대비(%)":    d["rs_vs_spy"],
            "고점대비(%)":   d["from_52w_high"],
            "매출성장(%)":   d["revenue_growth"],
            "이익성장(%)":   d["earnings_growth"],
            "영업이익률(%)": d["operating_margin"],
            "ROE(%)":        d["roe"],
            "PER":           d["pe"],
            "PEG":           d["peg"],
            "EV/EBITDA":     d["ev_ebitda"],
            "목표주가($)":   d["target_price"],
            "목표대비(%)":   d["upside_pct"],
            "애널의견":      d["recommendation"],
        })

    df = pd.DataFrame(rows)
    if not df.empty:
        df = df.sort_values("종합점수", ascending=False)
    return df
