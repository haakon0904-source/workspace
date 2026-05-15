"""
실적 데이터 모듈
- 다음 실적 발표일
- 분기별 EPS / 매출 추이
- EPS 서프라이즈 (예상 vs 실제)
"""
import yfinance as yf
import pandas as pd
from datetime import datetime
from typing import Dict, Optional


def get_earnings_data(ticker: str) -> Dict:
    """
    종목의 실적 관련 데이터 수집
    반환: {
        next_earnings_date, days_to_earnings,
        quarterly_eps, quarterly_revenue,
        eps_surprise_avg, last_surprise_pct
    }
    """
    try:
        tk = yf.Ticker(ticker)

        # 다음 실적 발표일
        next_date = None
        days_to = None
        try:
            cal = tk.calendar
            if cal is not None and not cal.empty:
                # calendar는 dict 또는 DataFrame 형태로 올 수 있음
                if isinstance(cal, dict):
                    earn_date = cal.get("Earnings Date")
                    if earn_date and len(earn_date) > 0:
                        next_date = pd.Timestamp(earn_date[0]).strftime("%Y-%m-%d")
                        days_to = (pd.Timestamp(earn_date[0]) - pd.Timestamp.now()).days
                elif hasattr(cal, 'loc'):
                    if "Earnings Date" in cal.index:
                        earn_val = cal.loc["Earnings Date"]
                        if hasattr(earn_val, '__iter__'):
                            next_date = pd.Timestamp(list(earn_val)[0]).strftime("%Y-%m-%d")
                        else:
                            next_date = pd.Timestamp(earn_val).strftime("%Y-%m-%d")
                        days_to = (pd.Timestamp(next_date) - pd.Timestamp.now()).days
        except Exception:
            pass

        # 분기별 재무 (EPS, 매출)
        quarterly_eps = []
        quarterly_revenue = []
        try:
            # 분기 재무제표
            qf = tk.quarterly_financials
            qi = tk.quarterly_income_stmt

            fin = qi if (qi is not None and not qi.empty) else qf
            if fin is not None and not fin.empty:
                # 매출
                rev_row = None
                for key in ["Total Revenue", "Revenue"]:
                    if key in fin.index:
                        rev_row = fin.loc[key]
                        break
                if rev_row is not None:
                    for col in rev_row.index[:8]:  # 최근 8분기
                        val = rev_row[col]
                        if pd.notna(val):
                            quarterly_revenue.append({
                                "quarter": str(col)[:7],
                                "revenue_B": round(float(val) / 1e9, 2),
                            })
                quarterly_revenue = list(reversed(quarterly_revenue))

                # 영업이익 (EPS 대용)
                op_row = None
                for key in ["Net Income", "Operating Income"]:
                    if key in fin.index:
                        op_row = fin.loc[key]
                        break
                if op_row is not None:
                    for col in op_row.index[:8]:
                        val = op_row[col]
                        if pd.notna(val):
                            quarterly_eps.append({
                                "quarter": str(col)[:7],
                                "net_income_B": round(float(val) / 1e9, 2),
                            })
                quarterly_eps = list(reversed(quarterly_eps))
        except Exception:
            pass

        # EPS 서프라이즈 (yfinance earnings_history)
        eps_surprise_avg = None
        last_surprise_pct = None
        surprise_history = []
        try:
            eh = tk.earnings_history
            if eh is not None and not eh.empty:
                # 최근 4~8개 분기
                recent = eh.tail(8).copy()
                recent = recent.dropna(subset=["epsEstimate", "epsActual"])
                for _, row in recent.iterrows():
                    est = float(row["epsEstimate"])
                    act = float(row["epsActual"])
                    surprise_pct = ((act - est) / abs(est) * 100) if est != 0 else 0
                    surprise_history.append({
                        "quarter": str(row.get("quarter", ""))[:7],
                        "estimate": round(est, 2),
                        "actual": round(act, 2),
                        "surprise_pct": round(surprise_pct, 1),
                    })
                if surprise_history:
                    eps_surprise_avg = round(
                        sum(s["surprise_pct"] for s in surprise_history) / len(surprise_history), 1
                    )
                    last_surprise_pct = surprise_history[-1]["surprise_pct"]
        except Exception:
            pass

        return {
            "ticker": ticker,
            "next_earnings_date": next_date,
            "days_to_earnings": days_to,
            "quarterly_revenue": quarterly_revenue,
            "quarterly_eps": quarterly_eps,
            "surprise_history": surprise_history,
            "eps_surprise_avg": eps_surprise_avg,
            "last_surprise_pct": last_surprise_pct,
        }

    except Exception as e:
        print(f"[WARN] {ticker} 실적 데이터 수집 실패: {e}")
        return {"ticker": ticker, "next_earnings_date": None, "days_to_earnings": None,
                "quarterly_revenue": [], "quarterly_eps": [], "surprise_history": [],
                "eps_surprise_avg": None, "last_surprise_pct": None}
