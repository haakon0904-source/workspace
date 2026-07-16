---
url: 'https://developers-apps-in-toss.toss.im/tutorials/ai-vibe-coding.md'
description: 코드를 잘 몰라도 괜찮아요. AI와 함께 앱인토스 미니앱을 처음부터 끝까지 만드는 방법을 안내해요.
---

# 미니앱 만들기

코딩 경험이 없어도 괜찮아요. AI와 함께라면 앱인토스 미니앱을 처음부터 끝까지 만들 수 있어요.\
이 문서는 Claude Code, Cursor, Codex 등 AI 도구를 활용해 미니앱을 개발하는 전체 과정을 안내해요.

::: tip 이런 분께 도움이 돼요

* 코딩을 전혀 해본 적 없는 분
* 앱 아이디어는 있지만 만드는 방법을 모르는 분
* AI로 빠르게 미니앱을 만들어 보고 싶은 분
  :::

이미 웹 프로젝트가 있다면 [기존 Web 프로젝트 개발 가이드](../tutorials/webview.html)를,\
React Native로 개발하고 싶다면 [React Native 개발 가이드](../tutorials/react-native)를 참고해 주세요.

***

## 1. 준비하기

앱을 만들기 전에 딱 3가지만 준비하면 돼요.

### 1-1. 앱인토스 오픈 정책 확인하기

[앱인토스 오픈 정책](/intro/guide.html)을 반드시 확인해 주세요.\
정책을 지키지 않으면 앱이 승인되지 않거나 나중에 사용할 수 없게 될 수 있어요.

### 1-2. Node.js 설치하기

Node.js는 AI 도구(Claude Code, Codex 등)를 설치하고 실행하는 데 필요한 프로그램이에요.\
[Node.js 공식 사이트](https://nodejs.org/)에서 다운로드해서 설치해 주세요.

![](/assets/install_node_1.DyB5MNik.webp)

![](/assets/install_node_2.CzmHIIMd.webp)

윈도우 환경에서는 드롭다운에서 Windows를 선택해 주세요.

![](/assets/install_node_3.DhnYEvZ3.webp)

![](/assets/install_node_4.BR4EujRi.webp)

설치가 끝나면 터미널에서 아래 명령어를 입력해 보세요. 버전 숫자가 표시되면 정상적으로 설치된 거예요.

:::details 터미널이란
터미널은 컴퓨터에게 글로 명령을 내리는 창이에요.
AI 도구도 이 창에서 실행해요.

* 맥은 `Cmd + Space` 를 누른 뒤 `터미널`을 검색해서 실행해요.
* 윈도우는 `Win` 키를 누른 뒤 `PowerShell`을 검색해서 실행해요.
  ![](/assets/install_node_5.Dpx_T0MU.webp)

:::

```bash
node -v
```

![](/assets/install_node_6.CUD4gATA.webp)

### 1-3. VS code 설치하기

VS Code(Visual Studio code)는 코드를 편집하는 프로그램이에요.\
하단 터미널에서 AI에게 코드 수정을 요청할 수 있어요.\
[VS Code 공식 사이트](https://code.visualstudio.com/)에서 다운로드해서 설치해 주세요.

![](/assets/install_vscode_1.65HdNVP3.webp)

설치가 끝나면 VS Code를 실행해 주세요.

![](/assets/install_vscode_2.LPbgY96D.webp)

좌측 상단 익스플로러 버튼을 눌러 미니앱 프로젝트 폴더를 생성해요.

![](/assets/install_vscode_3.CQzJkuDV.webp)

![](/assets/install_vscode_4.DqSQXROM.webp)

상단 메뉴에서 Terminal → New Terminal을 클릭하면 화면 하단에 터미널이 열려요.

![](/assets/install_vscode_5.CGFGrIrq.webp)

![](/assets/install_vscode_6.BUAUS1KM.webp)

***

## 2. AI 도구 설치하기

이제 앱을 대신 만들어 줄 AI 도구를 설치해요.\
처음 시작할 때는 Claude Code나 Codex 중 더 익숙한 도구를 사용하시면 돼요.\
사용하는 운영체제에 맞는 명령어를 VS Code 터미널에 복사해서 실행해 주세요.

### 2-1. macOS에서 설치하기

macOS에서는 Terminal을 열고 아래 명령어를 실행해 주세요.
::: code-group

```bash[Claude Code]
curl -fsSL https://claude.ai/install.sh | bash
```

```bash[Codex]
curl -fsSL https://chatgpt.com/codex/install.sh | sh
```

:::

### 2-2. Windows에서 설치하기

Windows에서는 PowerShell을 열고 아래 명령어를 실행해 주세요.

::: code-group

```powershell[Claude Code]
irm https://claude.ai/install.ps1 | iex
```

```powershell[Codex]
powershell -ExecutionPolicy ByPass -c "irm https://chatgpt.com/codex/install.ps1 | iex"
```

:::

설치가 끝나면 아래 명령어를 입력하고 버전 숫자가 표시되면 정상적으로 설치된 거예요.
::: code-group

```bash[Claude Code]
claude --version
```

```bash[Codex]
codex --version
```

:::

![](/assets/install_claude.DBai0Idw.webp)

***

## 3. 앱인토스 기능 연결하기

AI가 앱인토스 기능을 정확하게 사용할 수 있도록 MCP를 설치하고 연결하는 단계예요.

::: tip MCP가 왜 필요한가요?
AI는 기본적으로 앱인토스 SDK 사용법, API 구조 같은 도메인 지식을 알고 있지 않아요.\
MCP를 연결하면 AI가 앱인토스 문서와 코드 예제를 자동으로 참조해서 훨씬 정확한 코드를 만들어줘요.
:::

### 3-1. 패키지 관리자 설치하기

개발 도구를 쉽게 설치하기 위해 패키지 관리자가 필요해요.

::: details Mac
이미 Homebrew가 설치되어 있다면 이 단계는 건너뛰어도 돼요.
[brew.sh](https://brew.sh/)에서 코드를 복사해 터미널에 입력해 주세요.\
Homebrew는 개발 도구를 쉽게 설치하고 관리할 수 있게 해주는 도구예요.

![](/assets/install_homebrew.BTZ-H5u-.webp)\
Password: 라고 표시되면 컴퓨터 비밀번호를 입력하고 엔터를 누르면 돼요. 입력하는 동안에는 아무것도 표시되지 않아요.
:::

::: details Window
터미널에서 아래 명령어를 입력해 주세요.

```bash
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
Invoke-RestMethod -Uri https://get.scoop.sh | Invoke-Expression
```

:::

### 3-2. 앱인토스 MCP 설치하기

ax는 앱인토스(Apps in Toss)에서 만든 [AI 기반의 MCP/CLI 툴킷](https://github.com/toss/apps-in-toss-ax)으로,\
앱인토스 미니앱 개발을 위한 문서화, 코드 예제, 프로젝트 생성, 빌드, 배포까지 전체 워크플로우를 지원해요.\
아래 명령어를 입력해서 설치해 주세요.

:::code-group

```bash[macOS]
brew tap toss/tap && brew install ax
```

```bash[Window]
scoop bucket add toss https://github.com/toss/scoop-bucket.git
scoop install ax
```

:::

### 3-3. AI 도구에 MCP 연결하기

사용하는 AI 도구에 맞게 MCP를 연결해 주세요.

::: code-group

```bash [Claude Code]
claude mcp add --transport stdio apps-in-toss ax mcp start
```

```bash [Codex]
codex mcp add apps-in-toss -- ax mcp start
```

:::

아래와 같이 표시되면 정상적으로 설치된 거예요.

![](/assets/install_mcp.BFXa557m.webp)

**Cursor를 사용한다면**

아래 버튼을 클릭하면 자동으로 연결돼요.

버튼이 작동하지 않으면 `.cursor/mcp.json` 파일을 생성하거나 수정해 아래 내용을 추가해 주세요.

```json
{
  "mcpServers": {
    "apps-in-toss": {
      "command": "ax",
      "args": ["mcp", "start"]
    }
  }
}
```

#### 콘솔 작업용 MCP 연결하기

앱인토스 콘솔 MCP를 연결하면 콘솔에 직접 들어가지 않아도 Claude에서 워크스페이스, 미니앱, 검수, 번들, 인앱 결제, 인앱 광고 같은 작업을 실행할 수 있어요.\
현재는 Claude만 지원하고, Codex 지원은 준비 중이에요.

```bash
claude mcp add --transport http apps-in-toss-console \
  https://mcp.toss.im/adapters/apps-in-toss-console/mcp \
  --client-id mcp-gateway
```

명령어를 실행한 뒤 Claude에서 `/mcp`로 들어가 `apps-in-toss-console`을 선택하고 인증을 완료해 주세요.\
자세한 인증 방법과 사용할 수 있는 콘솔 작업 목록은 [AI로 콘솔 사용하기](/prepare/console-mcp.html)를 참고해 주세요.

***

## 4. 프로젝트 만들기

앱을 만들기 전에 코드 파일들이 들어갈 공간, 즉 프로젝트를 먼저 만들어야 해요.\
터미널에서 아래 명령어를 실행해 보세요.

```bash
# {appName} 에는 개발자센터 콘솔에서 앱을 등록할 때 입력한 appName을 넣어 주세요. (예: npx create-ait-app my-mini-app)
npx create-ait-app {appName}
```

질문이 나오면 아래 추천값을 선택해 주세요.\
처음이라면 그대로 따라 해도 되고, 이미 익숙한 패키지 매니저나 템플릿이 있다면 원하는 옵션을 선택해도 괜찮아요.

* **사용할 패키지 매니저를 선택하세요.** → `npm` 선택 후 엔터
* **사용할 템플릿을 선택하세요.** → `react-ts - React + TypeScript` 선택 후 엔터
* **TDS(Toss Design System)를 사용할까요?** → `Y` 입력 후 엔터
* **AI를 위한 skills를 추가할까요?** → 사용 중인 AI 도구 선택 후 엔터
* **예제 코드를 추가할까요?** → `인앱 결제` / `인앱 광고` 선택 후 엔터

![](/assets/install_project_1.Btl9fS-_.webp)

아래와 같이 표시되면 프로젝트가 정상적으로 만들어진 거예요.

![](/assets/install_project_2.C_RLWalA.webp)

***

## 5. 앱 정보 입력하기

좌측의 `granite.config.ts` 파일을 열어 앱 이름과 주요 색상, 아이콘과 같은 기본 정보를 넣어요.

![](/assets/config_granite.CN1KqaLi.webp)

그리고 아래와 같이 코드를 수정해 주세요.\
자세한 내용은 [앱 설정 가이드](https://developers-apps-in-toss.toss.im/bedrock/reference/framework/UI/Config.html)를 참고해 주세요.

```bash
import { defineConfig } from "@apps-in-toss/web-framework/config";

export default defineConfig({
  appName: "my-mini-app", // 콘솔에 입력한 appName을 입력하세요.
  brand: {
    displayName: "앱 이름", // 콘솔에 입력한 앱 이름을 입력하세요.
    primaryColor: "#FF91D5", // 화면에 노출될 앱의 기본 색상으로 바꿔주세요.
    icon: "", // 콘솔에서 업로드한 이미지의 URL을 입력하세요.(콘솔의 앱 정보에서 업로드한 이미지를 우클릭해 링크 복사 후 넣어주세요)
  },
  web: {
    host: "localhost",
    port: 5173,
    commands: {
      dev: "vite dev",
      build: "vite build",
    },
  },
  permissions: [],
  outdir: "dist",
});
```

***

## 6. 다양한 기능 추가하기

지금부터는 AI와 함께 원하는 기능을 하나씩 추가해 볼 차례예요.\
어떤 기능이 필요한지 말만 하면, AI가 알아서 만들어 줘요.

::: tip AI에게 잘 요청하는 방법

* 최대한 구체적으로 말해요
  * "버튼 만들어줘" 보다
    "화면 중앙에 시작하기 버튼을 만들고, 누르면 로그인 페이지로 이동하게 해줘"처럼 말하면 더 정확해요.
* 에러가 나오면 그대로 복사해서 보여줘요
  * 에러 메시지를 그대로 AI에게 보여주면 알아서 고쳐줘요.

:::

***

## 7. 테스트하고 완성하기

만든 앱 화면을 실시간으로 보면서 수정하고 싶다면 [샌드박스 가이드](/development/test/sandbox.html)를 따라해 주세요.

![](/assets/sandbox.BoUjbhlA.webp)

앱이 원하는 대로 만들어졌다면 터미널에서 아래 명령어로 ait 파일을 생성해요.

```bash
npm run build
```

![](/assets/build.BsSMTInn.webp)

그리고 아래 명령어를 입력해서 폴더를 연 다음에 ait 파일을 콘솔에 업로드 해주세요.

:::code-group

```bash[Mac]
open .
```

```bash[Window]
explorer .
```

:::

![](/assets/open.R7-BUrEl.webp)

해당 ait 파일을 앱인토스 콘솔의 ‘앱 출시’ 메뉴에 업로드하면 앱을 테스트할 수 있어요.\
테스트하는 방법은 [가이드](/development/test/toss.html)를 참고해 주세요.

![](/assets/ait_upload_1.B_i1wofP.webp)

![](/assets/ait_upload_2.D31dAsts.webp)

***

## 8. 앱 출시하기

테스트가 끝나면 앱인토스 콘솔에서 검토를 요청해 주세요.\
사용자에게 출시하기 전에는 반드시 아래 출시 가이드를 참고해 주세요.

* [게임 출시 가이드](/checklist/app-game.html) 문서 확인하기
* [비게임 출시 가이드](/checklist/app-nongame.html) 문서 확인하기

![](/assets/deploy_guide.1YJeIGW-.webp)

콘솔에서 앱 출시 및 롤백하는 방법이 궁금하면 [미니앱 출시](/development/deploy.html) 문서를 참고해 주세요.

처음엔 낯설었던 터미널과 코드가 이제 조금은 친숙하게 느껴지셨으면 좋겠어요.\
앞으로도 궁금한 게 생기면 언제든 AI에게 물어보며 만들어나가 보세요!

앱을 만든 후에는 유저에게 다가가기 위해 [마케팅 가이드](https://developers-apps-in-toss.toss.im/marketing/overview.html)도 함께 참고해 보세요.

***

## 더 잘 활용하기

Cursor나 다른 IDE를 사용하는 개발자라면, 앱인토스 문서를 AI에 직접 연결해서 더 정확한 코드를 생성할 수 있어요.

### Apps In Toss Skills 설치하기

Claude Code, Codex 같은 LLM 환경에서 앱인토스 공식 문서를 기반으로 답변을 받고 싶다면 **Apps In Toss Skills**를 설치해 주세요.\
`docs-search` 스킬은 앱인토스 전체 문서를 키워드와 의미 유사도 기반으로 검색해줘요.

::: code-group

```bash [Claude Code]
/plugin marketplace add toss/apps-in-toss-skills
/plugin install knowledge-skills@apps-in-toss-skills
```

```bash [Codex]
# $skill-installer 실행 후 아래 프롬프트 입력
install GitHub repo toss/apps-in-toss-skills path apps-in-toss
```

:::

설치 후 아래와 같이 사용할 수 있어요.

```
Search guide with docs-search "How to develop Apps In Toss Mini App"
```

### Cursor @docs 등록하기

Cursor를 사용한다면 앱인토스 문서를 직접 인덱싱해서 `@docs` 명령으로 참조할 수 있어요.

1. Cursor 우측 상단 **톱니바퀴(⚙️)** 아이콘을 클릭해요.
2. 왼쪽 메뉴에서 **Indexing & Docs**를 선택해요.
3. **Docs** 섹션에서 `+Add Doc` 버튼을 클릭해요.
4. 아래 표에서 필요한 문서 URL을 추가해요.

| 유형                   | 설명                           | URL                                                               |
| ---------------------- | ------------------------------ | ----------------------------------------------------------------- |
| **기본 문서 (권장)**   | 핵심 기능 위주의 문서          | `https://developers-apps-in-toss.toss.im/llms.txt`                |
| **전체 문서**          | 모든 기능 포함, 토큰 소모 많음 | `https://developers-apps-in-toss.toss.im/llms-full.txt`           |
| **예제 코드**          | 코드 예제만 빠르게 참고        | `https://developers-apps-in-toss.toss.im/tutorials/examples.html` |
| **TDS (WebView)**      | TDS WebView 문서               | `https://tossmini-docs.toss.im/tds-mobile/llms-full.txt`          |
| **TDS (React Native)** | TDS React Native 문서          | `https://tossmini-docs.toss.im/tds-react-native/llms-full.txt`    |

![llms-1](/assets/llms-1.BrrMMfdb.webp)

등록 후에는 `@docs`로 명시적으로 참조할 수 있어요.

```
@docs 앱인토스 인앱광고 샘플 코드 작성해줘
```

***

## 외부 서비스 연동하기

외부 서비스 연동이 필요하다면 아래 문서를 확인해 주세요.

* [Firebase 연동하기](/firebase/intro.html) — 인증, 데이터베이스, 푸시 알림 등 Firebase 서비스를 미니앱에 연동하는 방법을 안내해요.
* [Supabase 연동하기](/supabase/intro.html) — Supabase를 활용해 데이터베이스와 인증을 미니앱에 연동하는 방법을 안내해요.
* [Sentry 설정하기](/learn-more/sentry-monitoring) — 미니앱의 오류를 모니터링하고 추적하는 방법을 안내해요.
