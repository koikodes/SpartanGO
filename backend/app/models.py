"""Shared data shapes (API responses + internal types)."""
from datetime import datetime
from enum import Enum
from typing import Literal, Optional

from pydantic import BaseModel, EmailStr, Field


class TemporaryStop(BaseModel):
    """Where a stop has moved to while a 'stop moved' service alert is active."""
    name: str
    lat: float
    lng: float
    alert_id: int
    until: Optional[datetime] = None


class Stop(BaseModel):
    id: str
    name: str
    lat: float
    lng: float
    temporary: Optional[TemporaryStop] = None


class Schedule(BaseModel):
    """Official service pattern, used for 'Scheduled' arrival times when no shuttle is reporting."""
    first_departure: str = Field(description="HH:MM local time the first trip leaves the first stop")
    last_departure: str = Field(description="HH:MM local time the last trip leaves the first stop")
    headway_minutes: int = Field(gt=0, le=240)
    days: list[int] = Field(default=[0, 1, 2, 3, 4], description="0 = Monday ... 6 = Sunday")


class Route(BaseModel):
    id: str
    name: str
    color: str
    is_loop: bool
    stops: list[Stop]
    # Stop-to-stop travel times in seconds, measured by riding the route (one per path segment).
    # When present, arrival times use these instead of distance / average speed.
    segment_seconds: Optional[list[int]] = None
    dwell_seconds: int = 20
    schedule: Optional[Schedule] = None
    # Set when a 'no service' alert covers this route right now (the alert's title).
    service_paused: Optional[str] = None


class Vehicle(BaseModel):
    """A shuttle's live position, normalized from whatever tracker NSU uses."""
    id: str
    route_id: str
    lat: float
    lng: float
    heading: Optional[float] = None
    speed_mps: Optional[float] = None
    passenger_load: Optional[float] = Field(None, ge=0, le=1, description="0 = empty, 1 = full")
    updated_at: datetime
    source: Literal["live", "simulated"] = "live"


class Arrival(BaseModel):
    stop_id: str
    route_id: str
    vehicle_id: Optional[str]
    eta_seconds: int
    # live: from a real shuttle's position. simulated: demo shuttle. scheduled: from the timetable.
    kind: Literal["live", "simulated", "scheduled"] = "live"


class TrackerPositionIn(BaseModel):
    """A driver's (or tracker phone's) GPS fix, sent every few seconds while tracker mode is on."""
    vehicle_id: str = Field(min_length=1, max_length=40, pattern=r"^[A-Za-z0-9 _.-]+$")
    route_id: str
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)
    speed_mps: Optional[float] = Field(None, ge=0, le=60)
    heading: Optional[float] = Field(None, ge=0, le=360)


class AlertType(str, Enum):
    stop_moved = "stop_moved"
    no_service = "no_service"
    delay = "delay"
    announcement = "announcement"


class AlertIn(BaseModel):
    type: AlertType
    title: str = Field(min_length=1, max_length=80)
    message: str = Field(min_length=1, max_length=500)
    route_ids: list[str] = Field(default_factory=list, description="Empty = every route")
    stop_id: Optional[str] = None
    moved_to_name: Optional[str] = Field(None, max_length=80)
    moved_to_lat: Optional[float] = Field(None, ge=-90, le=90)
    moved_to_lng: Optional[float] = Field(None, ge=-180, le=180)
    starts_at: Optional[datetime] = None
    ends_at: Optional[datetime] = None
    notify: bool = True


class AlertOut(BaseModel):
    id: int
    type: AlertType
    title: str
    message: str
    route_ids: list[str]
    stop_id: Optional[str]
    moved_to_name: Optional[str]
    moved_to_lat: Optional[float]
    moved_to_lng: Optional[float]
    starts_at: datetime
    ends_at: Optional[datetime]
    created_at: datetime
    active: bool


class PushTokenIn(BaseModel):
    token: str = Field(min_length=10, max_length=200, pattern=r"^(ExponentPushToken|ExpoPushToken)\[[A-Za-z0-9_-]+\]$")


class Role(str, Enum):
    student = "student"
    driver = "driver"
    admin = "admin"


class SignupIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    name: str = Field(min_length=1, max_length=80)
    student_id: str = Field(min_length=4, max_length=20)
    accepted_terms_version: str = Field(min_length=1, max_length=20, description="Version of the Terms the user agreed to")


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: Role


class UserOut(BaseModel):
    id: int
    email: str
    name: str
    role: Role


class RideStatus(str, Enum):
    pending = "pending"
    accepted = "accepted"
    picked_up = "picked_up"
    completed = "completed"
    cancelled = "cancelled"


class RideRequestIn(BaseModel):
    route_id: str
    pickup_stop_id: str
    dropoff_stop_id: str
    note: Optional[str] = Field(None, max_length=200)


class RideRequestOut(BaseModel):
    id: int
    user_id: int
    route_id: str
    pickup_stop_id: str
    dropoff_stop_id: str
    status: RideStatus
    note: Optional[str]
    created_at: datetime
    # The shuttle the system assigned (Uber-style: riders never pick a driver).
    vehicle_id: Optional[str] = None
    pickup_eta_seconds: Optional[int] = None
    vehicle: Optional[Vehicle] = None


class RideStatusUpdate(BaseModel):
    status: RideStatus
    vehicle_id: Optional[str] = Field(None, max_length=40)  # a driver accepting a waiting ride for their shuttle


class PassOut(BaseModel):
    token: str          # what the QR code encodes
    expires_in: int     # seconds until the app should refresh it


class PassVerifyIn(BaseModel):
    token: str
    vehicle_id: Optional[str] = None


class PassVerifyOut(BaseModel):
    valid: bool
    name: Optional[str] = None
    reason: Optional[str] = None
