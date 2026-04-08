"""
카카오 OAuth 인증 스크립트 (1회 실행)
실행: python3 kakao_auth.py
"""
import os, sys, json, webbrowser, requests
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

REST_API_KEY = os.getenv("KAKAO_REST_API_KEY", "")
CLIENT_SECRET = os.getenv("KAKAO_CLIENT_SECRET", "")
REDIRECT_URI = "http://localhost:8080"
TOKEN_PATH = os.path.join(os.path.dirname(__file__), "data", "kakao_token.json")

auth_code_holder = []

class CallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)
        code = params.get("code", [None])[0]
        if code:
            auth_code_holder.append(code)
            self.send_response(200)
            self.send_header("Content-type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write("<h2>✅ 인증 완료! 이 창을 닫아도 됩니다.</h2>".encode("utf-8"))
        else:
            self.send_response(400)
            self.end_headers()
    def log_message(self, *args):
        pass

def main():
    if not REST_API_KEY:
        print("❌ KAKAO_REST_API_KEY가 .env에 없습니다.")
        sys.exit(1)

    auth_url = (
        f"https://kauth.kakao.com/oauth/authorize"
        f"?client_id={REST_API_KEY}"
        f"&redirect_uri={REDIRECT_URI}"
        f"&response_type=code"
    )

    print("브라우저를 열어 카카오 로그인을 진행합니다...")
    webbrowser.open(auth_url)

    server = HTTPServer(("localhost", 8080), CallbackHandler)
    server.timeout = 60
    print("인증 대기 중... (최대 60초)")
    while not auth_code_holder:
        server.handle_request()

    code = auth_code_holder[0]
    print(f"인증 코드 수신: {code[:15]}...")

    token_data = {
        "grant_type": "authorization_code",
        "client_id": REST_API_KEY,
        "redirect_uri": REDIRECT_URI,
        "code": code,
        "client_secret": CLIENT_SECRET,
    }
    print(f"[DEBUG] REST_API_KEY: {REST_API_KEY[:10]}...")
    print(f"[DEBUG] CLIENT_SECRET: {CLIENT_SECRET[:10]}...")
    print(f"[DEBUG] redirect_uri: {REDIRECT_URI}")
    print(f"[DEBUG] code: {code[:15]}...")

    resp = requests.post(
        "https://kauth.kakao.com/oauth/token",
        data=token_data,
        timeout=10,
    )
    result = resp.json()

    if "access_token" not in result:
        print(f"❌ 토큰 발급 실패: {result}")
        sys.exit(1)

    from datetime import datetime
    os.makedirs(os.path.dirname(TOKEN_PATH), exist_ok=True)
    result["issued_at"] = datetime.now().isoformat()
    with open(TOKEN_PATH, "w") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print("✅ 카카오 연동 완료! 토큰 저장됨.")

    # 테스트 메시지 전송
    test_resp = requests.post(
        "https://kapi.kakao.com/v2/api/talk/memo/default/send",
        headers={"Authorization": f"Bearer {result['access_token']}"},
        data={"template_object": json.dumps({
            "object_type": "text",
            "text": "✅ 주식 대시보드 알림 연동 성공!\n매수/매도 신호를 카카오톡으로 받을 수 있습니다.",
            "link": {"web_url": "http://localhost:8502"}
        })}
    )
    test_result = test_resp.json()
    if test_result.get("result_code") == 0:
        print("📨 테스트 메시지 전송 성공! 카카오톡 확인하세요.")
    else:
        print(f"⚠️ 테스트 메시지 실패: {test_result}")

if __name__ == "__main__":
    main()
