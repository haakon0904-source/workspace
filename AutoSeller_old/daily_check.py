"""
일일 자동 체크 스크립트
- 전체 워치리스트 분석 → 텔레그램 종합 리포트 전송
실행: python3 daily_check.py
크론: 0 9 * * 1-5 /Library/Frameworks/Python.framework/Versions/3.13/bin/python3 /Users/parkyongjin/PycharmProjects/stock_system/daily_check.py >> /Users/parkyongjin/PycharmProjects/stock_system/logs/daily.log 2>&1
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.chdir(os.path.dirname(os.path.abspath(__file__)))

from analyzers.screener import get_stock_data, WATCHLIST
from analyzers.earnings import get_earnings_data
from analyzers.notifier import send_daily_report, send_earnings_alert, is_connected


def run():
    if not is_connected():
        print("[SKIP] 텔레그램 미연동 - .env에 TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID 설정 필요")
        return

    now = __import__("datetime").datetime.now().strftime("%Y-%m-%d %H:%M")
    print(f"[{now}] 일일 체크 시작...")

    stock_data_list = []

    for ticker in WATCHLIST:
        print(f"  분석 중: {ticker}")
        try:
            d = get_stock_data(ticker)
            if d:
                stock_data_list.append(d)
        except Exception as e:
            print(f"  [WARN] {ticker} 오류: {e}")

    # 점수 내림차순 정렬
    stock_data_list.sort(key=lambda x: x.get("canslim_score", 0), reverse=True)

    strong_buy = [d for d in stock_data_list if "강력매수" in d.get("signal", "")]
    sell_alert = [d for d in stock_data_list if "강력권고" in d.get("sell_signal", "")]
    print(f"강력매수: {len(strong_buy)}개 / 매도강력권고: {len(sell_alert)}개")

    # 종합 리포트 전송
    ok = send_daily_report(stock_data_list)
    print("텔레그램 전송:", "성공" if ok else "실패")

    # 실적 임박 종목 별도 알림 (7일 이내)
    for ticker in WATCHLIST:
        try:
            ed = get_earnings_data(ticker)
            days_to = ed.get("days_to_earnings")
            if days_to and 0 < days_to <= 7:
                send_earnings_alert(ticker, ed["next_earnings_date"], days_to)
                print(f"  실적 알림: {ticker} D-{days_to}")
        except Exception:
            pass


if __name__ == "__main__":
    run()
