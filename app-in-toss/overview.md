---
url: >-
  https://developers-apps-in-toss.toss.im/bedrock/reference/framework/시작하기/overview.md
description: 앱인토스 API & SDK에서 제공하는 주요 기능을 한눈에 살펴볼 수 있어요.
---

# API & SDK 한 눈에 보기

| 기능                                                                                                                                                      | 설명                                                                                                           |
| --------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------- |
| [사용자 식별키 발급](/user-hash-key/develop.html)                                                                                                         | 게임 안에서 사용자를 안전하게 구분하는 고유 번호를 발급해요. 랭킹, 보상 같은 사용자별 데이터를 관리할 때 써요. |
| [게임 리더보드](/game-center/develop.html)                                                                                                                | 플레이가 끝나면 점수를 등록하고 순위를 보여줘요. 경쟁 요소로 다시 하고 싶게 만들어요.                          |
| [프로모션](/bedrock/reference/framework/비게임/promotion.html)                                                                                            | 사용자에게 포인트나 보상을 지급해요. 출석 보상, 이벤트 같은 데 활용하기 좋아요.                                |
| [공유 리워드](/bedrock/reference/framework/친구초대/contactsViral.html)                                                                                   | 친구를 초대하거나 공유를 완료하면 보상을 줘요. 입소문으로 새 사용자가 들어오게 해요.                           |
| [토스앱 공유 링크](/bedrock/reference/framework/공유/getTossShareLink.html)                                                                               | 게임 결과나 초대 링크를 만들어, 받은 사람이 토스 앱에서 바로 열 수 있어요.                                     |
| [일회성 결제](/bedrock/reference/framework/인앱%20결제/IAP.html)                                                                                          | 아이템처럼 한 번씩 파는 상품으로 수익을 낼 수 있어요.                                                          |
| [정기 결제](/bedrock/reference/framework/인앱%20결제/subscription.html)                                                                                   | 월간 멤버십 같은 구독 상품으로 매달 반복 수익을 낼 수 있어요.                                                  |
| [전면형/리워드 광고](/bedrock/reference/framework/광고/IntegratedAd.html)                                                                                 | 화면 전체를 덮는 광고나, 보면 보상을 주는 광고를 넣을 수 있어요.                                               |
| [배너 광고(WebView)](/bedrock/reference/framework/광고/BannerAd.html), [배너 광고(React Native)](/bedrock/reference/framework/광고/RN-BannerAd.html) | 화면 한쪽에 띄우는 띠 형태의 광고를 넣을 수 있어요. (웹뷰·리액트 네이티브 모두 지원)                           |
| [Storage](/bedrock/reference/framework/저장소/Storage.html)                                                                                               | 사용자 정보를 기기에 저장해요. 기기를 바꿔도 데이터가 사라지지 않게 설계할 수 있어요.                          |
| [화면 속성](/bedrock/reference/framework/화면%20제어/screen-properties.html)                                                                              | 화면이 꺼지지 않게 하거나(방치형 게임), 가로·세로를 고정할 수 있어요.                                          |
| [Safe Area](/bedrock/reference/framework/화면%20제어/safe-area.html)                                                                                      | 기기마다 다른 노치·둥근 모서리에 화면이 가려지지 않게 여백을 맞춰줘요.                                         |
| [사용자 행동 기록](/bedrock/reference/framework/분석/Analytics.html)                                                                                      | 사용자가 게임에서 뭘 했는지 기록해요. 데이터 분석, A/B 테스트 등 게임 개선에 꼭 필요해요.                      |
| [네트워크](/bedrock/reference/framework/네트워크/network.html)                                                                                            | 토스 서버 시간을 가져와요. 시간 조작(치팅)을 막거나 이벤트 기간을 정확히 확인할 때 써요.                       |

| 기능                                                                                                                                                      | 설명                                                                                 |
| --------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------ |
| [내비게이션 바](/bedrock/reference/framework/UI/NavigationBar.html)                                                                                       | 화면 상단의 제목·뒤로가기 영역을 설정할 수 있어요.                                   |
| [사용자 식별키 발급](/user-hash-key/develop.html)                                                                                                         | 로그인한 사용자가 누구인지 구분하고, 회원 정보와 연결할 수 있어요.                   |
| [토스 로그인](/login/develop.html)                                                                                                                        | 사용자가 토스 계정으로 별도 가입 없이 간편하게 로그인할 수 있어요.                   |
| [토스 인증](/tossauth/develop.html)                                                                                                                       | 본인 확인이 필요할 때 토스 인증 화면을 띄울 수 있어요.                               |
| [스마트 발송](/smart-message/develop.html)                                                                                                                | 사용자에게 알림 메시지를 보내거나, 알림 수신 동의를 받을 수 있어요.                  |
| [공유 리워드](/bedrock/reference/framework/친구초대/contactsViral.html)                                                                                   | 사용자가 친구에게 앱을 공유하면, 그 결과에 따라 보상을 줄 수 있어요.                 |
| [토스앱 공유 링크](/bedrock/reference/framework/공유/getTossShareLink.html)                                                                               | 원하는 화면 경로를 토스 앱에서 바로 열리는 공유 링크로 바꿔줘요.                     |
| [메시지 공유](/bedrock/reference/framework/공유/share.html)                                                                                               | 콘텐츠를 쉽게 공유하도록, 기기의 기본 공유 창을 띄워줘요.                            |
| [리뷰 요청](/bedrock/reference/framework/인터렉션/requestReview.html)                                                                                     | 사용자가 만족을 느낄 만한 시점에 앱 리뷰 작성을 부탁할 수 있어요.                    |
| [게임 리더보드](/game-center/develop.html)                                                                                                                | 사용자의 게임 점수를 모아 순위를 보여줄 수 있어요.                                   |
| [프로모션](/bedrock/reference/framework/비게임/promotion.html)                                                                                            | 사용자에게 토스 포인트를 지급할 수 있어요.                                           |
| [사용자 행동 기록](/bedrock/reference/framework/분석/Analytics.html)                                                                                      | 사용자가 앱에서 뭘 했는지 기록해, 데이터로 분석할 수 있어요.                         |
| [유입경로 레퍼러](/bedrock/reference/framework/분석/referrer.html)                                                                                        | 사용자가 어떤 경로로 앱에 들어왔는지 확인할 수 있어요.                               |
| [토스애즈 픽셀 연동](/tosspixel/develop.html)                                                                                                             | 광고를 보고 들어온 사용자의 성과를 측정할 수 있어요.                                 |
| [일회성 결제](/bedrock/reference/framework/인앱%20결제/IAP.html)                                                                                          | 한 번씩 결제하는 인앱 결제 기능을 넣을 수 있어요.                                    |
| [정기 결제](/bedrock/reference/framework/인앱%20결제/subscription.html)                                                                                   | 정해진 주기마다 자동으로 결제되는 구독 상품 결제 함수를 제공해요.                    |
| [일회성 결제](/tosspay/develop.html)                                                                                                                      | 토스페이 결제창을 띄우고 본인 인증까지 진행해요.                                     |
| [정기 결제](/tosspay/auto-pay.html)                                                                                                                       | 토스페이로 정기 결제를 연결할 수 있어요.                                             |
| [전면형/리워드 광고](/bedrock/reference/framework/광고/IntegratedAd.html)                                                                                 | 화면 전체를 덮는 광고나, 보면 보상을 주는 광고를 넣을 수 있어요.                     |
| [배너 광고(WebView)](/bedrock/reference/framework/광고/BannerAd.html), [배너 광고(React Native)](/bedrock/reference/framework/광고/RN-BannerAd.html) | 화면 한쪽에 띄우는 띠 형태의 광고를 넣을 수 있어요. (웹뷰·리액트 네이티브 모두 지원) |
| [Safe Area](/bedrock/reference/framework/화면%20제어/safe-area.html)                                                                                      | 노치·둥근 모서리에 가려지지 않도록 화면 여백 값을 확인해요.                          |
| [화면 속성](/bedrock/reference/framework/화면%20제어/screen-properties.html)                                                                              | 화면 방향(가로·세로), 항상 켜짐, 화면 캡처 막기 등을 설정할 수 있어요.               |
| [이벤트 제어](/bedrock/reference/framework/이벤트%20제어/back-event.html)                                                                                 | 뒤로가기 버튼을 눌렀을 때의 동작을 직접 정할 수 있어요.                              |
| [화면 닫기](/bedrock/reference/framework/화면%20제어/closeView.html)                                                                                      | 화면 닫기, 스와이프로 뒤로가기(iOS) 등 화면을 닫는 동작을 제어해요.                  |
| [외부 URL 열기](/bedrock/reference/framework/화면%20이동/openURL.html)                                                                                    | 지정한 주소를 기기 브라우저나 연결된 앱에서 열 수 있어요.                            |
| [사진 촬영](/bedrock/reference/framework/카메라/openCamera.html)                                                                                          | 카메라를 켜서 찍은 사진을 가져와요.                                                  |
| [앨범 선택](/bedrock/reference/framework/사진/album.html)                                                                                                 | 사용자의 앨범에서 사진·동영상을 골라 가져와요.                                       |
| [클립보드](/bedrock/reference/framework/클립보드/clipboard.html)                                                                                          | 복사한 텍스트를 가져오거나, 텍스트를 복사해 둘 수 있어요.                            |
| [연락처](/bedrock/reference/framework/연락처/fetchContacts.html)                                                                                          | 사용자의 연락처 목록을 가져와요.                                                     |
| [위치](/bedrock/reference/framework/위치%20정보/Location.html)                                                                                            | 현재 위치를 확인하거나 실시간으로 위치를 추적할 수 있어요.                           |
| [파일 저장](/bedrock/reference/framework/데이터/saveBase64Data.html)                                                                                      | 이미지·문서 같은 파일을 사용자 기기에 저장해요.                                      |
| [PDF 뷰어](/bedrock/reference/framework/PDF/openPDFViewer.html)                                                                                           | PDF 파일을 앱 안에서 바로 열어 볼 수 있어요.                                         |
| [Storage](/bedrock/reference/framework/저장소/Storage.html)                                                                                               | 사용자 정보를 기기에 저장할 수 있어요.                                               |
| [네트워크](/bedrock/reference/framework/네트워크/network.html)                                                                                            | 인터넷 연결 상태 확인, 데이터 통신, 서버 시간 조회를 할 수 있어요.                   |
| [버전](/bedrock/reference/framework/환경%20확인/version.html)                                                                                             | 사용자의 토스 앱 버전을 확인하거나, 최소 지원 버전을 점검할 수 있어요.               |
| [실행 환경](/bedrock/reference/framework/환경%20확인/runtime-environment.html)                                                                            | 사용자가 어떤 기기·환경에서 앱을 켰는지 정보를 확인할 수 있어요.                     |
| [언어](/bedrock/reference/framework/언어/getLocale.html)                                                                                                  | 사용자가 어떤 언어를 쓰는지 확인할 수 있어요.                                        |
