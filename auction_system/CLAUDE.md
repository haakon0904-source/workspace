# 부동산 경매 자동화 시스템 - 프로젝트 가이드

## 실행
```bash
cd /Users/parkyongjin/PycharmProjects/auction_system
streamlit run app.py
```

## 구조
```
auction_system/
├── app.py                      # Streamlit 대시보드 (메인)
├── crawlers/
│   ├── tankauction.py          # 탱크옥션 크롤러 (목록+상세)
│   ├── budongsan_planet.py     # 부동산플래닛 실거래 수집
│   └── vision_analyzer.py      # Claude Vision AI (standalone)
├── .env                        # TANKAUCTION_ID, TANKAUCTION_PW, ANTHROPIC_API_KEY
└── CLAUDE.md                   # 이 파일
```

## 데이터 흐름
1. **탱크옥션 목록 API** (`AuctList.php`) → 검색결과 목록
2. **탱크옥션 상세 페이지** (`caView.php`) → 권리분석, 임차인, 등기, 주변환경
3. **감정평가서 PDF** → 건물연식, 엘베, 방/화장실 (Vision AI)
4. **부동산플래닛** → 실거래가 (동일 건물종류 + 유사 면적 ±25%)

## 검색 조건 (사이드바)
- 지역: 인천/안산/고양/경기도 광주
- 물건종류: 다세대/연립/빌라
- 감정가 상한 (만원)
- 최대 페이지 수 (현재 슬라이더, 기본 3페이지 → **개편 필요**)
- 허그/대항력포기 물건만 (현재 후처리 필터 → **개편 필요**)

---

## 미완료 작업 (다음 세션에서 이어할 것)

### 🔴 우선순위 높음

#### 1. 검색 전체 개편 (tankauction.py `_search_region`)
**문제:**
- `max_pages` 슬라이더 기본값 3 → 최대 60건밖에 못 가져옴
- 매 페이지마다 `siCd` change 이벤트 재발생 → `guCd` 초기화 가능성
- 허그/대항력 포기를 API 조건이 아닌 후처리로 필터링

**해결 방향:**
- 검색 조건을 **1회만 설정**하고 전체 페이지 자동 순회
- `totalCnt` 기준으로 페이지 수 자동 계산, max_pages 슬라이더 제거
- 허그/대항력 포기 → 탱크옥션 검색 폼 파라미터로 직접 전달
  - 파라미터명 확인 필요: 탱크옥션 검색 시 Network 탭 > AuctList.php 요청 파라미터 확인
- 개편 후 코드 구조:
  ```python
  # 조건 1회 설정
  await set_search_conditions(sicd, gucd, ctgr, max_wan, hug_filter)
  # 1페이지 실행 후 totalCnt 확인
  total_pages = ceil(total / page_size)
  # 나머지 페이지: srchList(page_no)만 호출
  for page_no in range(2, total_pages + 1):
      await page.evaluate(f"srchList({page_no})")
  ```

#### 2. 방/화장실 개수 검색결과 표기
**문제:**
- 목록 API는 방 개수를 제공하지 않음
- 주소 텍스트 파싱도 탱크옥션엔 안 됨 → 전부 `-`

**해결 방향:**
- 검색 완료 후 "상세 일괄 조회" 버튼 추가
- 각 물건 상세 HTML(`caView.php`) 조회 (PDF 없이) → `lyCnt_object` 텍스트 파싱
- 그래도 없으면 상세분석 시 Vision AI(PDF)로 확인
- 배치 병렬 처리로 속도 개선 필요

### 🟡 확인 필요

#### 3. API 실제 필드명 확인 (디버그 출력 활용)
검색 실행 시 터미널에 `[DEBUG] API 필드: [...]` 출력됨.
다음 필드명 실제 존재 여부 확인:
- `flrNo`, `totFlrCnt` → 층 정보
- `bldgYear`, `useAprYear` → 건물 연식
- `elvtrYn` → 엘베 유무
- `roomCnt`, `bathCnt` → 방/화장실 수
- `bldgAr`, `lndAr` → 건물면적, 대지면적

#### 4. 부동산플래닛 API 필드명 확인
실거래 API 응답에서 실제 필드명 확인:
- `r_type_nm` → 건물종류 (다세대주택/연립주택)
- `bldg_area_m2` vs `supply_area_m2` → 어떤 면적인지 (전용/공급)

---

## 현재 구현 완료

### 검색결과 목록 컬럼
`사건번호 | 지역 | 종류 | 주소 | 층 | 연식 | 엘베 | 방/욕 | 건물㎡ | 대지㎡ | 감정가 | 최저가 | 최저가율% | 상태 | 매각기일 | 특수조건`

- 층: API 필드 → 주소 파싱 fallback
- 연식: API 필드 → 주소/비고 텍스트 파싱
- 엘베: API 필드 → 총층수 기반 추정 (5층↑ 있음, 4층↓ 없음)
- 방/욕: API 필드 → 주소 파싱 → 상세분석 후 Vision AI 결과로 업데이트

### 선택 물건 간략 정보 (상세분석 전)
물건 선택 시 `감정가 | 최저가(%) | 층 | 건물면적 | 상태` 5개 박스 표시

### 상세분석 결과 (HTML 테이블 형식)
기본정보 + 건물정보 + 주변환경을 12px 소형 HTML 테이블로 통합 표시
- 기본정보: 감정가, 최저매각가, 보증금, 인수금, 매각기일, 상태, 주소, 사건번호, (특수조건)
- 건물정보: 건물면적, 대지면적, 연식, 엘베, 방/화장실, 층
- 주변환경: 지하철, 편의점, 초등학교

### 부동산플래닛 실거래
- 동일 건물종류 필터 (다세대→다세대주택, 연립→연립주택, 빌라→다세대+연립)
- 면적 ±25% 필터
- 반경 500m 이내
- 최근 2년, 최대 8건

### 권리분석
- 선순위임차인 인수금 자동 계산
- 허그 인수조건 포기 / 대항력 포기 태그 표시

---

## 투자 기준 (참고용)
- 지역: 인천, 안산, 고양, 경기도 광주
- 물건: 다세대/연립/빌라
- 감정가 상한: 2억 이하
- 엘베 없는 2~4층 우선 (신축이면 2층부터)
- 방 3개 선호
- 전략: 경매 낙찰 → 시장가 매도
