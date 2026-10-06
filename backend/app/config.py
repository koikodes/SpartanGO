"""App settings, read from environment variables (see .env.example)."""
import os
import secrets
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Settings:
    # Which live-location source to use: "mock" (simulated shuttles) or "transloc".
    tracker_provider: str = os.getenv("TRACKER_PROVIDER", "mock")
    transloc_api_key: str = os.getenv("TRANSLOC_API_KEY", "")
    transloc_agency_id: str = os.getenv("TRANSLOC_AGENCY_ID", "")

    # Secrets. In production these MUST come from the environment, never the repo.
    jwt_secret: str = field(default_factory=lambda: os.getenv("JWT_SECRET") or secrets.token_hex(32))
    pass_secret: str = field(default_factory=lambda: os.getenv("PASS_SECRET") or secrets.token_hex(32))

    # Only these email domains can sign up.
    allowed_email_domains: tuple = tuple(
        d.strip() for d in os.getenv("ALLOWED_EMAIL_DOMAINS", "spartans.nsu.edu,nsu.edu").split(",")
    )

    access_token_minutes: int = int(os.getenv("ACCESS_TOKEN_MINUTES", "1440"))
    # Ride-pass QR codes rotate this often, so a screenshot stops working quickly.
    pass_window_seconds: int = int(os.getenv("PASS_WINDOW_SECONDS", "30"))

    database_path: str = os.getenv("DATABASE_PATH", "spartango.db")
    avg_shuttle_speed_mps: float = float(os.getenv("AVG_SHUTTLE_SPEED_MPS", "6.7"))  # ~15 mph with stops


settings = Settings()
