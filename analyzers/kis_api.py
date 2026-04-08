"""
한국투자증권 (KIS) OpenAPI 연동 모듈
- OAuth 액세스 토큰 발급
- 해외주식 잔고 조회
- 해외주식 체결 내역 조회
"""
import os
import json
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

KIS_REAL_URL  = "https://openapi.koreainvestment.com:9443"
KIS_VIRT_URL  = "https://openapivts.koreainvestment.com:29443"
_DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")


def _token_cache_path() -> str:
    mode = os.getenv("KIS_MODE", "real").lower()
    fname = "kis_token_vts.json" if mode == "vts" else "kis_token.json"
    return os.path.join(_DATA_DIR, fname)


def _base_url() -> str:
    """환경 변수 KIS_MODE=vts 이면 모의투자, 아니면 실전"""
    mode = os.getenv("KIS_MODE", "real").lower()
    return KIS_VIRT_URL if mode == "vts" else KIS_REAL_URL


def _tr_prefix() -> str:
    """모의투자 TR ID 접두어"""
    mode = os.getenv("KIS_MODE", "real").lower()
    return "V" if mode == "vts" else ""


def _load_cached_token() -> Optional[Dict]:
    """캐시된 토큰 로드 (유효한 경우만)"""
    try:
        with open(_token_cache_path(), "r") as f:
            data = json.load(f)
        expires_at = datetime.fromisoformat(data["expires_at"])
        if datetime.now() < expires_at - timedelta(minutes=10):
            return data
    except Exception:
        pass
    return None


def _save_token(token_data: Dict):
    os.makedirs(_DATA_DIR, exist_ok=True)
    with open(_token_cache_path(), "w") as f:
        json.dump(token_data, f)


def get_access_token() -> str:
    """OAuth 액세스 토큰 발급 (캐시 우선)"""
    cached = _load_cached_token()
    if cached:
        return cached["access_token"]

    app_key = os.getenv("KIS_APP_KEY", "")
    app_secret = os.getenv("KIS_APP_SECRET", "")

    if not app_key or not app_secret:
        raise ValueError("KIS_APP_KEY / KIS_APP_SECRET 환경 변수가 없습니다.")

    resp = requests.post(
        f"{_base_url()}/oauth2/tokenP",
        headers={"content-type": "application/json"},
        json={
            "grant_type": "client_credentials",
            "appkey": app_key,
            "appsecret": app_secret,
        },
        timeout=10,
    )
    resp.raise_for_status()
    result = resp.json()

    if "access_token" not in result:
        raise RuntimeError(f"토큰 발급 실패: {result}")

    expires_at = datetime.now() + timedelta(seconds=int(result.get("expires_in", 86400)))
    token_data = {
        "access_token": result["access_token"],
        "expires_at": expires_at.isoformat(),
    }
    _save_token(token_data)
    return result["access_token"]


def _headers(token: str, tr_id: str) -> Dict:
    # 모의투자 TR은 앞에 'V' 붙음 (예: JTTT3012R → VTTT3012R)
    prefix = _tr_prefix()
    actual_tr = prefix + tr_id if prefix and not tr_id.startswith("V") else tr_id
    return {
        "content-type": "application/json",
        "authorization": f"Bearer {token}",
        "appkey": os.getenv("KIS_APP_KEY", ""),
        "appsecret": os.getenv("KIS_APP_SECRET", ""),
        "tr_id": actual_tr,
    }


def get_overseas_balance() -> Tuple[List[Dict], Dict]:
    """
    해외주식 잔고 조회 (TR: JTTT3012R)
    반환: (holdings_list, summary_dict)
    """
    token = get_access_token()
    account_no = os.getenv("KIS_ACCOUNT_NO", "")
    account_sfx = os.getenv("KIS_ACCOUNT_SUFFIX", "01")

    # 거래소별로 조회 후 합산 (NASD, NYSE, AMEX, NYAM)
    all_holdings = []
    exchanges = ["NASD", "NYSE", "AMEX"]

    for excg in exchanges:
        try:
            resp = requests.get(
                f"{_base_url()}/uapi/overseas-stock/v1/trading/inquire-balance",
                headers=_headers(token, "JTTT3012R"),
                params={
                    "CANO": account_no,
                    "ACNT_PRDT_CD": account_sfx,
                    "OVRS_EXCG_CD": excg,
                    "TR_CRCY_CD": "USD",
                    "CTX_AREA_FK200": "",
                    "CTX_AREA_NK200": "",
                },
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()
            output = data.get("output1", []) or []

            for item in output:
                shares = float(item.get("cblc_qty13", 0) or 0)
                if shares <= 0:
                    continue
                ticker = item.get("pdno", "").strip()
                # 중복 방지
                if any(h["ticker"] == ticker for h in all_holdings):
                    continue
                all_holdings.append({
                    "ticker": ticker,
                    "name": item.get("prdt_name", "").strip(),
                    "shares": shares,
                    "avg_price": float(item.get("pchs_avg_pric", 0) or 0),
                    "current_price": float(item.get("now_pric2", 0) or 0),
                    "eval_amount_krw": float(item.get("evlu_amt_krw", 0) or 0),
                    "pnl_amount": float(item.get("evlu_pfls_amt", 0) or 0),
                    "pnl_pct": float(item.get("evlu_pfls_rt", 0) or 0),
                    "currency": "USD",
                    "exchange": excg,
                })
        except Exception:
            continue

    # 전체 합산 요약
    total_eval = sum(h["eval_amount_krw"] for h in all_holdings)
    total_cost = sum(h["shares"] * h["avg_price"] for h in all_holdings)
    total_pnl = sum(h["pnl_amount"] for h in all_holdings)

    summary = {
        "총평가금액(원)": total_eval,
        "총매수금액($)": round(total_cost, 2),
        "총손익($)": round(total_pnl, 2),
        "종목수": len(all_holdings),
    }

    return all_holdings, summary


def get_overseas_transactions(start_date: str = None, end_date: str = None) -> List[Dict]:
    """
    해외주식 체결 내역 조회 (TR: JTTT3001R, 최근 3개월 이내)
    start_date / end_date: "YYYYMMDD"
    반환: [{date, ticker, name, buy_sell, shares, price, amount_usd, currency}]
    """
    token = get_access_token()
    account_no = os.getenv("KIS_ACCOUNT_NO", "")
    account_sfx = os.getenv("KIS_ACCOUNT_SUFFIX", "01")

    if not end_date:
        end_date = datetime.now().strftime("%Y%m%d")
    if not start_date:
        start_date = (datetime.now() - timedelta(days=90)).strftime("%Y%m%d")

    resp = requests.get(
        f"{_base_url()}/uapi/overseas-stock/v1/trading/inquire-ccnl",
        headers=_headers(token, "JTTT3001R"),
        params={
            "CANO": account_no,
            "ACNT_PRDT_CD": account_sfx,
            "PDNO": "",
            "ORD_STRT_DT": start_date,
            "ORD_END_DT": end_date,
            "SLL_BUY_DVSN": "00",   # 00=전체, 01=매도, 02=매수
            "OVRS_EXCG_CD": "",
            "CTX_AREA_FK200": "",
            "CTX_AREA_NK200": "",
        },
        timeout=10,
    )
    resp.raise_for_status()
    data = resp.json()

    output = data.get("output1", []) or []
    result = []
    for item in output:
        qty = float(item.get("ft_ccld_qty", 0) or 0)
        if qty <= 0:
            continue
        result.append({
            "date": item.get("ord_dt", ""),
            "ticker": item.get("pdno", "").strip(),
            "name": item.get("prdt_name", "").strip(),
            "buy_sell": "매수" if item.get("sll_buy_dvsn_cd") == "02" else "매도",
            "shares": qty,
            "price": float(item.get("ft_ccld_unpr3", 0) or 0),
            "amount_usd": float(item.get("ft_ccld_amt3", 0) or 0),
            "currency": item.get("tr_crcy_cd", "USD"),
            "exchange": item.get("ovrs_excg_cd", ""),
        })

    return result


def sync_portfolio_from_kis() -> Dict:
    """
    KIS 잔고 → 포트폴리오 형식 변환
    반환: {holdings, summary, transactions, error, synced_at}
    """
    try:
        holdings, summary = get_overseas_balance()
        transactions = get_overseas_transactions()
        return {
            "holdings": holdings,
            "summary": summary,
            "transactions": transactions,
            "error": None,
            "synced_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
    except Exception as e:
        return {
            "holdings": [],
            "summary": {},
            "transactions": [],
            "error": str(e),
            "synced_at": None,
        }
