# AutoSeller

도매꾹 상품을 자동으로 수집하여 쿠팡 WING에 등록하는 위탁판매 자동화 파이프라인.

---

## 구조

```
AutoSeller/
├── run_pipeline.py              # 전체 파이프라인 실행 진입점
├── pipeline/
│   ├── step3_product_search.py  # 도매꾹 상품 크롤링
│   ├── step4_margin.py          # 마진 계산 및 필터링
│   ├── step5_register.py        # DB 저장 + 하네스 검증
│   └── step6_upload.py          # 플랫폼 업로드
├── uploader/
│   └── coupang.py               # 쿠팡 WING Open API 업로더
├── db/
│   └── autoseller.db            # SQLite 상품 DB
├── poc/
│   └── domeggook_crawl.py       # 도매꾹 크롤링 POC
└── pw/
    └── pw.md                    # 인증 정보 (비공개, git 제외)
```

---

## 파이프라인

### Step 3 - 도매꾹 상품 수집
- Playwright(headless Chromium)로 도매꾹 로그인 후 키워드 검색
- 페이지네이션 순회 (`&pg=N`)
- 상품 목록 + 상세 크롤링 (이미지, 가격, 최소구매수량, 배송정보)
- 네트워크 오류 시 3회 자동 재시도, 실패 상품 스킵 후 계속 진행

### Step 4 - 마진 계산
- 판매가 = 매입가 x 배수 (기본 2.5x)
- 순이익 = 판매가 - 매입가 - 쿠팡수수료(10.8%) - 배송비(3,000원)
- 최소 마진율 20%, 최소 순이익 1,000원 이상만 통과

### Step 5 - DB 저장
- SQLite `products` 테이블에 저장
- `item_no` 기준 중복 제거
- 상태: `pending` -> `uploaded` / `upload_failed`

### Step 6 - 쿠팡 WING 업로드
- 쿠팡 Open API (HMAC-SHA256 인증)
- 상품 등록: `POST /v2/providers/seller_api/apis/api/v1/marketplace/seller-products`
- 카테고리: 남녀공용2단우산 (69884) - 키워드별 자동 매핑 예정
- 고시정보: 패션잡화 8개 항목 자동 생성

---

## 실행

```bash
cd /Users/parkyongjin/Workspace/AutoSeller
python3 run_pipeline.py
```

### config 주요 항목 (run_pipeline.py)

| 키 | 설명 |
|---|---|
| `domeggook_id` / `domeggook_pw` | 도매꾹 로그인 정보 |
| `max_pages` | 크롤링 페이지 수 (기본 2) |
| `sell_price_multiplier` | 판매가 배수 (기본 2.5) |
| `min_margin_rate` | 최소 마진율 (기본 0.2) |
| `coupang_vendor_id` | 쿠팡 벤더 ID |
| `coupang_display_category` | 쿠팡 카테고리 코드 |

---

## 기술 스택

- Python 3.13
- Playwright (도매꾹 크롤링)
- requests (쿠팡 API 호출)
- SQLite (상품 DB)
- HMAC-SHA256 (쿠팡 WING 인증)

---

## 주의사항

- `pw/pw.md` - 인증 정보 포함, Git 제외 필수
- 쿠팡 WING Open API는 IP 화이트리스트 필요 (WING 개발자센터에서 등록)
- 유동 IP 환경에서는 IP 변경 시마다 WING 연동정보 업데이트 필요
- 서버 배포(EC2) 후 Elastic IP 고정하면 이 문제 해결됨

---

## 현황

| 단계 | 상태 |
|---|---|
| Step 3 도매꾹 크롤링 | 완료 |
| Step 4 마진 계산 | 완료 |
| Step 5 DB 저장 | 완료 |
| Step 6 쿠팡 업로드 | 완료 |
| Step 7 등록 검증 | 미구현 |
| Step 8 알림 | 미구현 |
| 카테고리 자동 매핑 | 미구현 |
| 서버 배포 (EC2) | 예정 |
