"""
Step 1: 네이버 쇼핑 인사이트로 트렌딩 키워드 발굴
- 실제 쇼핑 검색량 기반 (일반 검색 트렌드가 아닌 구매 의도 트렌드)
- 시드 키워드 목록 → 쇼핑 인사이트 API → 상승세 키워드 추출

config 필수 키:
    naver_client_id      str
    naver_client_secret  str
    trend_top_n          int   상위 몇 개 키워드 사용 (기본 10)
    trend_weeks          int   비교 기간 (기본 4주)

동작 원리:
    시드 키워드 → 쇼핑 인사이트 API (주간 쇼핑 검색량 추이) →
    최근 N주 평균 vs 이전 N주 평균 비교 → 상승률 정렬 → 상위 키워드 반환

API 발급:
    developers.naver.com → 애플리케이션 등록
    → 사용 API: 데이터랩(쇼핑인사이트) 선택 (일반 데이터랩과 별도)
"""

import requests
from datetime import datetime, timedelta


SHOPPING_INSIGHT_URL = "https://openapi.naver.com/v1/datalab/shopping/category/keywords"

# 네이버 쇼핑 카테고리 코드
# 참고: https://developers.naver.com/docs/datalab/shopping
NAVER_SHOPPING_CATEGORIES = {
    "패션의류":    "50000000",
    "패션잡화":    "50000001",
    "화장품/미용": "50000002",
    "디지털/가전": "50000003",
    "가구/인테리어":"50000004",
    "출산/육아":   "50000005",
    "식품":        "50000006",
    "스포츠/레저": "50000007",
    "생활/건강":   "50000008",
    "여가/생활편의":"50000009",
}

# 카테고리별 시드 키워드 (각 카테고리에서 탐색할 키워드 목록)
SEED_KEYWORDS = {
    "패션잡화": {
        "category": "50000001",
        "keywords": ["우산", "모자", "선글라스", "벨트", "지갑", "파우치", "백팩", "목도리", "장갑"],
    },
    "생활/건강": {
        "category": "50000008",
        "keywords": ["텀블러", "무릎보호대", "목베개", "안마기", "족욕기", "칫솔", "면도기", "헤어드라이어"],
    },
    "디지털/가전": {
        "category": "50000003",
        "keywords": ["보조배터리", "무선충전기", "이어폰", "케이블", "스마트워치", "손선풍기"],
    },
    "스포츠/레저": {
        "category": "50000007",
        "keywords": ["캠핑의자", "접이식테이블", "등산스틱", "물통", "아이스박스"],
    },
    "여가/생활편의": {
        "category": "50000009",
        "keywords": ["방수팩", "여행파우치", "목베개", "여행용품"],
    },
}


def _date_range(weeks_back: int, duration_weeks: int) -> tuple[str, str]:
    end = datetime.now() - timedelta(weeks=weeks_back)
    start = end - timedelta(weeks=duration_weeks)
    return start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")


def _query_shopping_insight(category_code: str, keywords: list[str],
                             start: str, end: str, config: dict) -> dict:
    """
    쇼핑 인사이트 API 호출 (한 번에 최대 5개 키워드).
    Returns: {keyword: avg_ratio}
    """
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
        "device": "",
        "gender": "",
        "ages": [],
    }
    resp = requests.post(SHOPPING_INSIGHT_URL, headers=headers, json=body, timeout=15)
    if resp.status_code != 200:
        raise RuntimeError(f"쇼핑 인사이트 API 오류: {resp.status_code} {resp.text[:200]}")

    result = {}
    for item in resp.json().get("results", []):
        name = item["title"]
        ratios = [d["ratio"] for d in item.get("data", [])]
        result[name] = sum(ratios) / len(ratios) if ratios else 0
    return result


def _chunk_list(lst: list, size: int):
    for i in range(0, len(lst), size):
        yield lst[i:i + size]


def run(config: dict, seed_keywords: dict = None) -> list[str]:
    """
    쇼핑 인사이트 기반 트렌딩 키워드 발굴.

    Returns:
        list[str]: 상승세 상위 키워드 목록
    """
    seeds = seed_keywords or SEED_KEYWORDS
    top_n = config.get("trend_top_n", 10)
    weeks = config.get("trend_weeks", 4)

    recent_start, recent_end = _date_range(0, weeks)
    prev_start, prev_end = _date_range(weeks, weeks)

    total_keywords = sum(len(v["keywords"]) for v in seeds.values())
    print(f"[step1] 쇼핑 인사이트 분석: {len(seeds)}개 카테고리, {total_keywords}개 키워드")
    print(f"        최근: {recent_start} ~ {recent_end}")
    print(f"        이전: {prev_start} ~ {prev_end}")

    recent_ratios = {}
    prev_ratios = {}

    for cat_name, info in seeds.items():
        cat_code = info["category"]
        kws = info["keywords"]
        # API 한 번에 최대 5개
        for chunk in _chunk_list(kws, 5):
            try:
                recent_ratios.update(_query_shopping_insight(cat_code, chunk, recent_start, recent_end, config))
                prev_ratios.update(_query_shopping_insight(cat_code, chunk, prev_start, prev_end, config))
            except RuntimeError as e:
                print(f"[step1] 경고 ({cat_name}): {e}")

    # 상승률 계산
    scores = {}
    for kw in recent_ratios:
        prev = prev_ratios.get(kw, 0)
        recent = recent_ratios.get(kw, 0)
        if prev > 0:
            scores[kw] = (recent - prev) / prev
        else:
            scores[kw] = recent

    sorted_kws = sorted(scores.items(), key=lambda x: x[1], reverse=True)

    print(f"\n[step1] 쇼핑 검색 트렌드 순위 (상위 {top_n}개):")
    for i, (kw, score) in enumerate(sorted_kws[:top_n], 1):
        recent = recent_ratios.get(kw, 0)
        arrow = "▲" if score > 0.05 else ("▼" if score < -0.05 else "─")
        print(f"  {i:2}. {kw:<15} 쇼핑검색비율 {recent:5.1f}  {arrow} {score:+.1%}")

    top_keywords = [kw for kw, _ in sorted_kws[:top_n]]
    print(f"\n[step1] 선정: {top_keywords}")
    return top_keywords


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent.parent))
    from run_pipeline import CONFIG

    keywords = run(CONFIG)
