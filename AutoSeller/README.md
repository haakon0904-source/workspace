# AutoSeller

도매꾹 상품을 자동 수집하여 쿠팡·네이버 스마트스토어에 위탁판매 등록하는 자동화 파이프라인.

---

## 구조

```
AutoSeller/
├── run_pipeline.py          # 파이프라인 전체 실행 진입점
├── start.sh                 # 웹 대시보드 서버 시작 스크립트
├── pipeline/
│   ├── step1_trending_keywords.py   # 네이버 데이터랩 트렌드 키워드 수집
│   ├── step2_keyword_variations.py  # 키워드 변형 생성
│   ├── step3_product_search.py      # 도매꾹 상품 크롤링 (Playwright)
│   ├── step4_margin.py              # 마진 계산 + pHash 중복 제거
│   ├── step5_register.py            # DB 저장 + 하네스 검증
│   ├── step6_upload.py              # 쿠팡/네이버 업로드
│   └── step7_order.py               # 주문 수집 및 발주 처리
├── uploader/
│   ├── coupang.py                   # 쿠팡 WING API 업로더
│   ├── naver.py                     # 네이버 스마트스토어 API 업로더
│   ├── coupang_order.py             # 쿠팡 주문 처리
│   ├── domeggook_order.py           # 도매꾹 발주 자동화
│   └── coupang_commission.py        # 카테고리별 수수료율 조회
├── web/
│   ├── app.py                       # Flask 웹 대시보드
│   └── templates/index.html         # 대시보드 UI
├── tools/
│   ├── find_category.py             # 쿠팡/네이버 카테고리 ID 조회
│   ├── check_orders_notify.py       # 주문 텔레그램 알림
│   └── refetch_detail_imgs.py       # 상세이미지 재수집
├── db/
│   └── autoseller.db                # SQLite DB (git 제외)
└── pw/
    └── pw.md                        # 인증 정보 (git 제외)
```

---

## 파이프라인 흐름

```
도매꾹 크롤링 (step3)
    → 마진 계산 + pHash 중복제거 (step4)
    → DB 저장 + 검증 (step5)
    → 쿠팡 / 네이버 업로드 (step6)
    → 주문 수집 + 도매꾹 발주 (step7)
```

---

## 실행 방법

### 웹 대시보드 (권장)

```bash
bash start.sh
# → http://localhost:5001
```

대시보드에서 키워드 입력 후 플랫폼(쿠팡/네이버) 선택 → 크롤링 시작.

### CLI 직접 실행

```bash
python3 run_pipeline.py
```

`run_pipeline.py` 상단의 `KEYWORD_CATEGORIES`에 키워드·카테고리·수수료율을 설정하고 실행.

### 주문 처리

```bash
python3 pipeline/step7_order.py
```

미처리 주문을 수집하여 도매꾹에 자동 발주.

### 유틸

```bash
# 쿠팡/네이버 카테고리 ID 조회
python3 tools/find_category.py

# 주문 텔레그램 알림
python3 tools/check_orders_notify.py
```

---

## 설정

`pw/pw.md`에 아래 항목을 기재 (git 제외):

```
도매꾹 ID
도매꾹 PW

Access Key : <쿠팡 access key>
Secret Key : <쿠팡 secret key>

Naver Client ID: <네이버 데이터랩 Client ID>
Naver Client Secret: <네이버 데이터랩 Client Secret>

네이버 커머스 Client ID: <스마트스토어 API Client ID>
네이버 커머스 Client Secret: <스마트스토어 bcrypt salt ($2a$...)>
네이버 CS 전화번호: 010-XXXX-XXXX

텔레그램 Bot Token: <token>
텔레그램 Chat ID: <chat_id>

사업자번호: XXX-XX-XXXXX
생년월일 : YYMMDD
```

주요 파이프라인 파라미터는 `run_pipeline.py`의 `CONFIG`에서 조정:

| 키 | 설명 | 기본값 |
|---|---|---|
| `sell_price_multiplier` | 도매가 대비 판매가 배수 | 2.5 |
| `min_margin_rate` | 최소 마진율 | 0.3 (30%) |
| `min_profit` | 최소 순이익 (원) | 1000 |
| `filter_min_price` | 최소 도매가 (원) | 3000 |
| `filter_max_price` | 최대 도매가 (원) | 30000 |
| `max_pages` | 도매꾹 검색 페이지 수 | 2 |

---

## 마진 계산 공식

```
수수료    = 판매가 × 수수료율
세전이익  = 판매가 - 도매가 - 배송비 - 수수료
부가세    = 세전이익 × 10%
순이익    = 세전이익 - 부가세
마진율    = 순이익 / 판매가
```

---

## 이미지 중복 제거 (pHash)

동일한 실물 상품이 도매꾹에 여러 판매자로 등록된 경우, step4에서 대표 이미지의 perceptual hash를 비교하여 중복을 제거합니다.

- Hamming distance ≤ 8 → 동일 상품으로 판단
- 중복 시 **판매가 낮은 것 유지** (소비자 기준)
- 이미지 다운로드는 병렬 처리 (ThreadPoolExecutor)

---

## 지원 플랫폼

| 플랫폼 | 상품 업로드 | 주문 수집 | 발주 |
|---|---|---|---|
| 쿠팡 | ✅ | ✅ | ✅ (도매꾹 자동발주) |
| 네이버 스마트스토어 | ✅ | 예정 | 예정 |
| 11번가 / G마켓 / 토스쇼핑 | 예정 | - | - |

---

## 의존성

```bash
pip install playwright requests bcrypt imagehash Pillow flask
playwright install chromium
```

---

## 주의사항

- `pw/pw.md`, `db/` — 인증 정보 및 DB 포함, git 제외 필수
- 쿠팡 WING Open API는 IP 화이트리스트 필요 (WING 개발자센터에서 등록)
- 네이버 커머스 API 인증은 bcrypt (HMAC-SHA256 아님) — Client Secret이 `$2a$...` 형태의 bcrypt salt
- 유동 IP 환경에서는 쿠팡 IP 변경 시마다 WING 연동정보 업데이트 필요 → EC2 Elastic IP로 해결
