from ..config import settings
from .base import TrackerProvider


def get_provider(routes) -> TrackerProvider:
    """Pick the live-location source from TRACKER_PROVIDER."""
    name = settings.tracker_provider.lower()
    if name == "mock":
        from .mock import MockProvider
        return MockProvider(routes)
    if name == "transloc":
        from .transloc import TransLocProvider
        return TransLocProvider(settings.transloc_api_key, settings.transloc_agency_id)
    raise ValueError(f"Unknown TRACKER_PROVIDER: {name!r}")
