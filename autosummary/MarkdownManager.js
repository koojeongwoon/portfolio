/**
 * ✅ Gemini 결과를 Markdown 파일로 저장
 */
function saveMarkdownResults(urls, markdownResults) {
  const rootFolder = DriveApp.getFolderById(OUTPUT_FOLDER_ID);
  let success = 0;

  markdownResults.forEach((md, i) => {
    if (!md) return;
    const url = urls[i];
    const category = extractCategory(md);
    const title = extractTitle(md);
    const categoryFolder = getOrCreateSubFolder(rootFolder, category);
    createMarkdownFileInFolder(categoryFolder.getId(), title, md);
    success++;
  });

  logInfo(`📝 Markdown 저장 완료 (${success}/${urls.length})`);
  return success;
}

function extractCategory(md) {
  const yamlMatch = md.match(/category:\s*"?([^"\n]+)"?/i);
  return yamlMatch ? yamlMatch[1].trim() : "기타";
}

function extractTitle(md) {
  const titleMatch = md.match(/^#\s*(.+)/m);
  return titleMatch ? titleMatch[1].trim() : "Untitled";
}

function createMarkdownFileInFolder(folderId, title, content) {
  const folder = DriveApp.getFolderById(folderId);
  const safeTitle = title.replace(/[\\/:*?"<>|]/g, "_");
  const fileName = `${safeTitle}.md`;
  const existing = folder.getFilesByName(fileName);
  if (existing.hasNext()) {
    existing.next().setContent(content);
    logInfo(`♻️ 덮어쓰기 완료: ${fileName}`);
  } else {
    folder.createFile(fileName, content, MimeType.PLAIN_TEXT);
    logInfo(`✅ 새 파일 생성: ${fileName}`);
  }
}

function getOrCreateSubFolder(parentFolder, name) {
  const safeName = name.replace(/[\\/:*?"<>|]/g, "_");
  const folders = parentFolder.getFoldersByName(safeName);
  if (folders.hasNext()) return folders.next();
  return parentFolder.createFolder(safeName);
}
