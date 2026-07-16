# App in Toss (앱인토스) 미니앱 런칭

토스 앱 내에서 구동되는 **미니앱**을 개발하고 런칭하기 위한 문서와 자료를 모아둔 폴더입니다.

## 이 폴더에 있는 문서

| 파일 | 설명 |
|------|------|
| `ai-vibe-coding.md` | AI(Claude Code)와 함께 앱인토스 미니앱을 처음부터 끝까지 만드는 공식 튜토리얼 |
| `release-note.md` | 앱인토스 제품·API·SDK의 새로운 기능과 변경 사항(릴리즈 노트) |
| `README.md` | 이 파일 — 개발/런칭 워크플로우 요약 |

## 개발 워크플로우 한눈에 보기

```
[환경 준비]                [프로젝트]                 [출시]
Node.js + VS Code          create-ait-app {appName}    npm run build → .ait 파일
Claude Code        →       granite.config.ts 설정  →   콘솔 업로드 → 검토 요청
ax (MCP/CLI)               기능 개발 (React+TS+TDS)     토스 앱에 출시
```

### 1. 환경 준비

```bash
# ax (앱인토스 공식 MCP/CLI 툴킷)
brew tap toss/tap && brew install ax

# Claude Code에 앱인토스 MCP 연결 (문서/SDK 자동 참조)
claude mcp add --transport stdio apps-in-toss ax mcp start

# (선택) 콘솔 작업용 MCP — 워크스페이스/검수/결제/광고를 AI로 직접 제어 (Claude만 지원)
claude mcp add --transport http apps-in-toss-console \
  https://mcp.toss.im/adapters/apps-in-toss-console/mcp \
  --client-id mcp-gateway
```

### 2. 프로젝트 생성 & 설정

```bash
# {appName}은 개발자센터 콘솔에 등록한 이름 기준
npx create-ait-app {appName}
```

추천 옵션: `npm` / `react-ts (React + TypeScript)` / TDS 사용(Y) / 인앱 결제·인앱 광고 예제 추가

앱 정보는 `granite.config.ts`에서 설정합니다(`appName`, `brand.displayName`, `brand.primaryColor`, `brand.icon`).

### 3. 빌드 & 출시

```bash
npm run build          # dist/ 에 .ait 파일 생성
# 콘솔 '앱 출시' 메뉴에 .ait 파일 업로드 → 테스트 → 검토 요청 → 출시
```

## 핵심 포인트

- **기술 스택**: React + TypeScript + Vite + **TDS(Toss Design System)**
- **가장 큰 장점 — 트래픽**: 활성 지표(핵심 지표)를 설정하면 토스가 비슷한 사용자를 찾아 자동으로 미니앱을 노출·추천
- **수익화**:
  - 인앱 광고 2.0 (토스애즈 + 구글 애드몹 통합, SDK 1개 연동) — 전면/보상형/배너
  - 인앱 결제 / 구독결제 (무료체험·할인 설정)
  - 토스페이 정기결제(자동결제) — 구독·멤버십·정기배송
- **온보딩 간소화**: 사용자 정보 기능 — 토스에 저장된 정보를 동의 후 즉시 불러오기 (서버 불필요, SDK만)
- **외부 연동**: Firebase, Supabase, Sentry

## 시작 전 체크리스트

- [ ] [앱인토스 오픈 정책](https://developers-apps-in-toss.toss.im/intro/guide.html) 확인
- [ ] 개발자센터 콘솔에서 앱 등록 (앱 이름, `appName`, 앱 유형 3가지면 충분)
- [ ] `ax` 설치 및 Claude Code MCP 연결
- [ ] [비게임 출시 가이드](https://developers-apps-in-toss.toss.im/checklist/app-nongame.html) / [게임 출시 가이드](https://developers-apps-in-toss.toss.im/checklist/app-game.html) 확인

## 참고 문서

- [AI와 함께 미니앱 만들기 (튜토리얼)](https://developers-apps-in-toss.toss.im/tutorials/ai-vibe-coding.html)
- [릴리즈 노트](https://developers-apps-in-toss.toss.im/release-note.html)
- [LLM용 전체 문서](https://developers-apps-in-toss.toss.im/llms-full.txt)
- [마케팅 가이드](https://developers-apps-in-toss.toss.im/marketing/overview.html)
- [ax 툴킷 (GitHub)](https://github.com/toss/apps-in-toss-ax)
