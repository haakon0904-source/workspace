"""
탱크옥션 크롤러
- 매물 목록: AJAX POST API
- 상세 (권리분석): HTML 파싱
- 실거래가: molitTradePrice.php API
"""
import asyncio
import re
from playwright.async_api import async_playwright, Page, Browser
from bs4 import BeautifulSoup
import json
from typing import List, Dict, Optional
from dataclasses import dataclass, field, asdict
from dotenv import load_dotenv
import os

load_dotenv()

TANKAUCTION_ID = os.getenv("TANKAUCTION_ID", "")
TANKAUCTION_PW = os.getenv("TANKAUCTION_PW", "")
BASE_URL = "https://www.tankauction.com"

# 지역 → (siCd, guCd) 매핑
REGION_CODES = {
    "인천":       ("28", "0"),
    "안산":       ("41", "270"),
    "고양":       ("41", "280"),
    "경기도 광주": ("41", "610"),
}

# 물건종류 코드
PROPERTY_CODES = {
    "다세대": "201014",
    "연립": "201013",
    "빌라": "201015,201017,201021",
}

# API ctgr 값 → 사용자 선택 이름 매핑
CTGR_NORMALIZE = {
    "다세대주택": "다세대",
    "연립주택": "연립",
    "빌라": "빌라",
}

# 사용자 선택 이름 → 허용 ctgr 값 목록
PROP_TYPE_CTGRS = {
    "다세대": ["다세대주택", "다세대"],
    "연립": ["연립주택", "연립"],
    "빌라": ["빌라", "다세대주택"],
}


@dataclass
class TenantInfo:
    """임차인 정보"""
    occupant: str = ""          # 임차인
    occupy_part: str = ""       # 점유부분
    move_in_date: str = ""      # 전입일
    confirmed_date: str = ""    # 확정일자
    deposit: str = ""           # 보증금
    resist_power: str = ""      # 대항력
    analysis: str = ""          # 분석
    note: str = ""              # 기타


@dataclass
class RegistryItem:
    """등기 항목"""
    order: str = ""             # 순서
    reg_date: str = ""          # 접수일
    right_type: str = ""        # 권리종류
    holder: str = ""            # 권리자
    amount: str = ""            # 채권금액
    note: str = ""              # 비고
    is_base: bool = False        # 말소기준등기 여부
    is_deleted: bool = False     # 소멸 여부


@dataclass
class AuctionDetail:
    """경매 물건 상세"""
    tid: int = 0
    sa_no: str = ""             # 사건번호
    court_dept: str = ""        # 담당법원/계
    address: str = ""           # 소재지
    category: str = ""          # 물건종류
    appraised_value: int = 0    # 감정가
    min_bid: int = 0            # 최저매각가격
    min_bid_pct: int = 0        # 최저가율(%)
    status: str = ""            # 진행상태
    bid_date: str = ""          # 매각기일
    area_info: str = ""         # 면적정보
    special: str = ""           # 특수조건

    # 권리분석
    cancel_base_date: str = ""  # 말소기준일
    demand_deadline: str = ""   # 배당요구종기일
    tenants: List[TenantInfo] = field(default_factory=list)
    tenant_note: str = ""       # 임차인 기타사항
    registry: List[RegistryItem] = field(default_factory=list)
    registry_total: str = ""    # 채권합계
    hug_waived: bool = False    # 허그 인수조건 포기 여부
    resist_waived: bool = False # 대항력 포기 여부

    # 주변환경 (거리)
    subway: str = ""            # 가장 가까운 지하철역
    convenience_store: str = "" # 가장 가까운 편의점
    elementary_school: str = "" # 가장 가까운 초등학교

    # 건물 정보
    building_year: str = ""     # 건물 연식 (매물명세서)
    has_elevator: str = ""      # 엘리베이터 유무 (감정평가서)
    room_count: int = 0         # 방 개수 (Vision AI)
    bathroom_count: int = 0     # 화장실 개수 (Vision AI)
    bldg_ar: float = 0.0        # 건물면적(㎡) - 상세 페이지에서 파싱
    lnd_ar: float = 0.0         # 대지면적(㎡) - 상세 페이지에서 파싱

    # 문서 링크
    floor_plan_img_url: str = ""   # 내부구조도 이미지 URL
    appraisal_idx: str = ""        # 감정평가서 idx
    statement_idx: str = ""        # 매물명세서 idx
    planet_url: str = ""           # 부동산플래닛 URL

    # 실거래가
    trade_prices: List[Dict] = field(default_factory=list)

    def to_dict(self) -> Dict:
        d = asdict(self)
        return d


class TankAuctionCrawler:
    def __init__(self):
        self._browser: Optional[Browser] = None
        self._page: Optional[Page] = None
        self._playwright = None

    async def __aenter__(self):
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(headless=True)
        self._page = await self._browser.new_page()
        await self._login()
        return self

    async def __aexit__(self, *args):
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()

    async def _login(self):
        """로그인"""
        await self._page.goto(f"{BASE_URL}/", wait_until="networkidle", timeout=30000)
        await asyncio.sleep(2)
        await self._page.click("text=로그인")
        await asyncio.sleep(1)
        await self._page.fill("#client_id", TANKAUCTION_ID)
        await self._page.fill("#passwd", TANKAUCTION_PW)
        await self._page.keyboard.press("Enter")
        await self._page.wait_for_load_state("networkidle", timeout=15000)
        await asyncio.sleep(2)
        print("[탱크옥션] 로그인 완료")

    async def search(
        self,
        regions: List[str],
        max_appraised_value: int = 200_000_000,
        property_types: List[str] = ["다세대", "연립", "빌라"],
        max_pages: int = 5,
    ) -> List[Dict]:
        """매물 목록 검색"""
        all_items = []

        await self._page.goto(
            f"{BASE_URL}/ca/caList.php", wait_until="networkidle", timeout=30000
        )
        await asyncio.sleep(2)

        for region in regions:
            items = await self._search_region(
                region, max_appraised_value, property_types, max_pages
            )
            all_items.extend(items)

        return all_items

    async def _search_region(
        self,
        region: str,
        max_value: int,
        property_types: List[str],
        max_pages: int,
    ) -> List[Dict]:
        """지역별 검색"""
        items = []
        sicd, gucd = REGION_CODES.get(region, ("0", "0"))

        # 카테고리 코드 조합
        codes = []
        for pt in property_types:
            codes.extend(PROPERTY_CODES.get(pt, "").split(","))
        ctgr_cd = "|".join(c.strip() for c in codes if c.strip())

        max_wan = max_value // 10_000  # 만원 단위

        api_results = {}

        async def on_response(response):
            if "AuctList.php" in response.url:
                try:
                    body = await response.json()
                    api_results["data"] = body
                except Exception:
                    pass

        self._page.on("response", on_response)

        try:
            for page_no in range(1, max_pages + 1):
                api_results.clear()

                # siCd 변경 시 guCd 옵션이 동적으로 로드되므로 순서대로 설정
                await self._page.evaluate(f"""
                    async () => {{
                        const siSel = document.querySelector("select[name=siCd]");
                        siSel.value = "{sicd}";
                        siSel.dispatchEvent(new Event("change", {{bubbles: true}}));
                    }}
                """)
                await asyncio.sleep(1)  # guCd 옵션 로드 대기

                # 체크박스 ID 목록 (콤마 → 언더스코어)
                cb_ids = [
                    "chkEaCtgr_" + PROPERTY_CODES[pt].replace(",", "_")
                    for pt in property_types if pt in PROPERTY_CODES
                ]
                cb_ids_js = json.dumps(cb_ids)

                await self._page.evaluate(f"""
                    () => {{
                        const guSel = document.querySelector("select[name=guCd]");
                        if (guSel) guSel.value = "{gucd}";

                        // 모든 카테고리 체크박스 해제
                        document.querySelectorAll('input[name=chkEaCtgr]').forEach(cb => {{
                            if (cb.checked) cb.click();
                        }});
                        // 원하는 카테고리만 체크
                        {cb_ids_js}.forEach(id => {{
                            const cb = document.getElementById(id);
                            if (cb && !cb.checked) cb.click();
                        }});

                        const maxInput = document.querySelector("input[name=apslAmtMax]");
                        if (maxInput) maxInput.value = "{max_wan}";

                        srchList({page_no});
                    }}
                """)
                await asyncio.sleep(3)

                data = api_results.get("data", {})
                page_items = data.get("item", [])
                total = data.get("totalCnt", 0)

                if not page_items:
                    break

                # post-filter: 물건종류 + 감정가 상한
                allowed_ctgrs = set()
                for pt in property_types:
                    allowed_ctgrs.update(PROP_TYPE_CTGRS.get(pt, [pt]))

                # 첫 아이템 API 필드 디버그 (1회)
                if page_no == 1 and page_items and not items:
                    print(f"[DEBUG] API 필드: {list(page_items[0].keys())}")

                for item in page_items:
                    if item.get("ctgr", "") not in allowed_ctgrs:
                        continue
                    if item.get("apslAmt", 0) > max_value:
                        continue
                    item["search_region"] = region
                    item["ctgr"] = CTGR_NORMALIZE.get(item["ctgr"], item["ctgr"])
                    item["floor_info"] = self._extract_floor_info(item)
                    item["list_build_year"] = self._extract_build_year(item)
                    item["list_elevator"] = self._estimate_elevator(item)
                    item["list_room_info"] = self._extract_room_info(item)
                    items.append(item)

                print(f"[{region}] 페이지 {page_no}: {len(page_items)}건 중 {sum(1 for i in page_items if i.get('ctgr','') in allowed_ctgrs)}건 필터 (전체 {total}건)")

                if page_no * 20 >= total:
                    break

        finally:
            self._page.remove_listener("response", on_response)

        return items

    def _extract_build_year(self, item: dict) -> str:
        """건물 연식 추출: API 필드 우선, 없으면 주소/비고에서 파싱"""
        # 탱크옥션 API 가능한 필드명들
        for key in ("bldgYear", "bldYear", "bldgYr", "useAprYear", "buildYear",
                    "constYear", "bldgCmpltYear", "aprvYear"):
            v = str(item.get(key) or "").strip()
            if v and v not in ("0", "None", ""):
                return v[:4]  # 연도 4자리만

        # 주소·비고 텍스트에서 "XXXX년" 패턴 (1970~2025 범위)
        text = str(item.get("regnAdrs", "")) + " " + str(item.get("note", ""))
        m = re.search(r"(19[7-9]\d|20[0-2]\d)년", text)
        if m:
            return m.group(1)
        return ""

    def _estimate_elevator(self, item: dict) -> str:
        """엘베 유무 추정: API 필드 우선, 없으면 총층수 기반 추정"""
        # API 직접 필드
        for key in ("elvtrYn", "elevatorYn", "elev", "elevator", "elvYn"):
            v = str(item.get(key) or "").strip()
            if v and v not in ("None", ""):
                if v in ("Y", "1", "있음", "true"):
                    return "있음"
                if v in ("N", "0", "없음", "false"):
                    return "없음"

        # 총층수 기반 추정 (5층 이상이면 있음 추정)
        tot = str(item.get("totFlrCnt") or item.get("totFlr") or
                  item.get("bldgFlrCnt") or item.get("totFloor") or "").strip()
        if tot and tot not in ("0", "None", ""):
            try:
                return "있음(추정)" if int(tot) >= 5 else "없음(추정)"
            except ValueError:
                pass

        # 주소에서 총층수 파싱 시도
        addr = item.get("regnAdrs", "")
        m = re.search(r"(\d+)층\s*중", addr)
        if m:
            try:
                return "있음(추정)" if int(m.group(1)) >= 5 else "없음(추정)"
            except ValueError:
                pass
        return ""

    def _extract_floor_info(self, item: dict) -> str:
        """층 정보 추출: API 필드 우선, 없으면 주소에서 파싱"""
        # 탱크옥션 API 가능한 필드명들
        fl = str(item.get("flrNo") or item.get("floor") or item.get("flr") or "").strip()
        tot = str(item.get("totFlrCnt") or item.get("totFlr") or item.get("bldgFlrCnt") or item.get("totFloor") or "").strip()

        if fl and fl not in ("0", "None", ""):
            return f"{fl}층/{tot}층" if (tot and tot not in ("0", "None", "")) else f"{fl}층"

        # 주소에서 파싱: "제N층", "(N층)", "N층 N호"
        addr = item.get("regnAdrs", "")
        m = re.search(r"제?(\d+)층", addr)
        if m:
            return f"{m.group(1)}층"
        return ""

    def _extract_room_info(self, item: dict) -> str:
        """방/화장실 개수 추출: API 필드 우선, 없으면 주소·비고 텍스트 파싱"""
        # API 직접 필드
        room = 0
        bath = 0
        for key in ("roomCnt", "room_count", "bdrmCnt", "roomNo", "방수", "방개수"):
            v = item.get(key)
            if v and str(v) not in ("0", "None", ""):
                try:
                    room = int(v)
                    break
                except (ValueError, TypeError):
                    pass
        for key in ("bathCnt", "bath_count", "wcroomCnt", "bathNo", "욕실수", "화장실수"):
            v = item.get(key)
            if v and str(v) not in ("0", "None", ""):
                try:
                    bath = int(v)
                    break
                except (ValueError, TypeError):
                    pass

        # 주소·비고 텍스트에서 파싱
        # 예) "방3/욕1", "방 3개 욕실 1개", "3룸", "방3개"
        if room == 0:
            text = str(item.get("regnAdrs", "")) + " " + str(item.get("note", ""))
            m = re.search(r"방\s*(\d+)\s*(?:개|실)?", text)
            if m:
                room = int(m.group(1))
            else:
                m = re.search(r"(\d+)\s*(?:룸|room)", text, re.IGNORECASE)
                if m:
                    room = int(m.group(1))
        if bath == 0:
            text = str(item.get("regnAdrs", "")) + " " + str(item.get("note", ""))
            m = re.search(r"(?:욕실|욕|화장실|bath)\s*(\d+)\s*(?:개|실)?", text, re.IGNORECASE)
            if m:
                bath = int(m.group(1))

        if room or bath:
            r = f"{room}방" if room else "-"
            b = f"{bath}욕" if bath else "-"
            return f"{r}/{b}"
        return ""

    async def get_detail(self, tid: int) -> AuctionDetail:
        """물건 상세 정보 (권리분석 포함)"""
        detail = AuctionDetail(tid=tid)

        # 실거래가 API 캡처
        trade_data = {}
        async def on_response(response):
            if "molitTradePrice.php" in response.url and "Form" not in response.url:
                try:
                    body = await response.json()
                    trade_data["items"] = body.get("item", [])
                except Exception:
                    pass

        self._page.on("response", on_response)

        try:
            await self._page.goto(
                f"{BASE_URL}/ca/caView.php?tid={tid}",
                wait_until="networkidle",
                timeout=30000,
            )
            await asyncio.sleep(6)

            content = await self._page.content()
            soup = BeautifulSoup(content, "lxml")

            self._parse_basic_info(soup, detail)
            self._parse_tenant_info(soup, detail)
            self._parse_registry_info(soup, detail)
            self._parse_env_info(soup, detail)
            self._extract_document_links(soup, detail)
            self._parse_building_year_from_page(soup, detail)
            detail.trade_prices = trade_data.get("items", [])

            # 감정평가서 PDF 파싱 (건물연식 재확인 + 엘베 + 층수)
            if detail.appraisal_idx:
                cookies = await self._page.context.cookies()
                cookie_dict = {c["name"]: c["value"] for c in cookies}
                await self._parse_appraisal_pdf(tid, detail.appraisal_idx, detail, cookie_dict)

            # 방/화장실 미확인 시 내부구조도 이미지(tp=B)로 Vision AI 보완
            if detail.floor_plan_img_url and detail.room_count == 0:
                import os as _os
                if _os.getenv("ANTHROPIC_API_KEY", ""):
                    await self._analyze_floor_plan_image(detail)

        finally:
            self._page.remove_listener("response", on_response)

        return detail

    def _parse_basic_info(self, soup: BeautifulSoup, detail: AuctionDetail):
        """기본 물건 정보 파싱 (건물면적/대지면적)"""
        try:
            obj_div = soup.find(id="lyCnt_object")
            if not obj_div:
                return
            obj_text = obj_div.get_text()

            # 건물면적
            for pat in [
                r"전유부분[^㎡\n]{0,30}?([\d.]+)\s*㎡",
                r"건물\s*면적[^\d]{0,10}([\d.]+)\s*㎡",
                r"전용\s*면적[^\d]{0,10}([\d.]+)\s*㎡",
            ]:
                m = re.search(pat, obj_text)
                if m:
                    detail.bldg_ar = float(m.group(1))
                    break

            # 대지면적
            for pat in [
                r"대지권[^㎡\n]{0,30}?([\d.]+)\s*㎡",
                r"대지\s*면적[^\d]{0,10}([\d.]+)\s*㎡",
                r"토지\s*면적[^\d]{0,10}([\d.]+)\s*㎡",
            ]:
                m = re.search(pat, obj_text)
                if m:
                    detail.lnd_ar = float(m.group(1))
                    break

            # 엘리베이터 (HTML에서 빠른 체크 - PDF 없이)
            if not detail.has_elevator:
                no_kws = ["승강기없음", "승강기 없음", "승강기:없음", "E/V없음", "E.V없음", "엘리베이터 없음", "승강기 : 없음"]
                yes_kws = ["승강기있음", "승강기 있음", "승강기:있음", "E/V있음", "엘리베이터 있음", "승강기 : 있음"]
                if any(kw in obj_text for kw in no_kws):
                    detail.has_elevator = "없음"
                elif any(kw in obj_text for kw in yes_kws):
                    detail.has_elevator = "있음"
        except Exception as e:
            print(f"[WARN] 면적/엘베 파싱 실패: {e}")

    def _parse_tenant_info(self, soup: BeautifulSoup, detail: AuctionDetail):
        """임차인 현황 파싱"""
        leas_div = soup.find(id="lyCnt_leas")
        if not leas_div:
            return

        # 말소기준일, 배당요구종기일
        span_box = leas_div.find(class_="spanBox")
        if span_box:
            box_text = span_box.get_text()
            base_match = re.search(r"말소기준일[^\:]*:\s*([\d\-]+)", box_text)
            demand_match = re.search(r"배당요구종기일\s*:\s*([\d\-]+)", box_text)
            if base_match:
                detail.cancel_base_date = base_match.group(1)
            if demand_match:
                detail.demand_deadline = demand_match.group(1)

        # 임차인 테이블
        tenant_table = leas_div.find("table", class_="Ltbl_list")
        if tenant_table:
            rows = tenant_table.find_all("tr")[1:]  # 헤더 제외
            for row in rows:
                cols = row.find_all("td")
                if len(cols) < 2:
                    continue
                text_all = row.get_text(strip=True)
                if "임차내역 없음" in text_all:
                    continue
                if len(cols) >= 7:
                    tenant = TenantInfo(
                        occupant=cols[1].get_text(strip=True),
                        occupy_part=cols[2].get_text(strip=True),
                        deposit=cols[4].get_text(strip=True),
                        resist_power=cols[5].get_text(strip=True),
                        analysis=cols[6].get_text(strip=True),
                    )
                    dates = cols[3].get_text(separator=" ", strip=True)
                    date_parts = dates.split()
                    if len(date_parts) >= 1:
                        tenant.move_in_date = re.sub(r"^전입:", "", date_parts[0])
                    if len(date_parts) >= 2:
                        tenant.confirmed_date = re.sub(r"^확정:", "", date_parts[1])
                    tenant.deposit = re.sub(r"^보:", "", tenant.deposit)
                    tenant.occupy_part = re.sub(r"^점유부분:", "", tenant.occupy_part)
                    detail.tenants.append(tenant)

        # 기타사항
        note_td = leas_div.find(class_="dtLeasP")
        if note_td:
            detail.tenant_note = note_td.get_text(separator=" ", strip=True)

        # 허그 인수조건 포기 / 대항력 포기 감지
        full_leas_text = leas_div.get_text()
        if any(kw in full_leas_text for kw in ["허그", "HUG", "인수조건 포기", "인수조건포기"]):
            detail.hug_waived = True
        if any(kw in full_leas_text for kw in ["대항력 포기", "대항력포기"]):
            detail.resist_waived = True
        # splCdtn 필드도 체크 (search_result 기반)
        for t in detail.tenants:
            if "포기" in t.analysis and "허그" in t.analysis:
                detail.hug_waived = True
            if "포기" in t.analysis and "대항력" in t.analysis:
                detail.resist_waived = True

    def _parse_registry_info(self, soup: BeautifulSoup, detail: AuctionDetail):
        """등기 현황 파싱"""
        rgt_div = soup.find(id="lyCnt_regist")
        if not rgt_div:
            return

        # 채권합계
        title_text = rgt_div.get_text()
        total_match = re.search(r"채권합계금액\s*:\s*([\d,]+원)", title_text)
        if total_match:
            detail.registry_total = total_match.group(1)

        # 등기 테이블
        tables = rgt_div.find_all("table")
        for table in tables:
            rows = table.find_all("tr")[1:]  # 헤더 제외
            for row in rows:
                cols = row.find_all("td")
                if len(cols) < 4:
                    continue
                row_text = row.get_text()
                reg_item = RegistryItem(
                    order=cols[0].get_text(strip=True) if cols else "",
                    reg_date=cols[1].get_text(strip=True) if len(cols) > 1 else "",
                    right_type=cols[2].get_text(strip=True) if len(cols) > 2 else "",
                    holder=cols[3].get_text(strip=True) if len(cols) > 3 else "",
                    amount=cols[4].get_text(strip=True) if len(cols) > 4 else "",
                    note=cols[5].get_text(strip=True) if len(cols) > 5 else "",
                    is_base="말소기준" in row_text,
                    is_deleted="소멸" in row_text,
                )
                if reg_item.right_type:
                    detail.registry.append(reg_item)

    # 실제 편의점 브랜드 키워드
    _CVS_BRANDS = ("GS25", "CU", "세븐일레븐", "이마트24", "미니스톱", "씨유", "지에스25")

    def _parse_env_info(self, soup: BeautifulSoup, detail: AuctionDetail):
        """편의점 / 지하철 / 초등학교 거리 파싱"""
        env_div = soup.find(id="envLtArea")
        if not env_div:
            return
        table = env_div.find("table")
        if not table:
            return

        for row in table.find_all("tr"):
            cols = row.find_all(["td", "th"])
            if len(cols) < 2:
                continue
            category = cols[0].get_text(strip=True)
            content_text = cols[1].get_text(strip=True)

            if "지하철" in category:
                m = re.search(r"(.+?)\s*\((\d+)(m|km)\)", content_text)
                if m:
                    detail.subway = f"{m.group(1).strip()} ({m.group(2)}{m.group(3)})"

            elif "편의점" in category:
                # 실제 편의점 브랜드만 필터링
                for m in re.finditer(r"(.+?)\s*\((\d+)(m|km)\)", content_text):
                    name = m.group(1).strip()
                    if any(brand in name for brand in self._CVS_BRANDS):
                        detail.convenience_store = f"{name} ({m.group(2)}{m.group(3)})"
                        break
                # 브랜드 없으면 첫 번째로 fallback
                if not detail.convenience_store:
                    m0 = re.search(r"(.+?)\s*\((\d+)(m|km)\)", content_text)
                    if m0:
                        detail.convenience_store = f"{m0.group(1).strip()} ({m0.group(2)}{m0.group(3)})"

        # 초등학교: envLtArea 전체 텍스트에서 가장 가까운 것 추출
        env_text = env_div.get_text()
        for m in re.finditer(r'([가-힣]{2,10}초등학교)\s*\((\d+)(m|km)\)', env_text):
            detail.elementary_school = f"{m.group(1)} ({m.group(2)}{m.group(3)})"
            break

    def _extract_document_links(self, soup: BeautifulSoup, detail: AuctionDetail):
        """감정평가서 / 매물명세서 / 내부구조도 링크 추출 + 부동산플래닛 URL"""
        for a in soup.find_all("a"):
            txt = a.get_text(strip=True)
            href = a.get("href", "")
            onclick = a.get("onclick", "")

            # 감정평가서: fileView(tid,'AF',idx,0)
            if txt == "감정평가서":
                m = re.search(r"fileView\(\d+,'AF','?(\d+)'?,", href + onclick)
                if m:
                    detail.appraisal_idx = m.group(1)

            # 매물명세서: fileView(tid,'AG',idx,0)
            elif txt == "매물명세서":
                m = re.search(r"fileView\(\d+,'AG','?(\d+)'?,", href + onclick)
                if m:
                    detail.statement_idx = m.group(1)

        # 내부구조도: fileView(tid,'B','',8)
        for a in soup.find_all("a", href=True):
            if "'B'" in a["href"] and "'내부구조'" in a.get_text() or "내부구조" in a.get_text(strip=True):
                detail.floor_plan_img_url = (
                    f"{BASE_URL}/ca/caFile.php?tid={detail.tid}&tp=B&idx=&fsq=8&free="
                )
                break
        # fallback: 내부구조 링크가 텍스트로 감지
        for a in soup.find_all("a"):
            if "내부구조" in a.get_text():
                detail.floor_plan_img_url = (
                    f"{BASE_URL}/ca/caFile.php?tid={detail.tid}&tp=B&idx=&fsq=8&free="
                )
                break

        # 부동산플래닛 URL (onclick에 bdsplanet.com 포함)
        for el in soup.find_all(True):
            onclick = el.get("onclick", "")
            if "bdsplanet.com" in onclick:
                m = re.search(r"'(https://www\.bdsplanet\.com[^']+)'", onclick)
                if m:
                    detail.planet_url = m.group(1)
                    break

    async def _parse_appraisal_pdf(self, tid: int, idx: str, detail: AuctionDetail, cookies: dict):
        """감정평가서 PDF 다운로드 → 텍스트 파싱 + Vision AI 분석"""
        try:
            import fitz  # PyMuPDF

            pdf_url = f"{BASE_URL}/ca/caFile.php?tid={tid}&tp=AF&idx={idx}&free="

            # 1. caFile.php 로드 → iframe src에서 실제 PDF URL 추출
            await self._page.goto(pdf_url, wait_until="networkidle", timeout=30000)
            await asyncio.sleep(2)
            content = await self._page.content()

            from bs4 import BeautifulSoup as BS
            s = BS(content, "lxml")
            iframe = s.find("iframe", class_="linkView")
            if not iframe:
                print("[WARN] 감정평가서 iframe 없음")
                return

            src = iframe.get("src", "")
            m = re.search(r"file=(/FILE/[^&\"]+\.pdf)", src)
            if not m:
                print(f"[WARN] PDF 경로 파싱 실패: {src[:100]}")
                return

            actual_pdf_url = f"{BASE_URL}{m.group(1)}"

            # 2. page.request로 브라우저 세션 그대로 PDF 다운로드
            resp = await self._page.request.get(actual_pdf_url)
            pdf_bytes = await resp.body()
            if len(pdf_bytes) < 10000:
                print(f"[WARN] PDF 다운로드 실패: size={len(pdf_bytes)}")
                return

            print(f"[INFO] PDF 다운로드 완료: {len(pdf_bytes):,} bytes")

            # 3. 텍스트 파싱
            pdf = fitz.open(stream=pdf_bytes, filetype="pdf")
            full_text = "\n".join(page.get_text() for page in pdf)

            # 건물 연식 (사용승인일)
            if not detail.building_year:
                m2 = re.search(r"(\d{4})년\s*\d{1,2}월\s*\d{1,2}일\s*사용승인", full_text)
                if m2:
                    detail.building_year = m2.group(1)

            # 엘리베이터 유무
            if not detail.has_elevator:
                if any(kw in full_text for kw in ["승강기", "엘리베이터", "E/V"]):
                    if any(kw in full_text for kw in ["승강기없음", "승강기 없음", "승강기:없음", "E/V없음"]):
                        detail.has_elevator = "없음"
                    else:
                        detail.has_elevator = "있음"
                else:
                    # 저층 건물은 기본 없음
                    floor_m = re.search(r"(\d+)층\s*건", full_text)
                    if floor_m and int(floor_m.group(1)) <= 4:
                        detail.has_elevator = "없음"

            # 4. Vision AI - 건물개황도 페이지 찾아서 방 개수 분석
            import os
            api_key = os.getenv("ANTHROPIC_API_KEY", "")
            if not api_key:
                pdf.close()
                return

            import base64, anthropic, json

            floor_plan_page = None
            FLOOR_PLAN_KEYWORDS = ("건물개황도", "내부구조도", "평면도", "건축물현황도", "층평면도", "각층평면")
            # 키워드가 있는 페이지 중 텍스트가 가장 적은 것 선택 (이미지 위주 도면 페이지)
            candidates = []
            for i, page in enumerate(pdf):
                txt = page.get_text()
                if any(kw in txt for kw in FLOOR_PLAN_KEYWORDS):
                    candidates.append((i, len(txt.strip())))
            if candidates:
                floor_plan_page = min(candidates, key=lambda x: x[1])[0]

            if floor_plan_page is None:
                pdf.close()
                return

            mat = fitz.Matrix(2.0, 2.0)
            pix = pdf[floor_plan_page].get_pixmap(matrix=mat)
            img_bytes = pix.tobytes("png")
            img_b64 = base64.standard_b64encode(img_bytes).decode()

            client = anthropic.Anthropic(api_key=api_key)
            msg = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=300,
                messages=[{
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {"type": "base64", "media_type": "image/png", "data": img_b64},
                        },
                        {
                            "type": "text",
                            "text": (
                                "이 건물 평면도/구조도 이미지를 보고 다음 정보를 JSON으로만 답하세요:\n"
                                "{\"room_count\": 방(침실)개수, \"bathroom_count\": 화장실(욕실)개수, \"has_elevator\": \"있음/없음/미확인\"}\n\n"
                                "- 방(침실)이 여러 세대 포함된 경우 한 세대 기준으로 답하세요\n"
                                "- 방이나 화장실을 확인할 수 없으면 0으로 답하세요\n"
                                "- 반드시 JSON만 출력하세요"
                            ),
                        },
                    ],
                }]
            )

            text = msg.content[0].text.strip()
            json_m = re.search(r"\{[^}]+\}", text, re.DOTALL)
            if json_m:
                parsed = json.loads(json_m.group())
                if parsed.get("room_count", 0) > 0:
                    detail.room_count = int(parsed["room_count"])
                if parsed.get("bathroom_count", 0) > 0:
                    detail.bathroom_count = int(parsed["bathroom_count"])
                if parsed.get("has_elevator") in ("있음", "없음"):
                    detail.has_elevator = str(parsed["has_elevator"])

            pdf.close()

        except Exception as e:
            print(f"[WARN] 감정평가서 PDF 파싱 실패: {e}")

    async def _analyze_floor_plan_image(self, detail: AuctionDetail):
        """내부구조도(tp=B) 페이지에서 실제 이미지 URL 추출 후 Vision AI 분석"""
        try:
            import base64, anthropic, json, os

            fp_url = detail.floor_plan_img_url
            await self._page.goto(fp_url, wait_until="networkidle", timeout=30000)
            await asyncio.sleep(2)
            content = await self._page.content()

            from bs4 import BeautifulSoup as BS
            soup = BS(content, "lxml")
            # /FILE/CA/BA/ 패턴의 img src 찾기
            img_url = None
            for img in soup.find_all("img"):
                src = img.get("src", "")
                if "/FILE/CA/" in src and src.lower().endswith((".jpg", ".jpeg", ".png")):
                    img_url = f"{BASE_URL}{src}" if src.startswith("/") else src
                    break

            if not img_url:
                return

            # page.request로 브라우저 세션으로 이미지 다운로드
            resp = await self._page.request.get(img_url)
            img_bytes = await resp.body()
            if len(img_bytes) < 1000:
                return

            img_b64 = base64.standard_b64encode(img_bytes).decode()
            # 확장자로 media_type 결정
            ext = img_url.rsplit(".", 1)[-1].lower()
            media_type = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png"}.get(ext, "image/jpeg")

            client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY", ""))
            msg = client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=300,
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "image", "source": {"type": "base64", "media_type": media_type, "data": img_b64}},
                        {
                            "type": "text",
                            "text": (
                                "이 건물 내부구조도(평면도)를 보고 다음 정보를 JSON으로만 답하세요:\n"
                                "{\"room_count\": 방개수, \"bathroom_count\": 화장실개수, \"has_elevator\": \"있음/없음/미확인\"}\n"
                                "방이나 화장실이 보이지 않으면 0으로 답하세요."
                            ),
                        },
                    ],
                }]
            )

            text = msg.content[0].text.strip()
            json_m = re.search(r"\{[^}]+\}", text, re.DOTALL)
            if json_m:
                parsed = json.loads(json_m.group())
                if parsed.get("room_count", 0) > 0:
                    detail.room_count = int(parsed["room_count"])
                if parsed.get("bathroom_count", 0) > 0:
                    detail.bathroom_count = int(parsed["bathroom_count"])
                if parsed.get("has_elevator") in ("있음", "없음") and not detail.has_elevator:
                    detail.has_elevator = str(parsed["has_elevator"])

        except Exception as e:
            print(f"[WARN] 내부구조도 Vision 분석 실패: {e}")

    def _parse_building_year_from_page(self, soup: BeautifulSoup, detail: AuctionDetail):
        """
        건물 연식 추출 (우선순위)
        1) lyCnt_object 테이블의 보존등기일/건축 관련 텍스트
        2) 현황조사서 텍스트
        3) 실거래가는 trade_prices 수집 후 app.py에서 활용
        """
        try:
            # lyCnt_object 섹션에서 준공/사용승인 파싱
            obj_div = soup.find(id="lyCnt_object")
            if obj_div:
                obj_text = obj_div.get_text()
                patterns = [
                    r"사용승인\s*(?:일\s*)?[:：]?\s*(\d{4})[.\-년]",
                    r"준\s*공\s*(?:일\s*)?[:：]?\s*(\d{4})[.\-년]",
                    r"건축년도\s*[:：]?\s*(\d{4})",
                    r"(\d{4})년\s*(?:건축|준공|사용승인)",
                ]
                for pat in patterns:
                    m = re.search(pat, obj_text)
                    if m:
                        detail.building_year = m.group(1)
                        return

            # 감정원 텍스트의 가격시점 근처에 보존등기일
            full_text = soup.get_text()
            m = re.search(r"보존등기일\s*[:：]?\s*(\d{4})-(\d{2})-(\d{2})", full_text)
            if m and m.group(1) != "0000":
                detail.building_year = f"{m.group(1)}.{m.group(2)}.{m.group(3)}"
                return

            # 현황 섹션
            m2 = re.search(r"(?:건축|사용승인|준공)\s*(?:년도|일|연도)?\s*[:：]?\s*(\d{4})", full_text)
            if m2:
                detail.building_year = m2.group(1)
        except Exception as e:
            print(f"[WARN] 건물연식 파싱 실패: {e}")


# ── 동기 래퍼 ──────────────────────────────────────────────────────

def search_properties(
    regions: List[str],
    max_appraised_value: int = 200_000_000,
    property_types: List[str] = ["다세대", "연립", "빌라"],
    max_pages: int = 5,
) -> List[Dict]:
    async def _run():
        async with TankAuctionCrawler() as crawler:
            return await crawler.search(regions, max_appraised_value, property_types, max_pages)
    return asyncio.run(_run())


def get_detail(tid: int) -> Dict:
    async def _run():
        async with TankAuctionCrawler() as crawler:
            detail = await crawler.get_detail(tid)
            return detail.to_dict()
    return asyncio.run(_run())
