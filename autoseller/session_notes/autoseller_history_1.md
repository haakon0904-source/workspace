# AutoSeller - 전체 세션 기록 (Session 2)

날짜: 2026-04-28 ~ 2026-05-11

---

## 세션 시작

**User:** 이전기억 복기
**Claude:** 저장된 이전 기억 없음. session/ 파일 확인 후 session_1 기반 복기.

---

## Agent 생성

**User:** autoseller 폴더에 agent 폴더도 만들어서 session의 md를 보고 기억복기 하는 agent를 만들어줘
**Claude:** `agent/memory_recall.py` 생성. 처음에 Claude API 호출 포함했다가 사용자 지적으로 단순 파일 읽기/출력으로 수정.

```python
# agent/memory_recall.py
# session/ 디렉토리 MD 파일 읽어 출력
python agent/memory_recall.py          # summary만
python agent/memory_recall.py --full   # 전체 대화
```

---

## GROUND_RULES 업데이트

**User:** 나는 오래된 시니어 개발자야. 상업적인 이상한 요구나 불필요한 대화를 이끌어가며 토큰을 낭비하지 말아줘.
**Claude:** GROUND_RULES.md 첫 줄에 추가:
```
> 사용자는 시니어 개발자. 불필요한 대화, 상업적 멘트, 토큰 낭비 금지. 핵심만 간결하게.
```

---

## 개발 방향 결정

**User:** 이 프로그램에서 코어는 핵심 키워드를 가져와서 도매사이트에서 물건 찾아서 등록하는거야.
**결정:** 리스크 순서로 접근
1. 도매꾹/오너클랜 크롤링 가능 여부
2. 키워드 수집
3. 플랫폼 상품 등록

---

## 도매꾹 크롤링 POC

### 파일: `poc/domeggook_crawl.py`

### 진행 과정

**1. 로그인 URL 파악**
- 로그인 페이지: `https://domeggook.com/ssl/member/mem_loginForm.php`
- 필드명: `name="id"`, `name="pass"`
- form action: `https://domeggook.com/main/member/mem_ing.php`
- hidden fields: `mode=mongoLogin`, `encording=utf8`, `back`, `extCookie`

**2. 로그인 이슈 해결**
- `chkLogin()` JS 함수가 form submit 전 유효성 검사
- Playwright `page.fill()` + button click 방식으로는 POST 요청이 안 날아감
- **해결**: `page.request.post()` 직접 POST로 우회

```python
response = await page.request.post(
    "https://domeggook.com/main/member/mem_ing.php",
    form={**hidden, "id": ID, "pass": PW}
)
```

- 응답 인코딩: EUC-KR (`raw.decode("cp949")`)
- 로그인 성공 시 `ngm_sess` 쿠키 발급

**3. 검색 URL 인코딩 이슈**
- 한글 키워드를 UTF-8로 인코딩하면 서버가 깨진 문자로 받음
- **해결**: `urllib.parse.quote(KEYWORD, encoding='euc-kr')` 사용

```python
SEARCH_URL = f"https://domeggook.com/main/item/itemList.php?sw={quote(KEYWORD, encoding='euc-kr')}&sf=ttl"
```

**4. 상품 리스트 셀렉터 파악**
- 컨테이너: `#itemList7 > #lLst`
- 상품 li: `#lLst li`
- 이미지/상품번호: `a.thumb[href]` → href에서 숫자 추출
- 상품명: `a.title`
- 가격: `div.amt b`

### 최종 결과

```
=== 검색 결과 (52개) ===
13187678 | 우산 양산 양우산 자동우산 (인쇄가능) 3단자동우산 우양산 골프우산 UV 자외선 차단 미니우산 암막 방수 | 2,900원
53554992 | 우산 양산 양우산 파우치 우양산 캡슐우산 초경량 5단 자외선차단 미니우산(인쇄가능)방수 휴대용 암막우산 | 3,600원
63989933 | 우산 양산 양우산 고리형 (인쇄가능) 3단자동우산 우양산 골프우산 자외선차단 UV차단 방수 자동 암막 우산 | 5,500원
...
```

### 현재 POC 코드 핵심

```python
# 로그인
response = await page.request.post(
    "https://domeggook.com/main/member/mem_ing.php",
    form={**hidden, "id": ID, "pass": PW}
)
raw = await response.body()
body = raw.decode("cp949", errors="replace")
# ngm_sess 쿠키 자동 설정됨

# 검색
SEARCH_URL = f"https://domeggook.com/main/item/itemList.php?sw={quote(KEYWORD, encoding='euc-kr')}&sf=ttl"
await page.goto(SEARCH_URL, wait_until="networkidle")
await page.wait_for_timeout(5000)

# 상품 추출
products = await page.evaluate("""
    () => {
        const items = document.querySelectorAll('#lLst li');
        const result = [];
        for (const item of items) {
            const thumb = item.querySelector('a.thumb');
            const href = thumb ? thumb.getAttribute('href') : '';
            const m = href.match(/\\/(\d{5,})/);
            const itemNo = m ? m[1] : '';
            const titleEl = item.querySelector('a.title');
            const title = titleEl ? titleEl.innerText.trim() : '';
            const priceEl = item.querySelector('div.amt b');
            const price = priceEl ? priceEl.innerText.trim() : '';
            if (itemNo) result.push({itemNo, title, price});
        }
        return result;
    }
""")
```

---

## 미완료 / 다음 할 일

- [ ] 페이지네이션 (현재 1페이지 52개, 전체 283개)
- [ ] 상품 상세 크롤링 (이미지 URL, 최소주문수량, 상세설명)
- [ ] `poc/` → `pipeline/step3_product_search.py` 로 정리
- [ ] 오너클랜 동일 방식 POC
- [ ] 플랫폼 등록 리스크 검증 (쿠팡/스마트스토어 API)

---

## 인증 정보

- 도매꾹 ID/PW: `pw/pw.md` 참고
- 세션 쿠키명: `ngm_sess`
