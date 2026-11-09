from ..config import settings
from ..models import Vehicle
from .base import TrackerProvider


class CompositeProvider(TrackerProvider):
    """Combine several sources, e.g. "phone+mock": real tracked shuttles plus simulated ones."""

    def __init__(self, providers: list[TrackerProvider]):
        self.providers = providers

    async def get_vehicles(self) -> list[Vehicle]:
        out: list[Vehicle] = []
        seen: set[str] = set()
        errors = []
        for p in self.providers:
            try:
                for v in await p.get_vehicles():
                    if v.id not in seen:
                        seen.add(v.id)
                        out.append(v)
            except Exception as exc:  # one source down shouldn't hide the others
                errors.append(exc)
        if errors and len(errors) == len(self.providers):
            raise errors[0]
        return out


def _single(name: str, routes) -> TrackerProvider:
    if name == "mock":
        from .mock import MockProvider
        return MockProvider(routes)
    if name == "phone":
        from .phone import PhoneProvider
        return PhoneProvider(settings.stale_after_seconds)
    if name == "transloc":
        from .transloc import TransLocProvider
        return TransLocProvider(settings.transloc_api_key, settings.transloc_agency_id)
    if name == "samsara":
        from .samsara import SamsaraProvider
        return SamsaraProvider.from_settings(settings)
    if name == "gtfs_rt":
        from .gtfs_rt import GtfsRealtimeProvider
        return GtfsRealtimeProvider.from_settings(settings)
    raise ValueError(f"Unknown TRACKER_PROVIDER: {name!r}")


def get_provider(routes) -> TrackerProvider:
    """Pick the live-location source(s) from TRACKER_PROVIDER, e.g. "phone" or "phone+mock"."""
    names = [n.strip() for n in settings.tracker_provider.lower().replace(",", "+").split("+") if n.strip()]
    if len(names) == 1:
        return _single(names[0], routes)
    return CompositeProvider([_single(n, routes) for n in names])
