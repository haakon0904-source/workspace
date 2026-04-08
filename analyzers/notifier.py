"""
텔레그램 알림 모듈
- 매수/매도/실적 알림
- 일일 종합 리포트 (리치 포맷)
"""
import os
import requests
from datetime import datetime
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))


def _get_credentials():
    token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "")
    return token, chat_id


def is_connected() -> bool:
    token, chat_id = _get_credentials()
    return bool(token and chat_id)


def send_message(text: str) -> bool:
    token, chat_id = _get_credentials()
    if not token or not chat_id:
        print("[WARN] 텔레그램 자격증명 없음 (.env 확인)")
        return False
    try:
        resp = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"},
            timeout=10,
        )
        return resp.json().get("ok", False)
    except Exception as e:
        print(f"[WARN] 텔레그램 전송 실패: {e}")
        return False


def _score_bar(score: int) -> str:
    """점수를 시각적 바로 변환 (0~100)"""
    filled = int(score / 10)
    return "█" * filled + "░" * (10 - filled) + f" {score}pt"


def send_daily_report(stock_data_list: list):
    """
    하루 1회 종합 리포트 전송
    stock_data_list: get_stock_data() 결과 딕셔너리 리스트 (점수 내림차순)
    """
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = [f"📊 <b>주식 분석 일일 리포트</b>  {now}\n"]

    # ── 1. 강력매수 후보 ──────────────────────────────────
    strong = [d for d in stock_data_list if "강력매수" in d.get("signal", "")]
    consider = [d for d in stock_data_list if "매수고려" in d.get("signal", "")]

    if strong:
        lines.append("🟢 <b>강력매수 후보</b>")
        for d in strong:
            lines.append(_format_stock_brief(d))
        lines.append("")

    if consider:
        lines.append("🟡 <b>매수 고려</b>")
        for d in consider:
            lines.append(_format_stock_brief(d))
        lines.append("")

    # ── 2. 매도 경보 ──────────────────────────────────────
    sell_strong = [d for d in stock_data_list if "강력권고" in d.get("sell_signal", "")]
    sell_watch  = [d for d in stock_data_list if "매도 검토" in d.get("sell_signal", "")]

    if sell_strong:
        lines.append("🚨 <b>매도 강력권고</b>")
        for d in sell_strong:
            lines.append(f"  • <b>{d['ticker']}</b> ${d['current']} — {d.get('sell_reason','')}")
        lines.append("")

    if sell_watch:
        lines.append("⚠️ <b>매도 검토</b>")
        for d in sell_watch:
            lines.append(f"  • <b>{d['ticker']}</b> ${d['current']} — {d.get('sell_reason','')}")
        lines.append("")

    # ── 3. 전체 순위 ──────────────────────────────────────
    lines.append("📋 <b>전체 종합 순위</b>")
    lines.append(f"{'순위':<2} {'티커':<5} {'점수':>4} {'신호':<8} {'1년%':>6}")
    lines.append("─" * 35)
    for i, d in enumerate(stock_data_list[:10], 1):
        signal_icon = {"강력매수": "🟢", "매수고려": "🟡", "관심유지": "⚪", "매수부적합": "🔴"}.get(
            d.get("signal", "").replace("🟢 ","").replace("🟡 ","").replace("⚪ ","").replace("🔴 ",""), "⚪"
        )
        ret = d.get("ret_1y", 0) or 0
        ret_str = f"+{ret:.0f}%" if ret >= 0 else f"{ret:.0f}%"
        lines.append(f"{i:<2} {d['ticker']:<5} {d['canslim_score']:>4}pt {signal_icon} {d.get('signal','').split()[-1]:<6} {ret_str:>6}")

    lines.append("")

    # ── 4. 시장 체크 (SPY 기준) ──────────────────────────
    spy_stocks = [d for d in stock_data_list if d.get("rs_vs_spy") is not None]
    if spy_stocks:
        avg_rs = sum(d["rs_vs_spy"] for d in spy_stocks) / len(spy_stocks)
        market_mood = "🔥 강세" if avg_rs > 10 else ("😐 중립" if avg_rs > -5 else "❄️ 약세")
        lines.append(f"📈 <b>시장 분위기</b>: {market_mood}  (워치리스트 평균 SPY대비 {avg_rs:+.1f}%)")

    return send_message("\n".join(lines))


def _format_stock_brief(d: dict) -> str:
    """종목 간략 요약 (텔레그램 1개 종목)"""
    ticker = d["ticker"]
    name = d.get("name", "")
    price = d.get("current", 0)
    score = d.get("canslim_score", 0)
    piotroski = d.get("piotroski", "-")
    rsi = d.get("rsi", "-")
    rev_g = d.get("revenue_growth")
    earn_g = d.get("earnings_growth")
    roe = d.get("roe")
    op_margin = d.get("operating_margin")
    pe = d.get("pe")
    peg = d.get("peg")
    target = d.get("target_price")
    upside = d.get("upside_pct")
    rec = d.get("recommendation", "")
    ret_1y = d.get("ret_1y", 0) or 0
    rs = d.get("rs_vs_spy", 0) or 0
    from_high = d.get("from_52w_high", 0) or 0

    lines = [
        f"\n  <b>{ticker}</b> ({name})  ${price}",
        f"  점수: {_score_bar(score)}",
        f"  재무건전성(Piotroski): {piotroski}/9",
        f"  RSI {rsi} | 고점대비 {from_high:+.1f}% | SPY대비 {rs:+.1f}%",
    ]
    if rev_g is not None:
        lines.append(f"  매출성장 {rev_g:+.1f}% | 이익성장 {earn_g:+.1f}%" if earn_g else f"  매출성장 {rev_g:+.1f}%")
    if roe is not None:
        lines.append(f"  ROE {roe:.1f}% | 영업이익률 {op_margin:.1f}%" if op_margin else f"  ROE {roe:.1f}%")
    if pe is not None:
        val_str = f"  PER {pe:.1f}"
        if peg: val_str += f" | PEG {peg:.2f}"
        lines.append(val_str)
    if target and upside is not None:
        lines.append(f"  애널 목표가 ${target} ({upside:+.1f}%) — {rec}")
    lines.append(f"  1년 수익률 {ret_1y:+.1f}%")
    return "\n".join(lines)


def send_buy_alert(ticker: str, signal: str, score: int, price: float, rsi: float):
    text = (
        f"📈 <b>[매수 신호] {ticker}</b>\n"
        f"신호: {signal}\n"
        f"현재가: ${price}\n"
        f"종합점수: {score}/100\n"
        f"RSI: {rsi}\n"
        f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    )
    return send_message(text)


def send_sell_alert(ticker: str, signal: str, reason: str, price: float):
    text = (
        f"🚨 <b>[매도 신호] {ticker}</b>\n"
        f"신호: {signal}\n"
        f"사유: {reason}\n"
        f"현재가: ${price}\n"
        f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    )
    return send_message(text)


def send_earnings_alert(ticker: str, next_date: str, days_to: int):
    text = (
        f"📅 <b>[실적 발표 임박] {ticker}</b>\n"
        f"발표일: {next_date}\n"
        f"D-{days_to}\n"
        f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    )
    return send_message(text)


def send_daily_summary(buy_list: list, sell_list: list, earnings_list: list):
    """기존 호환용 단순 요약 (daily_check.py에서 사용)"""
    lines = [f"📊 <b>주식 일일 요약 {datetime.now().strftime('%Y-%m-%d')}</b>"]

    if buy_list:
        lines.append(f"\n📈 매수 신호 ({len(buy_list)}개)")
        for item in buy_list:
            lines.append(f"  • <b>{item['ticker']}</b> {item['signal']} (점수 {item['score']})")

    if sell_list:
        lines.append(f"\n🚨 매도 신호 ({len(sell_list)}개)")
        for item in sell_list:
            lines.append(f"  • <b>{item['ticker']}</b> {item['signal']}")
            if item.get("reason"):
                lines.append(f"    └ {item['reason']}")

    if earnings_list:
        lines.append(f"\n📅 실적 임박 ({len(earnings_list)}개)")
        for item in earnings_list:
            lines.append(f"  • <b>{item['ticker']}</b> D-{item['days_to']} ({item['date']})")

    if not buy_list and not sell_list and not earnings_list:
        lines.append("\n특이 신호 없음. 보유 유지.")

    return send_message("\n".join(lines))
