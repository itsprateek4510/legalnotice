"""
Configuration module.

Loads environment variables and exposes application constants.
Add a `.env` file in the backend/ directory (copy from .env.example)
and fill in the required values.
"""

import os


def _load_dotenv():
    """Manually load a .env file if python-dotenv is not available."""
    try:
        from dotenv import load_dotenv

        load_dotenv()
    except ImportError:
        env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
        if os.path.exists(env_path):
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    key, _, value = line.partition("=")
                    os.environ.setdefault(key.strip(), value.strip())


_load_dotenv()


class Settings:
    """Central configuration loaded from environment variables."""

    # --- LLM provider ---
    # One of: "gemini" (default), "openai", "ollama"
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "gemini").lower()

    # --- Google Gemini (default provider) ---
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")

    # --- OpenAI (alternative provider) ---
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    LLM_MODEL: str = os.getenv("LLM_MODEL", "gpt-3.5-turbo")
    OPENAI_BASE_URL: str = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")

    # --- Optional local LLM (Ollama) ---
    USE_LOCAL_LLM: bool = os.getenv("USE_LOCAL_LLM", "false").lower() in (
        "true",
        "1",
        "yes",
    )
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "llama2")

    # --- Server ---
    PORT: int = int(os.getenv("PORT", "8000"))
    HOST: str = os.getenv("HOST", "0.0.0.0")

    # --- Allowed origins for CORS ---
    ALLOWED_ORIGINS: list = [
        origin.strip()
        for origin in os.getenv(
            "ALLOWED_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000"
        ).split(",")
        if origin.strip()
    ]

    # --- Database ---
    # SQLite by default (file lives inside the backend directory).
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "sqlite:///" + os.path.join(os.path.dirname(os.path.dirname(__file__)), "app.db"),
    )

    # --- Authentication (JWT) ---
    # Change SECRET_KEY in production (must be at least 32 chars for HS256).
    SECRET_KEY: str = os.getenv(
        "SECRET_KEY",
        "dev-secret-change-me-0123456789-0123456789abcdefgh",
    )
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    JWT_EXPIRE_MINUTES: int = int(os.getenv("JWT_EXPIRE_MINUTES", "1440"))

    # --- Misc constants ---
    MAX_FILE_SIZE: int = int(os.getenv("MAX_FILE_SIZE", str(10 * 1024 * 1024)))  # 10 MB


settings = Settings()
