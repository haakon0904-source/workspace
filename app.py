"""
미국 주식 투자 분석 대시보드
실행: streamlit run app.py
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import sys, os
from datetime import datetime

sys.path.insert(0, os.path.dirname(__file__))
from analyzers.etf import get_etf_data, compare_etfs, ETF_LIST, get_exchange_rate
from analyzers.screener import get_stock_data, screen_all, WATCHLIST
from analyzers.earnings import get_earnings_data
from analyzers.portfolio import (
    load, add_trade, delete_trade, calc_portfolio, calc_goal_progress,
    MONTHLY_KRW, GOAL_RETURN_PCT, GOAL_YEARS
)
from analyzers.kis_api import sync_portfolio_from_kis, get_overseas_transactions
from analyzers.notifier import is_connected, send_message, send_buy_alert, send_sell_alert

st.set_page_config(page_title="주식 투자 분석", page_icon="📈", layout="wide")

st.markdown("""
<style>
.metric-card {background:#f8f9fa;border-radius:8px;padding:12px 16px;margin:4px;}
.green {color:#00b894;font-weight:700;}
.red   {color:#e17055;font-weight:700;}
.gold  {color:#fdcb6e;font-weight:700;}
</style>
""", unsafe_allow_html=True)

st.title("📈 미국 주식 투자 분석 대시보드")
st.caption("ETF 50% + 주도주 50% · 월 150만원 적립 · 4년 100% 목표")

# ── 사이드바: 텔레그램 연동 ──────────────────────────────────
with st.sidebar:
    st.markdown("### 🔔 텔레그램 알림")

    if is_connected():
        st.success("연동 완료")
        if st.button("📨 테스트 메시지"):
            ok = send_message("✅ 주식 대시보드 알림 테스트\n정상 연동되었습니다!")
            st.toast("전송 완료!" if ok else "전송 실패")
    else:
        st.warning("미연동")
        st.caption(".env 파일에 TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID 설정 필요")

    st.divider()
    st.markdown("### ⚙️ 자동 알림 설정")
    st.caption("매일 오전 9시 자동 실행:")
    st.code("python3 daily_check.py", language="bash")
    st.caption("크론 등록:")
    st.code("crontab -e\n# 추가:\n0 9 * * 1-5 cd /Users/parkyongjin/PycharmProjects/stock_system && python3 daily_check.py >> logs/daily.log 2>&1", language="bash")

tab1, tab2, tab3, tab4 = st.tabs(["🏦 ETF 분석", "🚀 주도주 스크리닝", "💼 내 포트폴리오", "🎯 목표 관리"])


# ──────────────────────────────────────────────────────────
# TAB 1: ETF 분석
# ──────────────────────────────────────────────────────────
with tab1:
    st.markdown("### 🏦 ETF 비교 분석")
    st.caption("RSI 기반 모멘텀 DCA: 과매도 시 더 많이, 과매수 시 적게 매수하는 전략")

    # 카테고리별 그룹 표시
    from analyzers.etf import ETF_LIST as _EL
    categories = {}
    for t, info in _EL.items():
        cat = info.get("category", "기타")
        categories.setdefault(cat, []).append(t)

    cat_cols = st.columns(len(categories))
    for i, (cat, tickers) in enumerate(categories.items()):
        with cat_cols[i]:
            st.caption(f"**{cat}**")
            st.write(" / ".join(tickers))

    selected_etfs = st.multiselect(
        "분석할 ETF 선택",
        list(ETF_LIST.keys()),
        default=["QQQ", "SPY", "SCHD", "SOXX", "USO", "GLD", "EWY", "TLT"],
        format_func=lambda x: f"{x} ({ETF_LIST[x]['name']})",
    )

    if st.button("📊 ETF 분석 실행", type="primary"):
        with st.spinner("데이터 수집 중..."):
            exrate = get_exchange_rate()
            etf_data = {t: get_etf_data(t) for t in selected_etfs}
            st.session_state["etf_data"] = etf_data
            st.session_state["exrate"] = exrate

    if "etf_data" in st.session_state:
        etf_data = st.session_state["etf_data"]
        exrate   = st.session_state.get("exrate", 1350)

        # ETF 설명
        for t, info in ETF_LIST.items():
            if t in selected_etfs:
                cat = info.get("category", "")
                st.caption(f"**{t}** [{cat}] — {info['desc']}")

        st.divider()

        # 카드형 현황
        cols = st.columns(len(selected_etfs))
        for i, t in enumerate(selected_etfs):
            d = etf_data.get(t, {})
            if not d:
                continue
            with cols[i]:
                pct_color = "green" if (d.get("ret_1y") or 0) > 0 else "red"
                st.markdown(f"""
                <div class="metric-card">
                <b>{t}</b> {ETF_LIST.get(t,{}).get('name','')}<br>
                <span style="font-size:20px;font-weight:700">${d['current']:.2f}</span><br>
                1년 <span class="{pct_color}">{d.get('ret_1y','N/A')}%</span>
                &nbsp;|&nbsp; RSI <b>{d['rsi']}</b><br>
                {d['signal']}
                </div>
                """, unsafe_allow_html=True)

        st.divider()

        # 비교 테이블
        st.markdown("#### 📋 상세 비교")
        rows = []
        for t in selected_etfs:
            d = etf_data.get(t, {})
            if not d:
                continue
            monthly_krw = 750_000  # ETF 50% 중 분배 (기본 예시)
            buy_amount = int(monthly_krw * d["dca_ratio"])
            rows.append({
                "티커": t,
                "이름": ETF_LIST.get(t, {}).get("name", ""),
                "현재가($)": d["current"],
                "RSI": d["rsi"],
                "1개월(%)": d.get("ret_1m"),
                "3개월(%)": d.get("ret_3m"),
                "1년(%)": d.get("ret_1y"),
                "4년(%)": d.get("ret_4y"),
                "변동성(%)": d["volatility"],
                "고점대비(%)": d["drawdown"],
                "비용(%)": d.get("expense_ratio"),
                "이번달매수(원)": f"{buy_amount:,}",
                "DCA신호": d["signal"],
            })
        if rows:
            df = pd.DataFrame(rows)
            st.dataframe(df, use_container_width=True, hide_index=True)

        # 수익률 차트
        st.markdown("#### 📈 수익률 추이 (1년)")
        fig = go.Figure()
        for t in selected_etfs:
            d = etf_data.get(t, {})
            if not d or d.get("hist") is None:
                continue
            hist = d["hist"].tail(252)
            norm = hist["Close"] / hist["Close"].iloc[0] * 100 - 100
            fig.add_trace(go.Scatter(x=hist.index, y=norm, name=t, mode="lines"))
        fig.update_layout(
            yaxis_title="수익률 (%)", xaxis_title="",
            hovermode="x unified", height=350,
            legend=dict(orientation="h", yanchor="bottom", y=1.02)
        )
        st.plotly_chart(fig, use_container_width=True)

        # 이번달 DCA 가이드
        st.markdown("#### 💡 이번달 ETF 매수 가이드")
        etf_budget = sum(MONTHLY_KRW.values()) * 0.5  # ETF 50%
        st.info(f"이번달 ETF 예산: **{etf_budget:,.0f}원** (월 150만원의 50%)")
        for t in selected_etfs:
            d = etf_data.get(t, {})
            if not d:
                continue
            per_etf = etf_budget / len(selected_etfs)
            adjusted = per_etf * d["dca_ratio"]
            shares_est = adjusted / exrate / d["current"]
            st.write(f"- **{t}**: {d['signal']} → 예산 {adjusted:,.0f}원 (약 {shares_est:.2f}주 @ ${d['current']})")


# ──────────────────────────────────────────────────────────
# TAB 2: 주도주 스크리닝
# ──────────────────────────────────────────────────────────
with tab2:
    st.markdown("### 🚀 주도주 스크리닝")
    st.caption("CANSLIM + 퀄리티 성장주 혼합 · 점수 75+ 종목이 매수 적합")

    col_a, col_b = st.columns([3, 1])
    with col_a:
        selected_stocks = st.multiselect(
            "분석할 종목 선택",
            list(WATCHLIST.keys()),
            default=["NVDA", "MSFT", "META", "GOOGL", "AAPL", "AVGO", "PLTR", "APP"],
            format_func=lambda x: f"{x} — {WATCHLIST[x]}",
        )
    with col_b:
        custom = st.text_input("직접 입력 (쉼표 구분)", placeholder="예: ORCL,SNOW")

    if custom:
        extra = [t.strip().upper() for t in custom.split(",") if t.strip()]
        selected_stocks = list(dict.fromkeys(selected_stocks + extra))

    if st.button("🔍 스크리닝 실행", type="primary"):
        with st.spinner(f"{len(selected_stocks)}개 종목 분석 중..."):
            stock_data = {t: get_stock_data(t) for t in selected_stocks}
            earnings_data = {t: get_earnings_data(t) for t in selected_stocks}
            st.session_state["stock_data"] = stock_data
            st.session_state["earnings_data"] = earnings_data

    if "stock_data" in st.session_state:
        stock_data = st.session_state["stock_data"]
        exrate = get_exchange_rate()

        # 요약 카드 (상위 종목)
        sorted_stocks = sorted(
            [(t, d) for t, d in stock_data.items() if d],
            key=lambda x: x[1].get("canslim_score", 0), reverse=True
        )

        st.markdown("#### 🏆 종합 순위")
        cols = st.columns(min(4, len(sorted_stocks)))
        for i, (t, d) in enumerate(sorted_stocks[:4]):
            with cols[i]:
                score = d["canslim_score"]
                score_color = "green" if score >= 75 else ("gold" if score >= 55 else "red")
                st.markdown(f"""
                <div class="metric-card">
                <b>{t}</b><br>
                <span style="font-size:18px;font-weight:700">${d['current']}</span><br>
                점수 <span class="{score_color}"><b>{score}/100</b></span><br>
                {d['signal']}<br>
                <small>RSI {d['rsi']} | 1년 {d['ret_1y']}%</small>
                </div>
                """, unsafe_allow_html=True)

        st.divider()

        # 상세 테이블
        st.markdown("#### 📋 스크리닝 결과")
        earnings_data = st.session_state.get("earnings_data", {})
        rows = []
        for t, d in sorted_stocks:
            ed = earnings_data.get(t, {})
            next_earn = ed.get("next_earnings_date", "-") or "-"
            days_to = ed.get("days_to_earnings")
            earn_str = f"{next_earn} (D-{days_to})" if days_to and days_to > 0 else next_earn
            rows.append({
                "티커":          d["ticker"],
                "종목명":        d["name"],
                "현재가($)":     d["current"],
                "종합점수":      d["canslim_score"],
                "신호":          d["signal"],
                "매도신호":      d.get("sell_signal", ""),
                "Piotroski":     d.get("piotroski"),
                "RSI":           d["rsi"],
                "고점대비(%)":   d["from_52w_high"],
                "1년수익(%)":    d["ret_1y"],
                "SPY대비(%)":    d["rs_vs_spy"],
                "매출성장(%)":   d.get("revenue_growth"),
                "이익성장(%)":   d.get("earnings_growth"),
                "ROE(%)":        d.get("roe"),
                "영업이익률(%)": d.get("operating_margin"),
                "PER":           d.get("pe"),
                "PEG":           d.get("peg"),
                "EV/EBITDA":     d.get("ev_ebitda"),
                "목표대비(%)":   d.get("upside_pct"),
                "애널의견":      d.get("recommendation"),
                "EPS서프라이즈": ed.get("eps_surprise_avg"),
                "다음실적발표":  earn_str,
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

        # 개별 종목 상세
        st.markdown("#### 🔎 종목 상세 차트")
        selected_detail = st.selectbox("종목 선택", [t for t, d in sorted_stocks])
        d = stock_data.get(selected_detail, {})
        if d:
            fig = go.Figure()
            hist = d["hist"].tail(504)  # 2년
            fig.add_trace(go.Candlestick(
                x=hist.index, open=hist["Open"], high=hist["High"],
                low=hist["Low"], close=hist["Close"], name="주가"
            ))
            # MA선
            ma50_line  = hist["Close"].rolling(50).mean()
            ma200_line = hist["Close"].rolling(200).mean()
            fig.add_trace(go.Scatter(x=hist.index, y=ma50_line,  name="MA50",  line=dict(color="orange", width=1)))
            fig.add_trace(go.Scatter(x=hist.index, y=ma200_line, name="MA200", line=dict(color="blue",   width=1)))
            fig.update_layout(
                height=400, xaxis_rangeslider_visible=False,
                title=f"{selected_detail} — {d['name']}",
            )
            st.plotly_chart(fig, use_container_width=True)

            # 핵심 지표 요약
            m1, m2, m3, m4, m5, m6 = st.columns(6)
            m1.metric("종합점수", f"{d['canslim_score']}/100")
            m2.metric("Piotroski", f"{d.get('piotroski','N/A')}/9")
            m3.metric("RSI", d["rsi"])
            m4.metric("52주 고점대비", f"{d['from_52w_high']}%")
            m5.metric("SPY 대비 1년", f"{d['rs_vs_spy']}%")
            m6.metric("목표가 괴리", f"{d.get('upside_pct','N/A')}%")

            # 팩터 레이더
            with st.expander("📊 팩터별 세부 점수"):
                fc1, fc2, fc3, fc4, fc5 = st.columns(5)
                fc1.metric("성장(CANSLIM)", f"{d.get('score_growth',0)}/25")
                fc2.metric("모멘텀", f"{d.get('score_momentum',0)}/25")
                fc3.metric("퀄리티", f"{d.get('score_quality',0)}/15")
                fc4.metric("매직포뮬라", f"{d.get('score_magic',0)}/10")
                fc5.metric("밸류에이션", f"{d.get('score_valuation',0):+d}pt")
                st.caption(
                    f"매출성장 {d.get('revenue_growth','N/A')}% | 이익성장 {d.get('earnings_growth','N/A')}% | "
                    f"ROE {d.get('roe','N/A')}% | ROA {d.get('roa','N/A')}% | "
                    f"영업이익률 {d.get('operating_margin','N/A')}% | 부채비율 {d.get('debt_to_equity','N/A')}% | "
                    f"PER {d.get('pe','N/A')} | ForwardPER {d.get('forward_pe','N/A')} | "
                    f"PEG {d.get('peg','N/A')} | PBR {d.get('pbr','N/A')} | EV/EBITDA {d.get('ev_ebitda','N/A')}"
                )
                if d.get("recommendation"):
                    st.info(f"애널리스트 의견: **{d['recommendation']}** | 목표주가 ${d.get('target_price','N/A')} "
                            f"(현재가 대비 {d.get('upside_pct','N/A')}%) | {d.get('analyst_count',0)}명")

            # 매도 신호 표시
            sell_sig = d.get("sell_signal", "")
            sell_reason = d.get("sell_reason", "")
            if "강력권고" in sell_sig:
                st.error(f"{sell_sig}  |  {sell_reason}")
            elif "검토" in sell_sig:
                st.warning(f"{sell_sig}  |  {sell_reason}")
            else:
                st.success(sell_sig)

            # 실적 차트
            ed = earnings_data.get(selected_detail, {})
            next_earn = ed.get("next_earnings_date")
            days_to = ed.get("days_to_earnings")
            if next_earn:
                label = f"📅 다음 실적 발표: **{next_earn}**"
                if days_to and days_to > 0:
                    label += f"  (D-{days_to})"
                    if days_to <= 14:
                        st.warning(label + "  ⚠️ 2주 이내!")
                    else:
                        st.info(label)
                else:
                    st.info(label)

            col_rev, col_surp = st.columns(2)

            with col_rev:
                qrev = ed.get("quarterly_revenue", [])
                if qrev:
                    df_rev = pd.DataFrame(qrev)
                    fig_rev = go.Figure(go.Bar(
                        x=df_rev["quarter"], y=df_rev["revenue_B"],
                        marker_color="steelblue", text=df_rev["revenue_B"].round(1),
                        textposition="outside",
                    ))
                    fig_rev.update_layout(
                        title="분기별 매출 (B$)", height=280,
                        margin=dict(t=40, b=20), yaxis_title="매출($B)",
                    )
                    st.plotly_chart(fig_rev, use_container_width=True)

            with col_surp:
                surprises = ed.get("surprise_history", [])
                if surprises:
                    df_surp = pd.DataFrame(surprises)
                    colors = ["green" if v >= 0 else "red" for v in df_surp["surprise_pct"]]
                    fig_surp = go.Figure(go.Bar(
                        x=df_surp["quarter"], y=df_surp["surprise_pct"],
                        marker_color=colors, text=df_surp["surprise_pct"].apply(lambda x: f"{x:+.1f}%"),
                        textposition="outside",
                    ))
                    fig_surp.update_layout(
                        title="EPS 서프라이즈 (%)", height=280,
                        margin=dict(t=40, b=20), yaxis_title="서프라이즈(%)",
                    )
                    st.plotly_chart(fig_surp, use_container_width=True)
                    avg_surp = ed.get("eps_surprise_avg")
                    if avg_surp is not None:
                        st.caption(f"평균 EPS 서프라이즈: **{avg_surp:+.1f}%**")

        # 이번달 주도주 매수 가이드
        st.markdown("#### 💡 이번달 주도주 매수 가이드")
        buy_candidates = [(t, d) for t, d in sorted_stocks if d.get("canslim_score", 0) >= 55]
        stock_budget = sum(MONTHLY_KRW.values()) * 0.5
        st.info(f"이번달 주도주 예산: **{stock_budget:,.0f}원** (월 150만원의 50%)")
        if buy_candidates:
            per_stock = stock_budget / len(buy_candidates)
            for t, d in buy_candidates:
                shares_est = per_stock / exrate / d["current"]
                st.write(f"- **{t}** ({d['signal']}): {per_stock:,.0f}원 → 약 {shares_est:.2f}주 @ ${d['current']}")
        else:
            st.warning("현재 매수 적합 종목 없음. 관심 종목 유지 권장.")


# ──────────────────────────────────────────────────────────
# TAB 3: 내 포트폴리오
# ──────────────────────────────────────────────────────────
with tab3:
    st.markdown("### 💼 내 포트폴리오")

    # ── KIS 자동 동기화 ──────────────────────────────────────
    with st.expander("🔄 한국투자증권 자동 동기화", expanded=False):
        col_sync1, col_sync2, col_sync3 = st.columns([2, 1, 1])
        with col_sync1:
            st.caption("KIS 잔고 자동 조회 → 포트폴리오와 비교. 미등록 종목 일괄 등록 가능.")
        with col_sync2:
            kis_mode = st.selectbox("환경", ["실전투자", "모의투자"], key="kis_mode_sel")
            # 환경 변수 동적 설정
            import os as _os
            _os.environ["KIS_MODE"] = "vts" if kis_mode == "모의투자" else "real"
        with col_sync3:
            st.write("")
            do_sync = st.button("🔄 KIS 잔고 동기화", type="primary")

        if do_sync:
            with st.spinner("KIS API 연결 중..."):
                sync_result = sync_portfolio_from_kis()
                st.session_state["kis_sync"] = sync_result

        if "kis_sync" in st.session_state:
            sr = st.session_state["kis_sync"]
            if sr["error"]:
                st.error(f"동기화 실패: {sr['error']}")
            else:
                st.success(f"동기화 완료 ({sr['synced_at']})")
                holdings = sr["holdings"]
                summary = sr["summary"]

                # 요약 지표
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("보유 종목 수", f"{summary.get('종목수', 0)}개")
                m2.metric("총 매수금", f"${summary.get('총매수금($)', 0):,.2f}")
                m3.metric("총 손익", f"${summary.get('총손익($)', 0):+,.2f}")
                m4.metric("총 평가금(원)", f"₩{summary.get('총평가금액(원)', 0):,.0f}")

                if holdings:
                    import pandas as pd
                    df_hold = pd.DataFrame(holdings)
                    df_hold = df_hold.rename(columns={
                        "ticker": "티커",
                        "name": "종목명",
                        "shares": "수량",
                        "avg_price": "평균단가($)",
                        "current_price": "현재가($)",
                        "pnl_amount": "손익($)",
                        "pnl_pct": "손익(%)",
                        "exchange": "거래소",
                    })
                    display_cols = ["티커", "종목명", "수량", "평균단가($)", "현재가($)", "손익($)", "손익(%)", "거래소"]
                    st.dataframe(df_hold[[c for c in display_cols if c in df_hold.columns]],
                                 use_container_width=True, hide_index=True)

                    # 미등록 종목 자동 등록 버튼
                    existing_tickers = {d["ticker"] for d in load()}
                    new_holdings = [h for h in holdings if h["ticker"] not in existing_tickers]
                    if new_holdings:
                        st.warning(f"포트폴리오에 미등록 종목 {len(new_holdings)}개: {', '.join(h['ticker'] for h in new_holdings)}")
                        if st.button("📥 미등록 종목 일괄 등록 (부부 계좌)"):
                            for h in new_holdings:
                                if h["shares"] > 0 and h["avg_price"] > 0:
                                    add_trade("부부", h["ticker"], h["shares"],
                                              h["avg_price"], datetime.now().strftime("%Y-%m-%d"),
                                              "KIS 자동 동기화")
                            st.success("등록 완료!")
                            st.rerun()

                # 체결 내역 탭
                transactions = sr.get("transactions", [])
                if transactions:
                    st.markdown("##### 최근 체결 내역 (90일)")
                    df_tx = pd.DataFrame(transactions)
                    df_tx = df_tx.rename(columns={
                        "date": "체결일",
                        "ticker": "티커",
                        "name": "종목명",
                        "buy_sell": "구분",
                        "shares": "수량",
                        "price": "단가($)",
                        "amount_usd": "금액($)",
                    })
                    display_tx = ["체결일", "티커", "종목명", "구분", "수량", "단가($)", "금액($)"]
                    st.dataframe(df_tx[[c for c in display_tx if c in df_tx.columns]],
                                 use_container_width=True, hide_index=True)
                else:
                    st.info("최근 90일 체결 내역 없음")

    st.divider()

    # 매수 내역 입력
    with st.expander("➕ 매수 내역 추가"):
        c1, c2, c3, c4, c5, c6 = st.columns(6)
        acc   = c1.selectbox("계좌", ["부부", "자녀"])
        tick  = c2.text_input("티커", placeholder="NVDA").upper()
        shr   = c3.number_input("수량", min_value=0.0, step=0.01, format="%.4f")
        price = c4.number_input("매수가($)", min_value=0.0, step=0.01)
        dt    = c5.date_input("매수일")
        memo  = c6.text_input("메모")
        if st.button("추가", type="primary"):
            if tick and shr > 0 and price > 0:
                add_trade(acc, tick, shr, price, str(dt), memo)
                st.success(f"{acc} | {tick} {shr}주 @ ${price} 추가 완료")
                st.rerun()

    # 계좌 탭
    acc_tab1, acc_tab2, acc_tab3 = st.tabs(["전체", "부부 계좌", "자녀 계좌"])

    def show_portfolio(account=None, tab_label="전체"):
        result = calc_portfolio(account)
        summary = result["summary"]
        by_ticker = result["by_ticker"]
        trades = result["trades"]

        if not trades:
            st.info("매수 내역이 없습니다. 위에서 추가해주세요.")
            return

        # 요약 지표
        pnl_color = "normal" if summary["총손익(%)"] >= 0 else "inverse"
        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("총 매수금", f"${summary['총매수금($)']:,.0f}", f"₩{summary['총매수금(원)']:,.0f}")
        m2.metric("총 평가금", f"${summary['총평가금($)']:,.0f}", f"₩{summary['총평가금(원)']:,.0f}")
        m3.metric("총 손익", f"${summary['총손익($)']:,.0f}",
                  f"{summary['총손익(%)']:+.1f}%",
                  delta_color=pnl_color)
        m4.metric("목표달성률", f"{summary['목표달성률(%)']:.1f}%",
                  f"목표: {GOAL_RETURN_PCT}%")
        m5.metric("환율", f"₩{summary['환율']:,.0f}")

        # 종목별 비중 파이차트 + 테이블
        col_pie, col_tbl = st.columns([1, 2])
        with col_pie:
            if not by_ticker.empty:
                fig = px.pie(by_ticker, names="티커", values="평가금",
                             title="종목별 비중", hole=0.4)
                fig.update_layout(height=300, margin=dict(t=40, b=0))
                st.plotly_chart(fig, use_container_width=True)
        with col_tbl:
            st.dataframe(by_ticker, use_container_width=True, hide_index=True)

        # 매수 내역
        st.markdown("##### 매수 내역")
        df = pd.DataFrame(trades)
        display_cols = ["계좌", "티커", "수량", "매수가($)", "현재가($)", "매수금($)", "평가금($)", "손익($)", "손익(%)", "매수일", "메모"]
        st.dataframe(df[[c for c in display_cols if c in df.columns]],
                     use_container_width=True, hide_index=True)

        # 삭제
        if trades:
            del_id = st.selectbox("삭제할 내역 ID", [t["id"] for t in trades],
                                  format_func=lambda x: next(
                                      f"{t['티커']} {t['수량']}주 ({t['매수일']})"
                                      for t in trades if t["id"] == x
                                  ), key=f"del_{tab_label}")
            if st.button("🗑 삭제", key=f"delbtn_{tab_label}"):
                delete_trade(del_id)
                st.rerun()

    with acc_tab1:
        show_portfolio(None, "전체")
    with acc_tab2:
        show_portfolio("부부", "부부")
    with acc_tab3:
        show_portfolio("자녀", "자녀")


# ──────────────────────────────────────────────────────────
# TAB 4: 목표 관리
# ──────────────────────────────────────────────────────────
with tab4:
    st.markdown("### 🎯 4년 투자 목표 관리")

    start_date = st.date_input("투자 시작일", value=pd.Timestamp("2025-01-01"))
    goal = calc_goal_progress(str(start_date))

    # 진행 현황
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("경과", f"{goal['경과개월']}개월")
    m2.metric("남은 기간", f"{goal['남은일수']}일")
    m3.metric("시간 진행률", f"{goal['진행률(%)']}%")
    m4.metric("목표 수익률", f"{GOAL_RETURN_PCT}%")

    st.progress(goal["진행률(%)"] / 100)

    st.divider()

    # 원금 적립 계획
    st.markdown("#### 💰 월 적립 계획")
    c1, c2, c3 = st.columns(3)
    c1.metric("부부 월 적립", f"₩{MONTHLY_KRW['부부']:,}")
    c2.metric("자녀 월 적립", f"₩{MONTHLY_KRW['자녀']:,}")
    c3.metric("합계 월 적립", f"₩{sum(MONTHLY_KRW.values()):,}")

    col_l, col_r = st.columns(2)
    with col_l:
        st.markdown("#### 📊 누적 원금 계획")
        months = list(range(1, GOAL_YEARS * 12 + 1))
        principals = [sum(MONTHLY_KRW.values()) * m for m in months]
        targets_100 = [p * 2 for p in principals]   # 100% 목표
        targets_60  = [p * 1.6 for p in principals]  # 현실적 60%

        fig2 = go.Figure()
        fig2.add_trace(go.Scatter(x=months, y=principals,   name="원금",        fill="tozeroy", fillcolor="rgba(100,150,250,0.2)"))
        fig2.add_trace(go.Scatter(x=months, y=targets_100,  name="목표(100%)",  line=dict(dash="dash", color="green")))
        fig2.add_trace(go.Scatter(x=months, y=targets_60,   name="현실적(60%)", line=dict(dash="dot",  color="orange")))
        fig2.update_layout(
            yaxis_title="금액 (원)", xaxis_title="경과 개월",
            height=350, hovermode="x unified",
            yaxis=dict(tickformat=","),
        )
        st.plotly_chart(fig2, use_container_width=True)

    with col_r:
        st.markdown("#### 📋 시나리오별 4년 후 예상")
        final_p = goal["최종원금(원)"]
        scenarios = pd.DataFrame([
            {"시나리오": "보수적 (연 8%)",   "4년 후 평가금": f"₩{final_p * 1.36:,.0f}", "수익률": "~36%"},
            {"시나리오": "중립적 (연 12%)",  "4년 후 평가금": f"₩{final_p * 1.57:,.0f}", "수익률": "~57%"},
            {"시나리오": "목표 달성 (연 19%)","4년 후 평가금": f"₩{final_p * 2.00:,.0f}", "수익률": "100%"},
            {"시나리오": "강세장 (연 25%)",  "4년 후 평가금": f"₩{final_p * 2.44:,.0f}", "수익률": "~144%"},
        ])
        st.dataframe(scenarios, use_container_width=True, hide_index=True)

        st.markdown("#### 📌 월별 적립 스케줄")
        st.markdown(f"""
        | 계좌 | 월 적립액 | 48개월 원금 |
        |------|----------|------------|
        | 부부 | ₩{MONTHLY_KRW['부부']:,} | ₩{MONTHLY_KRW['부부']*48:,} |
        | 자녀 | ₩{MONTHLY_KRW['자녀']:,} | ₩{MONTHLY_KRW['자녀']*48:,} |
        | **합계** | **₩{sum(MONTHLY_KRW.values()):,}** | **₩{sum(MONTHLY_KRW.values())*48:,}** |
        """)
