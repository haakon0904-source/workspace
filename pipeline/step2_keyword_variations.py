"""
Step 2: 트렌딩 키워드 → 변형어 생성 + 쇼핑 인사이트 검증
- 수식어 조합으로 롱테일 키워드 후보 생성
- 네이버 쇼핑 인사이트로 실제 검색량 있는 것만 필터링
- 경쟁 희박한 세부 키워드 추출

config 필수 키:
    naver_client_id      str
    naver_client_secret  str
    variation_min_ratio  float  최소 쇼핑 검색 비율 (기본 1.0)
    variation_top_n      int    키워드당 최대 변형어 수 (기본 5)
"""

import requests
from datetime import datetime, timedelta
from itertools import product as iproduct


# 키워드 앞에 붙이는 수식어
PREFIX_MODIFIERS = [
    "휴대용", "미니", "소형", "대형", "접이식", "충전식",
    "USB", "무선", "목걸이형", "핸즈프리", "야외용",
    "캠핑용", "여행용", "사무용", "업무용", "등산용",
    "방수", "초경량", "저소음", "고출력",
]

# 키워드 뒤에 붙이는 수식어
SUFFIX_MODIFIERS = [
    "추천", "세트", "선물", "1+1", "2개입",
    "남성용", "여성용", "어린이", "유아용",
    "국산", "정품", "고급",
]

# 카테고리별 특화 수식어
CATEGORY_MODIFIERS = {
    "손선풍기":  (["목걸이형", "USB", "휴대용", "미니", "핸즈프리", "3단계속도"], []),
    "캠핑의자":  (["경량", "접이식", "컴팩트", "등받이", "팔걸이"], []),
    "아이스박스": (["소형", "대용량", "낚시용", "캠핑용", "보냉"], []),
    "텀블러":    (["진공", "스텐", "보온보냉", "대용량", "원터치"], []),
    "우산":      (["3단", "5단", "자동", "경량", "암막", "UV차단"], []),
    "면도기":    (["전동", "방수", "무선", "건습식", "휴대용"], []),
    "모자":      (["버킷햇", "볼캡", "챙모자", "자외선차단", "골프용"], []),
    "백팩":      (["방수", "경량", "노트북", "등산", "대용량"], []),
}

SHOPPING_INSIGHT_URL = "https://openapi.naver.com/v1/datalab/shopping/category/keywords"

# 키워드 → 네이버 쇼핑 카테고리 코드
KEYWORD_CATEGORY_MAP = {
    "손선풍기":  "50000003",  # 디지털/가전
    "캠핑의자":  "50000007",  # 스포츠/레저
    "아이스박스": "50000007",
    "텀블러":    "50000008",  # 생활/건강
    "면도기":    "50000008",
    "족욕기":    "50000008",
    "목베개":    "50000009",
    "방수팩":    "50000009",
    "우산":      "50000001",  # 패션잡화
    "모자":      "50000001",
    "선글라스":  "50000001",
    "백팩":      "50000001",
}
DEFAULT_CATEGORY = "50000008"


def _generate_candidates(keyword: str) -> list[str]:
    """수식어 조합으로 변형어 후보 생성."""
    candidates = set()

    # 카테고리 특화 수식어 우선 적용
    if keyword in CATEGORY_MODIFIERS:
        prefixes, suffixes = CATEGORY_MODIFIERS[keyword]
        for p in prefixes:
            candidates.add(f"{p} {keyword}")
            candidates.add(f"{p}{keyword}")
        for s in suffixes:
            candidates.add(f"{keyword} {s}")
    else:
        # 일반 수식어 조합
        for p in PREFIX_MODIFIERS[:10]:
            candidates.add(f"{p} {keyword}")
        for s in SUFFIX_MODIFIERS[:5]:
            candidates.add(f"{keyword} {s}")

    return list(candidates)


def _query_insight(category_code: str, keywords: list[str],
                   start: str, end: str, config: dict) -> dict:
    """쇼핑 인사이트 API로 검색량 조회. {keyword: avg_ratio}"""
    headers = {
        "X-Naver-Client-Id": config["naver_client_id"],
        "X-Naver-Client-Secret": config["naver_client_secret"],
        "Content-Type": "application/json",
    }
    body = {
        "startDate": start,
        "endDate": end,
        "timeUnit": "week",
        "category": category_code,
        "keyword": [{"name": kw, "param": [kw]} for kw in keywords],
        "device": "", "gender": "", "ages": [],
    }
    resp = requests.post(SHOPPING_INSIGHT_URL, headers=headers, json=body, timeout=15)
    if resp.status_code != 200:
        return {}
    result = {}
    for item in resp.json().get("results", []):
        ratios = [d["ratio"] for d in item.get("data", [])]
        result[item["title"]] = sum(ratios) / len(ratios) if ratios else 0
    return result


def _chunk(lst, size):
    for i in range(0, len(lst), size):
        yield lst[i:i + size]


def run(keywords: list[str], config: dict) -> list[str]:
    """
    트렌딩 키워드 → 변형어 생성 + 검색량 검증.

    Returns:
        list[str]: 원본 키워드 + 검증된 변형어 (검색량 높은 순)
    """
    min_ratio = config.get("variation_min_ratio", 1.0)
    top_n = config.get("variation_top_n", 5)

    end = datetime.now().strftime("%Y-%m-%d")
    start = (datetime.now() - __import__("datetime").timedelta(weeks=4)).strftime("%Y-%m-%d")

    result = []
    all_variations = {}

    for kw in keywords:
        candidates = _generate_candidates(kw)
        cat_code = KEYWORD_CATEGORY_MAP.get(kw, DEFAULT_CATEGORY)

        print(f"[step2] '{kw}' 변형어 {len(candidates)}개 검색량 검증 중...")
        ratios = {}
        for chunk in _chunk(candidates, 5):
            ratios.update(_query_insight(cat_code, chunk, start, end, config))

        # 최소 검색량 이상인 변형어만 선택
        valid = [(v, r) for v, r in ratios.items() if r >= min_ratio]
        valid.sort(key=lambda x: x[1], reverse=True)

        picked = [v for v, _ in valid[:top_n]]
        result.append(kw)         # 원본 키워드 포함
        result.extend(picked)

        print(f"         → 통과: {picked if picked else '없음 (원본만 사용)'}")

    # 중복 제거 (순서 유지)
    seen = set()
    deduped = []
    for kw in result:
        if kw not in seen:
            seen.add(kw)
            deduped.append(kw)

    print(f"\n[step2] 최종 키워드 {len(deduped)}개: {deduped}")
    return deduped


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent.parent))
    from run_pipeline import CONFIG

    test_keywords = ["손선풍기", "캠핑의자"]
    result = run(test_keywords, CONFIG)
    print(f"\n결과: {result}")
