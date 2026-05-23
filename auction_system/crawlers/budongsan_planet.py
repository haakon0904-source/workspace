"""
부동산플래닛 실거래가 스크래퍼
- 탱크옥션 상세 페이지의 부동산플래닛 URL (lat/lng 포함)을 이용
- getRealpriceMapMarker API에서 동일 평형대 최근 2년 거래 최대 8건 수집
- 반경 500m 이내 주변 빌라 시세만 수집 (같은 블럭/마을 기준)
"""
import math
from typing import List, Dict, Optional, Tuple
from urllib.parse import urlparse, parse_qs
from playwright.sync_api import sync_playwright
from datetime import datetime, timedelta


def _haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _parse_latlon_from_url(url: str) -> Tuple[Optional[float], Optional[float]]:
    try:
        params = parse_qs(urlparse(url).query)
        lat_val = (params.get("lat") or params.get("latitude") or params.get("y") or [None])[0]
        lng_val = (params.get("lng") or params.get("longitude") or params.get("lon") or params.get("x") or [None])[0]
        if lat_val and lng_val:
            return float(lat_val), float(lng_val)
    except Exception:
        pass
    return None, None


def _extract_item_latlon(item: dict) -> Tuple[Optional[float], Optional[float]]:
    lat_keys = ["lat", "latitude", "y_coor", "y", "mapY", "yCoord"]
    lng_keys = ["lng", "longitude", "x_coor", "x", "mapX", "xCoord"]
    try:
        lat = next((float(item[k]) for k in lat_keys if item.get(k)), None)
        lng = next((float(item[k]) for k in lng_keys if item.get(k)), None)
        return lat, lng
    except Exception:
        return None, None


_CTGR_TO_RTYPE = {
    "다세대": ["다세대주택"],
    "연립":   ["연립주택"],
    "빌라":   ["다세대주택", "연립주택"],
}


def fetch_planet_trades(
    planet_url: str,
    building_area_m2: float = 0,
    prop_type: str = "",
    max_results: int = 8,
    radius_m: float = 500.0,
) -> List[Dict]:
    if not planet_url:
        return []

    trades = []
    cutoff = datetime.now() - timedelta(days=730)
    allowed_rtypes = _CTGR_TO_RTYPE.get(prop_type, [])

    target_lat, target_lng = _parse_latlon_from_url(planet_url)
    has_target = target_lat is not None and target_lng is not None
    coord_filter_applied = False

    all_items = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        def on_response(response):
            if "getRealpriceMapMarker" in response.url:
                try:
                    body = response.json()
                    if isinstance(body, list):
                        all_items.extend(body)
                except Exception:
                    pass

        page.on("response", on_response)

        try:
            page.goto(planet_url, wait_until="networkidle", timeout=30000)
            page.wait_for_timeout(8000)
        finally:
            page.remove_listener("response", on_response)
            browser.close()

    if has_target and all_items:
        sample_lat, sample_lng = _extract_item_latlon(all_items[0])
        coord_filter_applied = sample_lat is not None and sample_lng is not None

    for item in all_items:
        if item.get("t_type") != "1":
            continue

        try:
            year = int(item.get("t_year", 0))
            month = int(item.get("t_month", 1))
            trade_date = datetime(year, month, 1)
            if trade_date < cutoff:
                continue
        except Exception:
            pass

        if allowed_rtypes:
            rtype = str(item.get("r_type_nm", "") or item.get("obj_type_nm", ""))
            if rtype and not any(rt in rtype for rt in allowed_rtypes):
                continue

        dist_m = None
        if has_target and coord_filter_applied:
            item_lat, item_lng = _extract_item_latlon(item)
            if item_lat and item_lng:
                dist_m = _haversine_m(target_lat, target_lng, item_lat, item_lng)
                if dist_m > radius_m:
                    continue

        if building_area_m2 > 0:
            try:
                area = 0.0
                for fld in ("supply_area_m2", "bldg_area_m2", "area_m2", "area", "공급면적"):
                    v = item.get(fld)
                    if v:
                        area = float(v)
                        break
                if area > 0 and not (building_area_m2 * 0.75 <= area <= building_area_m2 * 1.25):
                    continue
            except Exception:
                pass

        price_won = item.get("obj_amt", 0)
        price_man = price_won // 10000 if price_won else 0
        bldg_m2 = (item.get("supply_area_m2") or item.get("bldg_area_m2") or 0)
        bldg_py = (item.get("supply_area_py") or item.get("bldg_area_py") or 0)

        row = {
            "거래년월": f"{item.get('t_year', '')}.{str(item.get('t_month', '')).zfill(2)}",
            "건물면적(㎡)": f"{bldg_m2:.1f}" if bldg_m2 else "",
            "건물면적(평)": f"{bldg_py:.1f}" if bldg_py else "",
            "거래금액(만원)": f"{price_man:,}" if price_man else "",
            "동": item.get("dongnm_short", ""),
            "건축년도": item.get("build_year", ""),
            "물건종류": item.get("r_type_nm", ""),
        }
        if dist_m is not None:
            row["거리(m)"] = f"{dist_m:.0f}"

        trades.append(row)

        if len(trades) >= max_results * 3:
            break

    trades.sort(key=lambda x: x["거래년월"], reverse=True)
    return trades[:max_results]


# 하위 호환용 alias
fetch_planet_trades_sync = fetch_planet_trades
