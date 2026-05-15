# AutoSeller - 요약 써머리 Session 2

날짜: 2026-04-26

---

## 이번 세션에서 한 것

- session 1 기반 기억 복기
- agent/memory_recall.py 생성 (session MD 읽어 컨텍스트 출력, API 불필요)
- GROUND_RULES.md 첫 줄에 사용자 원칙 추가
- 메모리 저장: user_profile, project_autoseller, feedback 2개

## 개발 방향 결정

- **접근법**: 마진계산 같은 내부 로직 먼저 X → 외부 의존성/실현 가능성 먼저 검증
- **코어 정의**: 키워드 수집 → 도매사이트 상품 서치 → 플랫폼 등록
- **리스크 순서**:
  1. 도매꾹/오너클랜 크롤링 가능 여부
  2. 키워드 수집 (네이버 데이터랩, 쿠팡)
  3. 쿠팡/스마트스토어 상품 등록 API

## 다음 할 일

- 셀러 계정 유무 확인
- 도매꾹 Playwright 크롤링 POC (로그인 없이 상품 목록/상세 접근 가능한지)

## 미확인 사항 (session 1에서 이월)

- [ ] 쿠팡/스마트스토어 셀러 계정
- [ ] Claude API 키
- [ ] Twitter 개발자 계정
- [ ] 태사자 프로그램 상세 분석
- [ ] 각 플랫폼 API 승인 절차
