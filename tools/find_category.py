"""
쿠팡 카테고리 정보 및 수수료율 확인 도구

카테고리 코드 찾는 법:
  WING > 상품관리 > 상품등록 > 카테고리 검색 후 선택
  → 개발자도구 Network 탭에서 displayCategoryCode 확인

실행: python3 tools/find_category.py 69884
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from run_pipeline import CONFIG
from uploader.coupang import _request


def get_category_info(code: int):
    path = f"/v2/providers/seller_api/apis/api/v1/marketplace/meta/category-related-metas/display-categories/{code}"
    resp = _request("GET", path, CONFIG)
    data = resp.json()

    if data.get("code") != "SUCCESS":
        print(f"오류: {data.get('message')}")
        return

    d = data.get("data", {})
    rate = d.get("commissionRate")
    name = d.get("displayCategoryName", "")
    print(f"\n카테고리 코드 : {code}")
    print(f"카테고리명    : {name}")
    print(f"수수료율      : {rate}%")


if __name__ == "__main__":
    code = int(sys.argv[1]) if len(sys.argv) > 1 else int(input("카테고리 코드: "))
    get_category_info(code)
