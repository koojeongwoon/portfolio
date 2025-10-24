function loadUrlList() {
  const file = DriveApp.getFileById(LINK_FILE_ID);
  return file.getBlob()
    .getDataAsString("UTF-8")
    .split("\n")
    .map(u => u.trim())
    .filter(Boolean);
}

function updateLinkFile(nextUrls) {
  const file = DriveApp.getFileById(LINK_FILE_ID);
  file.setContent(nextUrls.join("\n\n"));
  logInfo(`🗂️ 남은 URL ${nextUrls.length}건 저장 완료`);
}
