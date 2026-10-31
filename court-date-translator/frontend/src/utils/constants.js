// Shared constants for the frontend.

export const API_BASE_URL =
  process.env.REACT_APP_API_URL || "http://localhost:8000";

// Language options sent to the backend to control the regional translation.
export const LANGUAGES = [
  { code: "hindi", label: "हिन्दी (Hindi)" },
  { code: "english", label: "English" },
  { code: "punjabi", label: "ਪੰਜਾਬੀ (Punjabi)" },
  { code: "tamil", label: "தமிழ் (Tamil)" },
  { code: "telugu", label: "తెలుగు (Telugu)" },
  { code: "bengali", label: "বাংলা (Bengali)" },
  { code: "marathi", label: "मराठी (Marathi)" },
  { code: "gujarati", label: "ગુજરાતી (Gujarati)" },
  { code: "kannada", label: "ಕನ್ನಡ (Kannada)" },
  { code: "malayalam", label: "മലയാളം (Malayalam)" },
];

// localStorage key for the JWT auth token.
export const AUTH_TOKEN_KEY = "legal-notice-token";
export const AUTH_USER_KEY = "legal-notice-user";

// localStorage key for saved analyses (kept as a light offline cache).
export const HISTORY_STORAGE_KEY = "legal-notice-history";

// Maximum number of history entries kept in localStorage.
export const MAX_HISTORY = 10;