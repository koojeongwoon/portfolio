/**
 * ✅ Gemini 병렬 요약 (fetchAll + systemInstruction 1회 정의)
 * - 각 URL별 독립 요청을 구성하고 fetchAll로 병렬 전송
 * - inlineRequests 미사용 (비동기 전용)
 * - systemInstruction은 한 번만 생성 후 모든 요청에 동일하게 주입
 */
function summarizeWithGemini(urls) {
  logInfo(`🚀 Gemini 병렬 요청 시작 (${urls.length}건)`);

  // 1️⃣ 공통 systemInstruction (한 번만 정의)
  const systemInstruction = {
    role: "system",
    parts: [{ text: buildPromptWithCategories() }],
  };

  // 2️⃣ URL별 요청 구성
  const requests = urls.map((url, idx) => {
    const isYouTube = /(?:youtube\.com|youtu\.be)/i.test(url);
    const parts = [];
    

    // 2) 유튜브면 file_data를 push (스프레드 X)
    if (isYouTube) {
      // 🎥 유튜브: file_data만 사용
      parts.push({ text: `You are summarizing a YouTube video.

Your task is to analyze **only the actual video content and its transcript**.  
Completely ignore any search results, external pages, metadata, or related videos suggested by search tools.

Do **not** use or rely on Google Search snippets, summaries, or any information outside the video itself.  
You must behave as if you have watched and listened to the video directly.

The only exception: you may include the **upload date** (publish date) if it appears clearly in the available metadata.  
Other details such as view count, channel description, or external references must be ignored.

Your summary must reflect the real narrative, arguments, and tone of the video itself — not web previews or summaries.`});
      parts.push({ file_data: { file_uri: url } });
      
    } else {
      parts.push({ text: buildUserPrompt(url) });
    }

    // 3️⃣ tools는 “기사 전용”으로만 추가
    const payload = {
      systemInstruction,
      tools: [{ googleSearch: {} }], // ✅ 유지
      // ...(isYouTube ? {} : { tools: [{ googleSearch: {} }] }),
      contents: [{ role: "user", parts }],
    };

    const byteSize = Utilities.newBlob(JSON.stringify(payload)).getBytes().length;
    const sizeMB = (byteSize / (1024 * 1024)).toFixed(2);
    if (byteSize > 20 * 1024 * 1024) {
      logError(`⚠️ [${idx + 1}] 요청 크기 초과 (${sizeMB}MB) - ${url}`);
    } else {
      logInfo(`📦 [${idx + 1}] 요청 크기: ${sizeMB}MB`);
    }

    return {
      url: GEMINI_API_URL,
      method: "post",
      contentType: "application/json",
      headers: { "x-goog-api-key": GEMINI_API_KEY },
      payload: JSON.stringify(payload),
      muteHttpExceptions: true,
    };
  });

  // 3️⃣ 병렬 요청 실행
  const responses = UrlFetchApp.fetchAll(requests);

  // 4️⃣ 결과 파싱
  const results = responses.map((res, idx) => {
    try {
      const code = res.getResponseCode();
      const body = res.getContentText();

      if (code >= 400) {
        logError(`⚠️ [${idx + 1}] Gemini 오류 (${code}) - ${urls[idx]}`);
        return "";
      }

      const data = JSON.parse(body);
      const text = data?.candidates?.[0]?.content?.parts?.[0]?.text || "";
      const clean = cleanMarkdown(text);

      if (!clean) {
        logError(`⚠️ [${idx + 1}] 빈 응답 - ${urls[idx]}`);
        return "";
      }

      logInfo(`✅ [${idx + 1}] 요약 완료`);
      return clean;
    } catch (e) {
      logError(`❌ [${idx + 1}] 파싱 실패 (${e.message})`);
      return "";
    }
  });

  // 5️⃣ 통계 요약
  const successCount = results.filter(Boolean).length;
  logInfo(`🎯 Gemini 병렬 요약 완료: ${successCount}/${urls.length} 성공`);

  return results;
}

/**
 * ✅ Markdown 정리
 */
function cleanMarkdown(md) {
  return md
    .replace(/```(?:markdown)?/gi, "")
    .replace(/```$/g, "")
    .trim();
}

/**
 * ✅ 실패 URL 추출
 */
function extractFailedUrls(urls, results) {
  return urls.filter((_, i) => !results[i] || results[i].trim() === "");
}
