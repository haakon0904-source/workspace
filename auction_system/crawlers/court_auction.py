"""
법원경매정보 크롤러
대상: https://www.courtauction.go.kr
"""
import asyncio
import re
from playwright.async_api import async_playwright, Page
from bs4 import BeautifulSoup
import pandas as pd
from typing import List, Dict, Optional
from dataclasses import dataclass, field, asdict

# 지역 → 법원 매핑 (법원 선택 방식)
REGION_TO_COURT = {
    "인천": "인천지방법원",
    "안산": "안산지원",
    "고양": "고양지원",
}

# 경기도 광주는 지역 선택 방식으로 처리 (수원지방법원 관할이나 별도 지원 없음)
REGION_TO_SIDO = {
    "경기도 광주": ("경기도", "광주시"),
}

# 물건종류 소분류
PROPERTY_SUBTYPES = {
    "다세대": "다세대주택",
    "연립": "연립주택",
    "빌라": "빌라",
}

SEARCH_URL = "https://www.courtauction.go.kr/pgj/index.on?w2xPath=/pgj/ui/pgj100/PGJ151F00.xml"


@dataclass
class AuctionItem:
    case_number: str = ""        # 사건번호
    item_number: str = ""        # 물건번호
    court: str = ""              # 법원
    region: str = ""             # 검색지역
    address: str = ""            # 소재지
    property_type: str = ""      # 물건종류 (다세대/연립/빌라)
    appraised_value: float = 0   # 감정평가액
    min_bid_price: float = 0     # 최저매각가격
    deposit: float = 0           # 매수신청보증금
    auction_date: str = ""       # 매각기일
    auction_dept: str = ""       # 담당계
    status: str = ""             # 진행상태 (유찰 N회)
    failed_count: int = 0        # 유찰 횟수
    area_m2: float = 0           # 전용면적 (㎡)
    note: str = ""               # 물건비고
    bid_ratio: float = 0         # 최저가율 (최저가/감정가 %)

    def to_dict(self) -> Dict:
        return asdict(self)


class CourtAuctionCrawler:
    def __init__(self):
        self.results: List[AuctionItem] = []

    async def search(
        self,
        regions: List[str],
        max_appraised_value: float = 200_000_000,
        property_subtypes: List[str] = ["다세대", "연립", "빌라"],
    ) -> List[Dict]:
        self.results = []

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()

            for region in regions:
                for subtype in property_subtypes:
                    items = await self._search_one(context, region, subtype, max_appraised_value)
                    self.results.extend(items)
                    await asyncio.sleep(1)

            await browser.close()

        return [item.to_dict() for item in self.results]

    async def _search_one(
        self,
        context,
        region: str,
        subtype: str,
        max_appraised_value: float,
    ) -> List[AuctionItem]:
        """지역 + 물건종류 조합으로 검색"""
        page = await context.new_page()
        items = []

        try:
            await page.goto(SEARCH_URL, wait_until="networkidle", timeout=30000)
            await asyncio.sleep(5)  # w2x UI 프레임워크 초기화 대기

            # 검색 조건 설정
            await self._set_search_conditions(page, region, subtype, max_appraised_value)

            # 검색 실행
            await page.click("#mf_wfm_mainFrame_btn_gdsDtlSrch")
            await page.wait_for_load_state("networkidle", timeout=30000)
            await asyncio.sleep(2)

            # 전체 건수 확인
            total_count = await self._get_total_count(page)
            print(f"[{region}] {subtype}: {total_count}건 검색")

            if total_count == 0:
                await page.close()
                return []

            # 페이지별 수집
            court_name = REGION_TO_COURT.get(region, region)
            first_page_items = self._parse_list_page(await page.content(), court_name, region, subtype)
            items.extend(first_page_items)

            # 페이지네이션
            total_pages = self._calc_pages(total_count, len(first_page_items) or 10)
            for page_num in range(2, min(total_pages + 1, 20)):
                try:
                    page_btn = page.locator(f"#mf_wfm_mainFrame_pgl_gdsDtlSrchPage_page_{page_num}")
                    if await page_btn.count() > 0:
                        await page_btn.click()
                        await page.wait_for_load_state("networkidle", timeout=20000)
                        await asyncio.sleep(1)
                        page_items = self._parse_list_page(await page.content(), court_name, region, subtype)
                        items.extend(page_items)
                    else:
                        break
                except Exception as e:
                    print(f"[WARN] 페이지 {page_num} 이동 실패: {e}")
                    break

        except Exception as e:
            print(f"[ERROR] [{region}] {subtype} 검색 실패: {e}")
        finally:
            await page.close()

        return items

    async def _select(self, page: Page, selector: str, value: str, wait: float = 0.5):
        """JS로 직접 select 값 설정 후 change 이벤트 발생"""
        await page.evaluate(
            """([sel, val]) => {
                const el = document.querySelector(sel);
                if (!el) throw new Error('Not found: ' + sel);
                el.value = val;
                el.dispatchEvent(new Event('change', {bubbles: true}));
            }""",
            [selector, value],
        )
        await asyncio.sleep(wait)

    async def _set_search_conditions(self, page: Page, region: str, subtype: str, max_value: float):
        """검색 조건 입력"""
        # 법원 or 지역 선택
        if region in REGION_TO_COURT:
            court = REGION_TO_COURT[region]
            await self._select(page, "#mf_wfm_mainFrame_sbx_rletCortOfc", court)
        elif region in REGION_TO_SIDO:
            sido, sigungu = REGION_TO_SIDO[region]
            await self._select(page, "#mf_wfm_mainFrame_sbx_rletAdongSdS", sido, wait=1.0)
            try:
                await page.wait_for_function(
                    "document.querySelector('#mf_wfm_mainFrame_sbx_rletAdongSggS').options.length > 1",
                    timeout=5000,
                )
                await self._select(page, "#mf_wfm_mainFrame_sbx_rletAdongSggS", sigungu)
            except Exception:
                pass

        # 물건종류: 건물 → 주거용건물 → 소분류
        await self._select(page, "#mf_wfm_mainFrame_sbx_rletLclLst", "건물")
        await self._select(page, "#mf_wfm_mainFrame_sbx_rletMclLst", "주거용건물")
        scl_value = PROPERTY_SUBTYPES.get(subtype, subtype)
        await self._select(page, "#mf_wfm_mainFrame_sbx_rletSclLst", scl_value)

        # 감정가 상한
        max_label = self._value_to_price_label(max_value)
        if max_label:
            await self._select(page, "#mf_wfm_mainFrame_sbx_rletAeePyngEqvalMax", max_label, wait=0.3)

    def _value_to_price_label(self, value: float) -> Optional[str]:
        """금액 → 드롭다운 텍스트 변환"""
        mapping = {
            10_000_000: "1천만원",
            50_000_000: "5천만원",
            100_000_000: "1억원",
            150_000_000: "1억5천만원",
            200_000_000: "2억원",
            250_000_000: "2억5천만원",
            300_000_000: "3억원",
        }
        # 가장 가까운 상한 찾기
        for threshold, label in sorted(mapping.items()):
            if value <= threshold:
                return label
        return "2억원"

    async def _get_total_count(self, page: Page) -> int:
        """검색 결과 총 건수"""
        try:
            content = await page.content()
            soup = BeautifulSoup(content, "lxml")
            tables = soup.find_all("table")
            if tables:
                header_text = tables[0].get_text()
                match = re.search(r"총\s*물건수(\d+)건", header_text.replace(" ", ""))
                if match:
                    return int(match.group(1))
        except Exception:
            pass
        return 0

    def _calc_pages(self, total: int, per_page: int) -> int:
        if per_page == 0:
            return 1
        return (total + per_page - 1) // per_page

    def _parse_list_page(self, html: str, court: str, region: str, subtype: str) -> List[AuctionItem]:
        """목록 페이지 파싱 (2행 = 1물건)"""
        soup = BeautifulSoup(html, "lxml")
        tables = soup.find_all("table")
        if len(tables) < 2:
            return []

        result_table = tables[1]
        rows = result_table.find_all("tr")
        items = []

        # rows[0]: 헤더, rows[1]: 서브헤더, rows[2+]: 데이터 (2행씩)
        i = 2
        while i < len(rows) - 1:
            row_main = rows[i]
            row_sub = rows[i + 1] if i + 1 < len(rows) else None

            item = self._parse_row_pair(row_main, row_sub, court, region, subtype)
            if item and item.case_number:
                items.append(item)
            i += 2

        return items

    def _parse_row_pair(self, row_main, row_sub, court: str, region: str, subtype: str) -> Optional[AuctionItem]:
        """2개 행에서 물건 1개 파싱"""
        try:
            cols_main = row_main.find_all("td")
            if len(cols_main) < 6:
                return None

            item = AuctionItem()
            item.court = court
            item.region = region
            item.property_type = subtype

            # 메인 행: [사건번호, 사건번호, 물건번호, 주소+면적, 지도, 비고, 감정가, 담당계+기일]
            item.case_number = cols_main[0].get_text(strip=True)
            item.item_number = cols_main[2].get_text(strip=True)

            # 주소 + 면적 파싱
            addr_cell = cols_main[3]
            addr_text = addr_cell.get_text(strip=True)
            item.address = addr_text

            # 면적 추출 (예: [집합건물 철근콘크리트구조 60.24㎡])
            area_match = re.search(r"(\d+\.?\d*)\s*㎡", addr_text)
            if area_match:
                item.area_m2 = float(area_match.group(1))

            # 감정가
            item.appraised_value = self._parse_price(cols_main[-2].get_text(strip=True))

            # 담당계 + 기일
            last_col = cols_main[-1].get_text(strip=True)
            # 예: "경매15계2026.03.30"
            date_match = re.search(r"(\d{4}\.\d{2}\.\d{2})", last_col)
            if date_match:
                item.auction_date = date_match.group(1)
            dept_match = re.search(r"(경매\d+[-\d]*계[^\d]*)", last_col)
            if dept_match:
                item.auction_dept = dept_match.group(1).strip()

            # 서브 행: [물건종류, 최저매각가격(율%), 진행상태]
            if row_sub:
                cols_sub = row_sub.find_all("td")
                if len(cols_sub) >= 2:
                    min_price_text = cols_sub[1].get_text(strip=True)
                    # 예: "117,600,000(70%)" or "29,498,000(34%)"
                    price_match = re.search(r"([\d,]+)", min_price_text.replace(" ", ""))
                    if price_match:
                        item.min_bid_price = float(price_match.group(1).replace(",", ""))

                    # 보증금 = 최저가의 10%
                    item.deposit = item.min_bid_price * 0.1

                if len(cols_sub) >= 3:
                    status_text = cols_sub[2].get_text(strip=True)
                    item.status = status_text
                    fail_match = re.search(r"유찰\s*(\d+)회", status_text)
                    if fail_match:
                        item.failed_count = int(fail_match.group(1))

            # 낙찰가율 계산
            if item.appraised_value > 0:
                item.bid_ratio = round(item.min_bid_price / item.appraised_value * 100, 1)

            return item

        except Exception as e:
            print(f"[WARN] 행 파싱 오류: {e}")
            return None

    def _parse_price(self, text: str) -> float:
        """가격 문자열 → float (원 단위)"""
        text = text.replace(",", "").replace(" ", "").replace("원", "")
        if not text:
            return 0.0
        try:
            return float(text)
        except ValueError:
            return 0.0

    def to_dataframe(self) -> pd.DataFrame:
        if not self.results:
            return pd.DataFrame()
        return pd.DataFrame([item.to_dict() for item in self.results])


def search_properties(
    regions: List[str],
    max_appraised_value: float = 200_000_000,
    property_subtypes: List[str] = ["다세대", "연립", "빌라"],
) -> List[Dict]:
    """동기 래퍼 (Streamlit에서 호출)"""
    return asyncio.run(
        CourtAuctionCrawler().search(regions, max_appraised_value, property_subtypes)
    )
