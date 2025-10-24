/**
 * ✅ 공통 로깅 유틸 (향후 Slack 알림 등 확장 가능)
 */
function logInfo(msg) {
  Logger.log(`ℹ️ ${msg}`);
}

function logError(msg) {
  Logger.log(`❌ ${msg}`);
}

/**
 * ✅ 간단한 delay (API rate 제한 대응용)
 */
function sleep(ms) {
  Utilities.sleep(ms);
}
