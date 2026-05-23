# 부동산 경매 자동화 시스템

소액 빌라 경매 물건을 자동 수집하고, 권리분석·시세 조회까지 한 화면에서 처리하는 대시보드.

## 실행 방법

### 방법 1 — 더블클릭 실행 (macOS)
`경매시스템 시작.command` 파일을 더블클릭하면 브라우저가 자동으로 열립니다.

> 처음 실행 시 macOS 보안 경고 → 시스템 환경설정 > 보안 및 개인 정보 > 어쨌든 열기

### 방법 2 — 터미널 직접 실행
```bash
cd auction_system
streamlit run app.py
```
브라우저에서 `http://localhost:8501` 접속

---

## 주요 기능

| 기능 | 설명 |
|------|------|
| 매물 검색 | 탱크옥션에서 지역·종류·감정가 기준으로 실시간 수집 |
| 권리분석 | 선순위임차인 인수금 자동 계산, 허그/대항력포기 감지 |
| 건물 정보 | 감정평가서 PDF에서 연식·엘베 파싱, 평면도 Vision AI 분석 |
| 실거래가 | 부동산플래닛 API에서 동일 평형 최근 2년 거래 수집 |

## 검색 조건
- 지역: 인천 / 안산 / 고양 / 경기도 광주
- 물건 종류: 다세대 / 연립 / 빌라
- 감정가 상한: 최대 2억 (만원 단위 입력)
- 허그/대항력포기 물건만 필터 가능

## 환경 설정

`.env` 파일에 아래 키 입력 (`.env.example` 참고):

```
TANKAUCTION_ID=탱크옥션_아이디
TANKAUCTION_PW=탱크옥션_비밀번호
ANTHROPIC_API_KEY=클로드_API_키
```

## 설치

```bash
pip install -r requirements.txt
playwright install chromium
```

## 기술 스택

| 역할 | 기술 |
|------|------|
| 웹 크롤링 | Python + Playwright (Headless Chromium) |
| HTML 파싱 | BeautifulSoup4 |
| PDF 파싱 | PyMuPDF (fitz) |
| Vision AI | Claude Haiku |
| 실거래 수집 | Playwright (부동산플래닛 API 인터셉트) |
| 대시보드 | Streamlit |
