"""
부동산플래닛 실거래가 스크래퍼
- 탱크옥션 상세 페이지의 부동산플래닛 URL (lat/lng 포함)을 이용
- getRealpriceMapMarker API에서 동일 평형대 최근 2년 거래 최대 8건 수집
- 반경 500m 이내 주변 빌라 시세만 수집 (같은 블럭/마을 기준)
"""
import asyncio
import math
from typing import List, Dict, Optional, Tuple
from urllib.parse import urlparse, parse_qs
from playwright.async_api import async_playwright
from datetime import datetime, timedelta


def _haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """두 좌표 간 거리 계산 (미터)"""
    R = 6371000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _parse_latlon_from_url(url: str) -> Tuple[Optional[float], Optional[float]]:
    """URL 쿼리스트링에서 위도/경도 추출"""
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
    """API 응답 아이템에서 위도/경도 추출 (여러 필드명 시도)"""
    lat_keys = ["lat", "latitude", "y_coor", "y", "mapY", "yCoord"]
    lng_keys = ["lng", "longitude", "x_coor", "x", "mapX", "xCoord"]
    try:
        lat = next((float(item[k]) for k in lat_keys if item.get(k)), None)
        lng = next((float(item[k]) for k in lng_keys if item.get(k)), None)
        return lat, lng
    except Exception:
        return None, None


# 탱크옥션 ctgr → 부동산플래닛 r_type_nm 매핑
_CTGR_TO_RTYPE = {
    "다세대": ["다세대주택"],
    "연립":   ["연립주택"],
    "빌라":   ["다세대주택", "연립주택"],
}


async def fetch_planet_trades(
    planet_url: str,
    building_area_m2: float = 0,
    prop_type: str = "",
    max_results: int = 8,
    radius_m: float = 500.0,
) -> List[Dict]:
    """
    부동산플래닛 URL에서 최근 2년 실거래 데이터 수집
    building_area_m2: 기준 공급면적(㎡) - ±25% 범위로 필터
    prop_type: 탱크옥션 ctgr (다세대/연립/빌라) - 동일 건물종류만 필터
    radius_m: 반경 필터 (미터, 기본 500m)
    """
    if not planet_url:
        return []

    trades = []
    cutoff = datetime.now() - timedelta(days=730)  # 2년
    allowed_rtypes = _CTGR_TO_RTYPE.get(prop_type, [])  # 빈 리스트 = 필터 없음

    # URL에서 목표 좌표 추출
    target_lat, target_lng = _parse_latlon_from_url(planet_url)
    has_target = target_lat is not None and target_lng is not None
    coord_filter_applied = False  # API 아이템에 실제로 좌표가 있었는지 추적

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        all_items = []

        async def on_response(response):
            if "getRealpriceMapMarker" in response.url:
                try:
                    body = await response.json()
                    if isinstance(body, list):
                        all_items.extend(body)
                except Exception:
                    pass

        page.on("response", on_response)

        try:
            await page.goto(planet_url, wait_until="networkidle", timeout=30000)
            await asyncio.sleep(8)
        finally:
            page.remove_listener("response", on_response)
            await browser.close()

    # 거리 필터 적용 가능 여부 사전 확인 (첫 아이템으로 판단)
    if has_target and all_items:
        sample_lat, sample_lng = _extract_item_latlon(all_items[0])
        coord_filter_applied = sample_lat is not None and sample_lng is not None

    # 필터링 및 정렬
    for item in all_items:
        # 거래유형: 매매만
        if item.get("t_type") != "1":
            continue

        # 날짜 필터: 최근 2년
        try:
            year = int(item.get("t_year", 0))
            month = int(item.get("t_month", 1))
            trade_date = datetime(year, month, 1)
            if trade_date < cutoff:
                continue
        except Exception:
            pass

        # 건물종류 필터: ctgr이 지정된 경우 동일 종류만
        if allowed_rtypes:
            rtype = str(item.get("r_type_nm", "") or item.get("obj_type_nm", ""))
            if rtype and not any(rt in rtype for rt in allowed_rtypes):
                continue

        # 거리 필터: 반경 이내 (좌표가 있는 경우만 적용)
        dist_m = None
        if has_target and coord_filter_applied:
            item_lat, item_lng = _extract_item_latlon(item)
            if item_lat and item_lng:
                dist_m = _haversine_m(target_lat, target_lng, item_lat, item_lng)
                if dist_m > radius_m:
                    continue

        # 공급면적 필터: ±25% (여러 필드명 시도)
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
        # 면적 값: 여러 필드명 시도
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

        if len(trades) >= max_results * 3:  # 정렬 후 자르기 위해 여유 수집
            break

    # 최신순 정렬 후 상위 max_results
    trades.sort(key=lambda x: x["거래년월"], reverse=True)
    return trades[:max_results]


def fetch_planet_trades_sync(
    planet_url: str,
    building_area_m2: float = 0,
    prop_type: str = "",
    max_results: int = 8,
    radius_m: float = 500.0,
) -> List[Dict]:
    """동기 래퍼"""
    return asyncio.run(fetch_planet_trades(planet_url, building_area_m2, prop_type, max_results, radius_m))
