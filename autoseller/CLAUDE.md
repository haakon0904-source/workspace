# AutoSeller - Claude 지시사항

## 보안 규칙 (최우선)
- `pw/pw.md` 에서 읽은 ID, 비밀번호, API 키 등 인증 정보를 절대 Claude 응답 텍스트에 노출하지 않는다.
- 코드 내 인증 정보는 환경변수 또는 `pw/pw.md` 참조로만 처리한다.
- 로그/출력에도 인증 정보가 포함되지 않도록 한다.

## 사용자
시니어 개발자. 불필요한 대화, 상업적 멘트, 토큰 낭비 금지. 핵심만 간결하게.

## "오토셀러 기억복기" 명령
이 명령을 받으면 아래 순서로 파일을 읽고 컨텍스트를 복원한다:

1. `session_notes/` 디렉토리의 모든 `autoseller_history_N.md` 파일 (번호 순)
2. `session/` 디렉토리의 `auto_seller_summary_session_N.md` 파일 (번호 순)
3. `GROUND_RULES.md`

복기 후 출력 형식:
- 프로젝트 현황 (완료된 것 / 미완료)
- 다음 할 일 (우선순위 순)
- 미확인 사항

## 프로젝트 위치
`/Users/parkyongjin/Workspace/AutoSeller`
