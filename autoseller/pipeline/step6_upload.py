"""
Step 6: 전 플랫폼 동시 업로드
- 현재: 쿠팡만 지원 (추후 스마트스토어 등 추가)
- 실행: python pipeline/step6_upload.py

config 필수 키:
    coupang_access_key  str
    coupang_secret_key  str
    coupang_vendor_id   str
"""

from uploader import coupang


def run(products: list, config: dict) -> list:
    """
    step5 통과 상품을 플랫폼에 업로드.

    Returns:
        list[dict]: 업로드 결과 포함 상품 목록
    """
    print(f"[step6] 업로드 대상: {len(products)}개")
    results = coupang.run(products, config)
    success = [r for r in results if r.get("success")]
    print(f"[step6] 완료: {len(success)}/{len(products)}개 성공")
    return results
