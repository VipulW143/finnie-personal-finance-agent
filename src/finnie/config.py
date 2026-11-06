import os
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def get_settings() -> dict[str, str]:
    """Return non-secret settings from the process environment."""
    load_dotenv(PROJECT_ROOT / ".env")
    return {
        "environment": os.getenv("FINNIE_ENV", "development"),
        "provider": os.getenv("FINNIE_PROVIDER", "openai"),
        "model": os.getenv("FINNIE_MODEL", "gpt-4o-mini"),
        "embedding_model": os.getenv(
            "OPENAI_EMBEDDING_MODEL", "text-embedding-3-small"
        ),
    }


def get_alpaca_credentials() -> tuple[str, str] | None:
    """Read the Alpaca key pair without including either secret in app settings."""
    load_dotenv(PROJECT_ROOT / ".env")
    key_id = os.getenv("APCA_API_KEY_ID", "").strip()
    secret_key = os.getenv("APCA_API_SECRET_KEY", "").strip()
    if not key_id or not secret_key:
        return None
    return key_id, secret_key
