"""
내부구조도 Vision AI 분석
Claude API로 floor plan 이미지에서 방/화장실/엘베 정보 추출
"""
import anthropic
import base64
import httpx
from typing import Dict


def analyze_floor_plan(image_url: str, cookies: Dict[str, str]) -> Dict:
    """
    내부구조도 이미지를 Claude Vision으로 분석
    Returns: {"room_count": int, "bathroom_count": int, "has_elevator": str}
    """
    result = {"room_count": 0, "bathroom_count": 0, "has_elevator": "미확인"}

    try:
        # 인증된 세션으로 이미지 다운로드
        cookie_str = "; ".join(f"{k}={v}" for k, v in cookies.items())
        headers = {
            "Cookie": cookie_str,
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Referer": "https://www.tankauction.com/",
        }

        # caFile.php 페이지에서 실제 이미지 URL 찾기
        resp = httpx.get(image_url, headers=headers, follow_redirects=True, timeout=30)
        resp.raise_for_status()

        content_type = resp.headers.get("content-type", "")
        if "html" in content_type:
            # HTML 페이지인 경우 → 내부 img src 추출
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(resp.text, "lxml")
            img = soup.find("img")
            if not img:
                return result
            src = img.get("src", "")
            if src.startswith("/"):
                src = "https://www.tankauction.com" + src
            img_resp = httpx.get(src, headers=headers, follow_redirects=True, timeout=30)
            img_resp.raise_for_status()
            image_data = img_resp.content
            media_type = img_resp.headers.get("content-type", "image/jpeg").split(";")[0]
        else:
            # 직접 이미지
            image_data = resp.content
            media_type = content_type.split(";")[0] or "image/jpeg"

        if not image_data:
            return result

        img_b64 = base64.standard_b64encode(image_data).decode("utf-8")

        client = anthropic.Anthropic()
        message = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=300,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": img_b64,
                            },
                        },
                        {
                            "type": "text",
                            "text": (
                                "이 건물 내부구조도(평면도)를 보고 다음 정보를 JSON으로 답해주세요:\n"
                                "1. room_count: 방(침실) 개수 (숫자만)\n"
                                "2. bathroom_count: 화장실/욕실 개수 (숫자만)\n"
                                "3. has_elevator: 엘리베이터 유무 (있음/없음/미확인)\n\n"
                                "반드시 JSON 형식으로만 답하세요. 예: {\"room_count\": 3, \"bathroom_count\": 1, \"has_elevator\": \"없음\"}"
                            ),
                        },
                    ],
                }
            ],
        )

        text = message.content[0].text.strip()
        import json, re
        json_match = re.search(r"\{[^}]+\}", text)
        if json_match:
            parsed = json.loads(json_match.group())
            result["room_count"] = int(parsed.get("room_count", 0))
            result["bathroom_count"] = int(parsed.get("bathroom_count", 0))
            result["has_elevator"] = str(parsed.get("has_elevator", "미확인"))

    except Exception as e:
        print(f"[WARN] Vision 분석 실패: {e}")

    return result
