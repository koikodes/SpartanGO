"""The one interface every tracking source must implement.

NSU's shuttles already report location through an existing system. Whatever that turns
out to be (TransLoc, Passio GO, DoubleMap, Samsara, a custom feed...), write one class that
implements `get_vehicles()` and returns normalized `Vehicle` objects. Nothing else in the
backend or the app has to change.
"""
from abc import ABC, abstractmethod

from ..models import Vehicle


class TrackerProvider(ABC):
    @abstractmethod
    async def get_vehicles(self) -> list[Vehicle]:
        """Return every shuttle currently in service."""
