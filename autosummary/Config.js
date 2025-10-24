/** ✅ 전역 환경 설정 (Script Properties 기반) */
const scriptProps = PropertiesService.getScriptProperties();

const LINK_FILE_ID = scriptProps.getProperty("LINK_FILE_ID");
const OUTPUT_FOLDER_ID = scriptProps.getProperty("OUTPUT_FOLDER_ID");
const GEMINI_API_KEY = scriptProps.getProperty("GEMINI_API_KEY");

const GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent";

const CATEGORY_MAP = JSON.parse(scriptProps.getProperty("CATEGORY_MAP") || "{}");


/*
 * 설정에 넣을 카테고리 맵
{
  "AI": [
    "AI 기술",
    "인공지능",
    "LLM",
    "ChatGPT",
    "Codex",
    "Claude",
    "Claude Code",
    "Gemini",
    "Gemini Cli",
    "NotebookLM",
    "Perplexity",
    "MCP",
    "A2A",
    "Context",
    "Prompt"
  ],
  "보안": [
    "보안",
    "Security",
    "침해사고",
    "해킹",
    "취약점"
  ],
  "개발": [
    "개발",
    "Development",
    "Programming",
    "코딩",
    "코드",
    "Software",
    "java",
    "spring",
    "springboot",
    "성능 튜닝",
    "SQL"
  ],
  "재테크": [
    "경제",
    "Business",
    "Finance",
    "투자",
    "시장",
    "주식",
    "ETF",
    "절세",
    "세금"
  ],
  "블로그": [
    "마케팅",
    "부업",
    "키워드"
  ],
  "육아": [
    "언어",
    "훈육",
    "어린이",
    "아들"
  ],
  "요리": [
    "레시피",
    "음식",
    "식재료",
    "밥",
    "찌개"
  ],
  "여행": [
    "국내여행",
    "해외여행",
    "숙소",
    "교통",
    "비행기",
    "현지"
  ],
  "건강": [
    "운동",
    "혈액순환",
    "관절"
  ]
}
 */