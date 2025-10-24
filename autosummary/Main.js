/**
 * ✅ Google Apps Script Entry Point
 * - 웹앱 실행 시 doGet() 자동 호출
 * - 전체 파이프라인을 한 번 실행합니다.
 */
function doGet() {
  try {
    const result = processLinkBatch();
    return ContentService.createTextOutput(`✅ 실행 성공: ${result}`);
  } catch (error) {
    logError(`❌ [Fatal] ${error.message}`);
    return ContentService.createTextOutput(`❌ 오류: ${error.message}`);
  }
}

/**
 * ✅ 전체 URL 처리 파이프라인
 */
function processLinkBatch() {
  const urls = loadUrlList();
  if (urls.length === 0) return "처리할 URL이 없습니다.";

  const BATCH_SIZE = 10;
  const batchUrls = urls.slice(0, BATCH_SIZE);
  const remainingUrls = urls.slice(BATCH_SIZE);

  const geminiResults = summarizeWithGemini(batchUrls);

  const successCount = saveMarkdownResults(batchUrls, geminiResults);
  const failedUrls = extractFailedUrls(batchUrls, geminiResults);
  const nextUrls = [...remainingUrls, ...failedUrls];

  updateLinkFile(nextUrls);

  const msg = `이번 실행: ${successCount}/${batchUrls.length} 성공 (잔여 ${nextUrls.length})`;
  logInfo(msg);
  return msg;
}
