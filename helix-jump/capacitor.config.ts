import type { CapacitorConfig } from '@capacitor/cli';

// ─── 출시 전 교체 필요 ───────────────────────────────────────────────────────
// androidAppId / iosAppId를 AdMob 콘솔에서 발급받은 앱 ID로 교체하세요.
// appId는 앱스토어 등록 시 사용한 Bundle ID와 일치해야 합니다.
// ────────────────────────────────────────────────────────────────────────────

const config: CapacitorConfig = {
  appId: 'com.haakon0904.helixjump',    // App Store / Play Store Bundle ID
  appName: 'Helix Jump',
  webDir: 'dist',
  plugins: {
    AdMob: {
      androidAppId: 'YOUR_ADMOB_ANDROID_APP_ID', // 예: ca-app-pub-XXXXXX~XXXXXXXX
      iosAppId:     'YOUR_ADMOB_IOS_APP_ID',     // 예: ca-app-pub-XXXXXX~XXXXXXXX
    },
  },
};

export default config;
