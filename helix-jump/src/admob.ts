import { AdMob, BannerAdSize, BannerAdPosition } from '@capacitor-community/admob';
import type { BannerAdOptions, AdOptions, RewardAdOptions } from '@capacitor-community/admob';

// ─── 출시 전 교체 필요 ───────────────────────────────────────────────────────
// 아래 값을 Google AdMob 콘솔(https://apps.admob.com)에서 발급받은 실제 ID로 교체하세요.
// 테스트 ID는 개발/심사용으로만 사용하고 절대 출시하지 마세요.
const IS_PROD = import.meta.env.PROD;

const TEST_IDS = {
  banner:       'ca-app-pub-3940256099942544/6300978111',
  interstitial: 'ca-app-pub-3940256099942544/1033173712',
  rewarded:     'ca-app-pub-3940256099942544/5224354917',
};

const PROD_IDS = {
  banner:       'YOUR_BANNER_AD_UNIT_ID',       // AdMob 콘솔에서 발급
  interstitial: 'YOUR_INTERSTITIAL_AD_UNIT_ID', // AdMob 콘솔에서 발급
  rewarded:     'YOUR_REWARDED_AD_UNIT_ID',     // AdMob 콘솔에서 발급
};

const IDS = IS_PROD ? PROD_IDS : TEST_IDS;
// ────────────────────────────────────────────────────────────────────────────

export async function initAdMob() {
  try {
    await AdMob.initialize({ testingDevices: IS_PROD ? [] : ['EMULATOR'] });
  } catch {
    // 웹 환경에서는 무시
  }
}

export async function showBanner() {
  try {
    const options: BannerAdOptions = {
      adId: IDS.banner,
      adSize: BannerAdSize.BANNER,
      position: BannerAdPosition.BOTTOM_CENTER,
      margin: 0,
    };
    await AdMob.showBanner(options);
  } catch {
    // 웹 환경에서는 무시
  }
}

export async function removeBanner() {
  try {
    await AdMob.removeBanner();
  } catch {}
}

export async function showInterstitial() {
  try {
    const options: AdOptions = { adId: IDS.interstitial };
    await AdMob.prepareInterstitial(options);
    await AdMob.showInterstitial();
  } catch {
    // 웹 환경에서는 무시
  }
}

export async function showRewardedAd(): Promise<boolean> {
  try {
    const options: RewardAdOptions = { adId: IDS.rewarded };
    await AdMob.prepareRewardVideoAd(options);
    const result = await AdMob.showRewardVideoAd();
    return !!result;
  } catch {
    // 웹 환경에서는 시청 완료로 처리 (테스트용)
    return !IS_PROD;
  }
}
