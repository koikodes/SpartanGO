"""Push notifications through Expo's push service (works for iPhone and Android builds).

Only send what a rider needs (service alerts, ride status). Messages never include other
riders' information. Failures are logged and ignored so a push outage never breaks the API.
"""
import logging
from typing import Iterable, Optional

import httpx

from . import db
from .config import settings

EXPO_PUSH_URL = "https://exp.host/--/api/v2/push/send"
log = logging.getLogger("spartango.push")


def tokens_for(user_ids: Optional[Iterable[int]] = None) -> list[str]:
    with db.connect() as c:
        if user_ids is None:
            rows = c.execute("SELECT token FROM push_tokens").fetchall()
        else:
            ids = list(user_ids)
            if not ids:
                return []
            rows = c.execute(f"SELECT token FROM push_tokens WHERE user_id IN ({','.join('?' * len(ids))})", ids).fetchall()
    return [r["token"] for r in rows]


def send(tokens: list[str], title: str, body: str, data: Optional[dict] = None) -> None:
    if not settings.push_enabled or not tokens:
        return
    messages = [{"to": t, "title": title, "body": body, "sound": "default", "data": data or {}} for t in tokens]
    try:
        with httpx.Client(timeout=10) as client:
            for i in range(0, len(messages), 100):  # Expo accepts up to 100 per request
                client.post(EXPO_PUSH_URL, json=messages[i:i + 100])
    except Exception as exc:  # never let notifications break a request
        log.warning("push send failed: %s", exc)


def to_everyone(title: str, body: str, data: Optional[dict] = None) -> None:
    send(tokens_for(None), title, body, data)


def to_user(user_id: int, title: str, body: str, data: Optional[dict] = None) -> None:
    send(tokens_for([user_id]), title, body, data)
