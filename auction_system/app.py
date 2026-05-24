"""
부동산 경매 자동화 대시보드
실행: streamlit run app.py
"""
import streamlit as st
import pandas as pd
import re, sys, os, time
import queue as q_module

sys.path.insert(0, os.path.dirname(__file__))
from crawlers.tankauction import TankAuctionCrawler, PROPERTY_CODES
from crawlers.budongsan_planet import fetch_planet_trades_sync
import concurrent.futures

st.set_page_config(page_title="부동산 경매 자동화", page_icon="🏠", layout="wide")

st.markdown("""
<style>
.tag-danger { background:#ffe0e0; color:#c0392b; padding:2px 8px; border-radius:4px; font-size:12px; font-weight:600; }
.tag-warn   { background:#fff3cd; color:#856404; padding:2px 8px; border-radius:4px; font-size:12px; font-weight:600; }
.tag-safe   { background:#d4edda; color:#155724; padding:2px 8px; border-radius:4px; font-size:12px; font-weight:600; }
.tag-info   { background:#cce5ff; color:#004085; padding:2px 8px; border-radius:4px; font-size:12px; font-weight:600; }
.conclusion-ok   { background:#d4edda; color:#155724; padding:8px 14px; border-radius:6px; font-weight:700; }
.conclusion-warn { background:#fff3cd; color:#856404; padding:8px 14px; border-radius:6px; font-weight:700; }
.conclusion-bad  { background:#ffe0e0; color:#c0392b; padding:8px 14px; border-radius:6px; font-weight:700; }
</style>
""", unsafe_allow_html=True)

st.title("🏠 부동산 경매 자동화 대시보드")

# ── 헬퍼 ─────────────────────────────────────────────────────────
def fmt_price(val):
    if not val or val == 0:
        return "-"
    wan = val // 10_000
    if wan >= 10_000:
        uk = wan // 10_000
        rem = wan % 10_000
        return f"{uk}억 {rem:,}만원" if rem else f"{uk}억"
    return f"{wan:,}만원"

def fmt_area(val):
    try:
        m2 = float(val)
        py = m2 / 3.3058
        return f"{m2:.1f}㎡\n({py:.1f}평)"
    except Exception:
        return str(val) if val else "-"

def parse_deposit_man(deposit_str):
    """보증금 문자열 → 만원 정수"""
    try:
        s = str(deposit_str).replace(",", "").replace(" ", "")
        m = re.search(r"(\d+)만원", s)
        if m:
            return int(m.group(1))
        m = re.search(r"(\d+)원", s)
        if m:
            return int(m.group(1)) // 10_000
    except Exception:
        pass
    return 0

def calc_insu(tenants):
    """선순위임차인 인수금 합계 (만원)"""
    return sum(parse_deposit_man(t.get("deposit", "")) for t in tenants if t.get("resist_power") == "있음")

def rights_conclusion(tenants, hug_waived, resist_waived, insu_man):
    """권리분석 결론 HTML"""
    tags = []
    if hug_waived:
        tags.append('<span class="tag-info">허그인수조건포기</span>')
    if resist_waived:
        tags.append('<span class="tag-info">대항력포기</span>')

    senior = [t for t in tenants if t.get("resist_power") == "있음"]
    if senior:
        insu_txt = f"{insu_man:,}만원" if insu_man else "금액미확인"
        body = f'⚠️ 선순위임차인 {len(senior)}명 · 인수금 {insu_txt}'
        cls = "conclusion-bad"
    elif tenants:
        body = f'△ 임차인 {len(tenants)}명 · 인수금 없음'
        cls = "conclusion-warn"
    else:
        body = '✅ 임차인 없음 · 권리분석 이상없음'
        cls = "conclusion-ok"

    tag_str = " ".join(tags)
    return f'<div class="{cls}">{body} {tag_str}</div>'

# ── 실행 래퍼 ────────────────────────────────────────────────────
def run_search(regions, max_val, prop_types, progress_callback=None):
    def _run():
        with TankAuctionCrawler() as c:
            return c.search(regions, max_val, prop_types, progress_callback=progress_callback)
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
        return ex.submit(_run).result()

def run_detail(tid):
    def _run():
        with TankAuctionCrawler() as c:
            return c.get_detail(tid).to_dict()
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
        return ex.submit(_run).result()

# ── 사이드바 ─────────────────────────────────────────────────────
with st.sidebar:
    st.header("🔍 검색 조건")
    regions = st.multiselect("지역", ["인천", "안산", "고양", "경기도 광주"], default=["인천"])
    prop_types = st.multiselect("물건 종류", ["다세대", "연립", "빌라"], default=["다세대", "연립"])
    max_appraised = st.number_input("감정가 상한 (만원)", 1000, 50000, 20000, 1000)
    only_waived = st.checkbox("허그/대항력포기 물건만")
    st.divider()
    search_btn = st.button("🔍 매물 검색", type="primary", use_container_width=True)

tab_main, tab_doc = st.tabs(["📊 대시보드", "📖 설계 문서"])

with tab_doc:
    st.markdown("""
## 시스템 개요

탱크옥션에서 소액 빌라 경매 물건을 자동 수집하고, 권리분석·시세 조회까지 한 화면에서 처리하는 자동화 대시보드.
수익률/입찰가 계산은 직접 판단하며, 이 시스템은 **정보 수집과 정리**에 집중합니다.

---

## 투자 대상 조건

| 항목 | 조건 |
|------|------|
| 지역 | 인천, 안산, 고양, 경기도 광주 |
| 물건 종류 | 다세대, 연립, 빌라 |
| 감정가 상한 | 2억 이하 |
| 방 개수 | 3개 (Vision AI로 감정평가서에서 확인) |
| 엘리베이터 | 없는 2~3층 빌라 우선 / 신축이면 2층부터 |
| 건물 연식 | 표기 (감정평가서 사용승인일 기준) |

---

## 수집 정보 및 출처

### 탱크옥션 목록 (AuctList.php)
- 사건번호, 주소, 감정가, 최저매각가, 최저가율, 매각기일, 상태, 특수조건
- 건물면적(㎡), 대지면적(㎡)

### 탱크옥션 상세 (caView.php)
| 항목 | 파싱 방법 |
|------|-----------|
| 지하철 거리 | `envLtArea` 테이블 |
| 편의점 거리 | `envLtArea` 테이블 (GS25·CU·세븐일레븐·이마트24 등 브랜드 필터) |
| 초등학교 거리 | `envLtArea` 전체 텍스트에서 `초등학교 (Xm)` 패턴 추출 |
| 말소기준일 | `lyCnt_leas` 섹션 |
| 임차인 현황 | `lyCnt_leas` 테이블 (전입일·확정일자·보증금·대항력) |
| 등기 현황 | `lyCnt_regist` 테이블 |
| 허그 인수조건 포기 | 임차인 분석 텍스트에서 "허그/HUG/인수조건포기" 키워드 감지 |
| 대항력 포기 | 임차인 분석 텍스트에서 "대항력포기" 키워드 감지 |

### 감정평가서 PDF (caFile.php?tp=AF)
| 항목 | 방법 |
|------|------|
| 건물 연식 | PDF 텍스트에서 `XXXX년 XX월 XX일 사용승인` 패턴 |
| 엘리베이터 | PDF 텍스트에서 `승강기/엘리베이터/E/V` 키워드 |
| 방 개수 | 평면도 페이지(건물개황도·평면도 등) → **Claude Vision AI** 분석 |
| 화장실 개수 | 동일 (Vision AI) |

> PDF는 Playwright 응답 인터셉터로 다운로드 → PyMuPDF(fitz)로 파싱

### 내부구조도 (caFile.php?tp=B)
- PDF에서 평면도를 찾지 못한 경우 fallback
- 탱크옥션 내부구조도 이미지(JPG) → Claude Vision AI 분석

### 부동산플래닛
- 탱크옥션 상세 페이지의 부동산플래닛 링크(lat/lng 포함) 추출
- `getRealpriceMapMarker` API 응답 캡처
- 필터: 매매(t_type=1), 최근 2년, 동일 평형 ±30%
- 최대 8건 (거래년월·면적·금액·동·건축년도·물건종류)

---

## 권리분석 결론 로직

```
선순위임차인(대항력 있음) 존재
  → ⚠️ 위험  · 인수금 = Σ 선순위임차인 보증금
임차인 있음 (대항력 없음)
  → △ 주의  · 인수금 없음
임차인 없음
  → ✅ 이상없음 · 인수금 없음
```

허그 인수조건 포기 / 대항력 포기가 감지되면 별도 태그 표시.

---

## 기술 스택

| 역할 | 기술 |
|------|------|
| 웹 크롤링 | Python + Playwright (Headless Chromium) |
| HTML 파싱 | BeautifulSoup4 |
| PDF 파싱 | PyMuPDF (fitz) |
| Vision AI | Claude Haiku (claude-haiku-4-5) |
| 실거래 수집 | Playwright (부동산플래닛 API 인터셉트) |
| 대시보드 | Streamlit |
| 인증 | .env (TANKAUCTION_ID/PW, ANTHROPIC_API_KEY) |

---

## 파일 구조

```
auction_system/
├── app.py                        # Streamlit 대시보드
├── .env                          # 인증 정보
└── crawlers/
    ├── tankauction.py            # 탱크옥션 크롤러 (메인)
    ├── budongsan_planet.py       # 부동산플래닛 실거래 수집
    └── vision_analyzer.py        # Claude Vision AI (standalone)
```
""")

with tab_main:
    # ── 검색 실행 ────────────────────────────────────────────────
    if search_btn:
        if not regions:
            st.warning("지역을 선택해주세요.")
        else:
            pq = q_module.Queue()

            def on_progress(region, page, total_pages, found):
                pq.put({"type": "list", "region": region, "page": page,
                        "total_pages": total_pages, "found": found})

            def on_batch(completed, total, est_remaining):
                pq.put({"type": "batch", "completed": completed,
                        "total": total, "est_remaining": est_remaining})

            status_ph = st.empty()
            bar_ph = st.empty()

            def _do_search():
                with TankAuctionCrawler() as c:
                    return c.search(regions, max_appraised * 10_000, prop_types,
                                    progress_callback=on_progress,
                                    batch_callback=on_batch)

            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
                future = ex.submit(_do_search)
                while not future.done():
                    try:
                        msg = pq.get_nowait()
                        if msg["type"] == "list":
                            pct = msg["page"] / msg["total_pages"] if msg["total_pages"] > 0 else 0.0
                            bar_ph.progress(pct)
                            status_ph.markdown(
                                f"🔍 **[목록 수집]** {msg['region']} "
                                f"{msg['page']}/{msg['total_pages']} 페이지 · {msg['found']}건")
                        elif msg["type"] == "batch":
                            pct = msg["completed"] / msg["total"] if msg["total"] > 0 else 0.0
                            rem = msg["est_remaining"]
                            time_str = f"{rem//60}분 {rem%60}초" if rem >= 60 else f"{rem}초"
                            bar_ph.progress(pct)
                            status_ph.markdown(
                                f"🔎 **[엘베/방 수집]** {msg['completed']}/{msg['total']}건 "
                                f"· 잔여 약 {time_str}")
                    except q_module.Empty:
                        time.sleep(0.2)
                results = future.result()

            bar_ph.empty()
            status_ph.empty()

            if results:
                st.session_state["results"] = results
                st.session_state.pop("detail", None)
                st.success(f"총 **{len(results)}건** 검색 완료")
            else:
                st.info("검색 결과가 없습니다.")

    # ── 결과 목록 ────────────────────────────────────────────────
    if "results" in st.session_state and st.session_state["results"]:
        results = st.session_state["results"]
        df = pd.DataFrame(results)

        st.markdown("#### 📋 검색 결과")

        col1, col2, col3 = st.columns(3)
        with col1:
            filter_region = st.multiselect("지역 필터", df["search_region"].unique().tolist(),
                                           default=df["search_region"].unique().tolist(), key="fr")
        with col2:
            available_types = [t for t in prop_types if t in df["ctgr"].unique().tolist()]
            filter_type = st.multiselect("종류 필터", prop_types,
                                         default=available_types if available_types else prop_types, key="ft")
        with col3:
            max_fail = st.slider("최대 유찰", 0, 10, 10, key="mf")

        # 주소에서 구 추출
        df["gu"] = df["regnAdrs"].str.extract(r"([가-힣]+구)")
        gu_options = sorted(df["gu"].dropna().unique().tolist())

        col4, col5, col6, col7, col8 = st.columns([2, 1, 1, 1, 1])
        with col4:
            max_pct = st.slider("최저가율% 상한", 50, 100, 100, key="mp")
        with col5:
            floor_min = st.number_input("층 최소", 1, 20, 1, key="fmin")
        with col6:
            floor_max = st.number_input("층 최대", 1, 20, 20, key="fmax")
        with col7:
            elev_filter = st.selectbox("엘베", ["전체", "Y", "N", "미확인"], key="ef")
        with col8:
            min_rooms = st.selectbox("방 최소", ["전체", "2개↑", "3개↑", "4개↑"], key="mr")

        col9, col10, col11 = st.columns([1, 1, 2])
        max_amt_default = int(df["minbAmt"].max() // 10_000) if "minbAmt" in df.columns else 20000
        with col9:
            price_min = st.number_input("최저가 최소(만원)", 0, 50000, 0, 500, key="prmin")
        with col10:
            price_max = st.number_input("최저가 최대(만원)", 0, 50000, max_amt_default, 500, key="prmax")
        with col11:
            filter_gu = st.multiselect("구 필터", gu_options, default=gu_options, key="fg") if gu_options else []

        df["fail_cnt"] = df["statNm"].str.extract(r"(\d+)회").fillna(0).astype(int)
        filtered = df[
            df["search_region"].isin(filter_region) &
            df["ctgr"].isin(filter_type) &
            (df["fail_cnt"] <= max_fail)
        ]

        # 최저가율% 상한 필터
        filtered = filtered[filtered["minbPct"].fillna(100).astype(int) <= max_pct]

        # 층 범위 필터
        def _extract_floor(s):
            m = re.match(r"(\d+)층", str(s))
            return int(m.group(1)) if m else None
        if floor_min > 1 or floor_max < 20:
            floor_nums = filtered["floor_info"].apply(_extract_floor)
            filtered = filtered[floor_nums.isna() | ((floor_nums >= floor_min) & (floor_nums <= floor_max))]

        # 최저가 범위 필터
        if price_min > 0 or price_max < max_amt_default:
            filtered = filtered[
                (filtered["minbAmt"].fillna(0) >= price_min * 10_000) &
                (filtered["minbAmt"].fillna(0) <= price_max * 10_000)
            ]

        # 구 필터
        if filter_gu:
            filtered = filtered[filtered["gu"].isin(filter_gu)]

        # 엘베 필터
        if elev_filter != "전체" and "list_elevator" in filtered.columns:
            filtered = filtered[filtered["list_elevator"].astype(str) == elev_filter]

        # 방 최소 필터
        if min_rooms != "전체" and "list_room_info" in filtered.columns:
            min_r = int(min_rooms[0])
            def _room_num(s):
                m = re.search(r"방(\d+)", str(s))
                return int(m.group(1)) if m else None
            room_nums = filtered["list_room_info"].apply(_room_num)
            filtered = filtered[room_nums.isna() | (room_nums >= min_r)]

        # 허그/대항력포기 필터 - 여러 필드·표기 통합 검색
        if only_waived:
            waive_kws = "포기|허그|HUG|인수조건"
            check_cols = [c for c in ["splCdtn", "statNm", "note", "remark"] if c in filtered.columns]
            mask = pd.Series(False, index=filtered.index)
            for col in check_cols:
                mask |= filtered[col].astype(str).str.contains(waive_kws, case=False, na=False, regex=True)
            filtered = filtered[mask]

        st.caption(f"{len(filtered)}건 표시")

        base_cols = ["saNo", "search_region", "ctgr", "regnAdds", "floor_info", "apslAmt", "minbAmt", "minbPct", "statNm", "bidDt", "splCdtn"]
        area_cols = [c for c in ["bldgAr", "lndAr"] if c in filtered.columns]
        # 주소 + 층 + 연식 + 엘베 + 면적 순서로 배치
        extra_cols = [c for c in ["floor_info", "list_build_year", "list_elevator", "list_room_info"] if c in filtered.columns]
        display_cols = ["saNo", "search_region", "ctgr", "regnAdrs"] + \
                       extra_cols + area_cols + \
                       ["apslAmt", "minbAmt", "minbPct", "statNm", "bidDt", "splCdtn"]
        display = filtered[[c for c in display_cols if c in filtered.columns]].copy()

        col_rename = {
            "saNo": "사건번호", "search_region": "지역", "ctgr": "종류", "regnAdrs": "주소",
            "floor_info": "층", "list_build_year": "연식", "list_elevator": "엘베",
            "list_room_info": "방/욕",
            "bldgAr": "건물㎡", "lndAr": "대지㎡",
            "apslAmt": "감정가", "minbAmt": "최저가", "minbPct": "최저가율%",
            "statNm": "상태", "bidDt": "매각기일", "splCdtn": "특수조건"
        }
        display.rename(columns={k: v for k, v in col_rename.items() if k in display.columns}, inplace=True)
        if "감정가" in display.columns:
            display["감정가"] = display["감정가"].apply(fmt_price)
        if "최저가" in display.columns:
            display["최저가"] = display["최저가"].apply(fmt_price)
        if "최저가율%" in display.columns:
            display["최저가율%"] = display["최저가율%"].apply(lambda x: f"{x}%")

        st.dataframe(display, use_container_width=True, hide_index=True, height=280)

        # ── 물건 선택 → 상세 ─────────────────────────────────────
        st.markdown("#### 🔎 물건 상세 분석")

        options = {f"[{r['saNo']}] {r['regnAdrs'][:50]}": r["tid"] for r in filtered.to_dict("records")}
        selected_label = st.selectbox("분석할 물건 선택", list(options.keys()))
        selected_tid = options.get(selected_label)

        # ── 선택 물건 간략 정보 (상세분석 전 판단용) ─────────────
        pre_row = filtered[filtered["tid"] == selected_tid]
        if not pre_row.empty:
            pr = pre_row.iloc[0]
            p1, p2, p3, p4, p5 = st.columns(5)
            p1.info(f"**감정가** {fmt_price(pr['apslAmt'])}")
            p2.info(f"**최저가** {fmt_price(pr['minbAmt'])} ({pr['minbPct']}%)")
            floor_val = pr.get("floor_info", "") or "-"
            p3.info(f"**층** {floor_val}")
            bldg_val = fmt_area(pr.get("bldgAr", 0))
            p4.info(f"**건물면적** {bldg_val}")
            p5.info(f"**상태** {pr.get('statNm', '-')}")

        btn_col1, btn_col2 = st.columns([3, 1])
        with btn_col2:
            st.link_button("🔗 탱크옥션 상세", f"https://www.tankauction.com/ca/caView.php?tid={selected_tid}", use_container_width=True)
        with btn_col1:
            run_btn = st.button("📊 상세 분석 실행", type="primary", use_container_width=True)
        if run_btn:
            with st.spinner("권리분석 및 실거래가 조회 중..."):
                detail = run_detail(selected_tid)
            planet_url = detail.get("planet_url", "")
            if planet_url:
                with st.spinner("부동산플래닛 실거래 조회 중..."):
                    sel_row = filtered[filtered["tid"] == selected_tid]
                    bldg_m2 = 0.0
                    prop_ctgr = ""
                    if not sel_row.empty:
                        try:
                            bldg_m2 = float(sel_row.iloc[0].get("bldgAr") or detail.get("bldg_ar") or 0)
                        except Exception:
                            pass
                        prop_ctgr = str(sel_row.iloc[0].get("ctgr", ""))
                    detail["planet_trades"] = fetch_planet_trades_sync(
                        planet_url, bldg_m2, prop_ctgr, max_results=8
                    )
            else:
                detail["planet_trades"] = []
            st.session_state["detail"] = detail

            # Vision AI 결과로 검색결과 목록의 방/욕 컬럼 업데이트
            rc = detail.get("room_count", 0)
            bc = detail.get("bathroom_count", 0)
            if (rc or bc) and "list_room_info" in st.session_state["results"][0]:
                r_str = f"{rc}방/{bc}욕" if (rc and bc) else (f"{rc}방" if rc else f"{bc}욕")
                for item in st.session_state["results"]:
                    if item.get("tid") == selected_tid:
                        item["list_room_info"] = r_str
                        break

        # ── 상세 결과 출력 ───────────────────────────────────────
        if "detail" in st.session_state:
            d = st.session_state["detail"]
            row = filtered[filtered["tid"] == selected_tid]
            if row.empty:
                st.warning("해당 물건 정보를 찾을 수 없습니다.")
            else:
                row = row.iloc[0]
                tenants = d.get("tenants", [])
                insu_man = calc_insu(tenants)

                # ── 기본정보 · 건물정보 · 주변환경 (소형 테이블) ──
                bldg_area = row.get("bldgAr") or d.get("bldg_ar") or 0
                lnd_area  = row.get("lndAr")  or d.get("lnd_ar")  or 0
                room_label = f"{d.get('room_count',0)}개" if d.get('room_count') else "-"
                bath_label = f"{d.get('bathroom_count',0)}개" if d.get('bathroom_count') else "-"
                splcdtn_html = f'<tr><th>특수조건</th><td colspan="5" style="color:#c0392b">{row.get("splCdtn","")}</td></tr>' if row.get("splCdtn") else ""

                info_html = f"""
<style>
.info-tbl {{width:100%;border-collapse:collapse;font-size:12px;}}
.info-tbl th {{background:#f0f2f6;color:#555;font-weight:600;padding:4px 8px;border:1px solid #ddd;white-space:nowrap;width:80px;}}
.info-tbl td {{padding:4px 8px;border:1px solid #ddd;}}
.info-tbl .section-hd {{background:#e8eaf0;font-weight:700;color:#333;font-size:11px;padding:3px 8px;}}
</style>
<table class="info-tbl">
  <tr><td class="section-hd" colspan="6">📌 기본 정보</td></tr>
  <tr>
    <th>감정가</th><td>{fmt_price(row["apslAmt"])}</td>
    <th>최저매각가</th><td>{fmt_price(row["minbAmt"])} ({row['minbPct']}%)</td>
    <th>보증금(10%)</th><td>{fmt_price(int(row["minbAmt"] * 0.1))}</td>
  </tr>
  <tr>
    <th>인수금</th><td>{"<b style='color:#c0392b'>"+f"{insu_man:,}만원"+"</b>" if insu_man else "없음"}</td>
    <th>매각기일</th><td>{row['bidDt']}</td>
    <th>상태</th><td>{row['statNm']}</td>
  </tr>
  <tr><th>주소</th><td colspan="3">{row['regnAdrs']}</td><th>법원/계</th><td>{row.get('crtDpt','-')}</td></tr>
  <tr><th>사건번호</th><td colspan="5">{row['saNo']}</td></tr>
  {splcdtn_html}
  <tr><td class="section-hd" colspan="6">🏗️ 건물정보</td></tr>
  <tr>
    <th>건물면적</th><td>{fmt_area(bldg_area)}</td>
    <th>대지면적</th><td>{fmt_area(lnd_area)}</td>
    <th>연식</th><td>{d.get("building_year") or "-"}</td>
  </tr>
  <tr>
    <th>엘베</th><td>{d.get("has_elevator") or "-"}</td>
    <th>방/화장실</th><td>{room_label}/{bath_label}</td>
    <th>층</th><td>{row.get("floor_info") or "-"}</td>
  </tr>
  <tr><td class="section-hd" colspan="6">🗺️ 주변환경</td></tr>
  <tr>
    <th>지하철</th><td>{d.get("subway") or "-"}</td>
    <th>편의점</th><td>{d.get("convenience_store") or "-"}</td>
    <th>초등학교</th><td>{d.get("elementary_school") or "-"}</td>
  </tr>
</table>
"""
                st.markdown(info_html, unsafe_allow_html=True)
                st.markdown("")

                # ── 권리분석 ─────────────────────────────────────
                st.markdown("#### ⚖️ 권리분석")

                conclusion_html = rights_conclusion(tenants, d.get("hug_waived", False), d.get("resist_waived", False), insu_man)
                st.markdown(conclusion_html, unsafe_allow_html=True)
                st.markdown(f"말소기준일 `{d.get('cancel_base_date','-')}` | 배당요구종기일 `{d.get('demand_deadline','-')}`")

                r_col1, r_col2 = st.columns(2)
                with r_col1:
                    if tenants:
                        tnt_df = pd.DataFrame(tenants)[["occupant","occupy_part","move_in_date","confirmed_date","deposit","resist_power","analysis"]]
                        tnt_df.columns = ["임차인","점유부분","전입일","확정일자","보증금","대항력","분석"]
                        st.dataframe(tnt_df, use_container_width=True, hide_index=True)
                    else:
                        st.success("✅ 임차내역 없음")
                    if d.get("tenant_note"):
                        with st.expander("임차인 기타사항"):
                            st.text(d["tenant_note"])

                with r_col2:
                    registry = d.get("registry", [])
                    if registry:
                        reg_df = pd.DataFrame(registry)[["reg_date","right_type","holder","amount","is_base","is_deleted"]]
                        reg_df.columns = ["접수일","권리종류","권리자","채권금액","말소기준","소멸"]
                        reg_df["말소기준"] = reg_df["말소기준"].apply(lambda x: "✅" if x else "")
                        reg_df["소멸"] = reg_df["소멸"].apply(lambda x: "소멸" if x else "인수")
                        st.dataframe(reg_df, use_container_width=True, hide_index=True)

                # ── 부동산플래닛 실거래 ──────────────────────────
                st.markdown("#### 💰 부동산플래닛 실거래 (최근 2년)")
                planet_trades = d.get("planet_trades", [])
                if planet_trades:
                    pt_df = pd.DataFrame(planet_trades)
                    st.dataframe(pt_df, use_container_width=True, hide_index=True)
                    try:
                        prices = [int(str(t.get("거래금액(만원)", "0")).replace(",", ""))
                                  for t in planet_trades if str(t.get("거래금액(만원)", "0")).replace(",", "").isdigit()]
                        if prices:
                            tc1, tc2, tc3 = st.columns(3)
                            tc1.metric("평균 거래가", f"{sum(prices)/len(prices):,.0f}만원")
                            tc2.metric("최고 거래가", f"{max(prices):,}만원")
                            tc3.metric("최저 거래가", f"{min(prices):,}만원")
                    except Exception:
                        pass
                else:
                    st.info("부동산플래닛 실거래 데이터 없음")

                trades = d.get("trade_prices", [])
                if trades:
                    with st.expander("📄 국토부 실거래 원본"):
                        trade_df = pd.DataFrame(trades)
                        cols_show = [c for c in ["계약년월일","전용면적","층","거래금액","구분"] if c in trade_df.columns]
                        if cols_show:
                            st.dataframe(trade_df[cols_show].sort_values("계약년월일", ascending=False),
                                         use_container_width=True, hide_index=True)

    else:
        with st.expander("📖 사용 방법"):
            st.markdown("""
            1. 왼쪽에서 **지역**, **물건 종류**, **감정가 상한** 설정
            2. **매물 검색** 클릭 → 탱크옥션에서 실시간 수집
            3. 결과 테이블에서 원하는 물건 선택
            4. **상세 분석 실행** → 권리분석 + 실거래가 + Vision AI 자동 조회
            """)
