"""Shared data shapes (API responses + internal types)."""
from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class Stop(BaseModel):
    id: str
    name: str
    lat: float
    lng: float


class Route(BaseModel):
    id: str
    name: str
    color: str
    is_loop: bool
    stops: list[Stop]


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


class Arrival(BaseModel):
    stop_id: str
    route_id: str
    vehicle_id: str
    eta_seconds: int


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


class RideStatusUpdate(BaseModel):
    status: RideStatus


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
