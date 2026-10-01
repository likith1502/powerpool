"""
Pydantic data schemas for PowerPool API contracts.
"""

from pydantic import BaseModel, Field
from typing import List, Optional


class ForecastSlot(BaseModel):
    slot: int
    time: str
    timestamp: Optional[str] = None
    demand_kw: float
    solar_kw: float
    capacity_kw: float
    gap_kw: float
    is_stress: bool


class ForecastResponse(BaseModel):
    date: str
    scenario: str
    slots: List[ForecastSlot]


class OptimizeRequest(BaseModel):
    date: Optional[str] = "2026-10-01"
    scenario: Optional[str] = "sunny"
    compliance_rate: Optional[float] = 0.65


class OptimizeResponse(BaseModel):
    before: List[ForecastSlot]
    after: List[ForecastSlot]
    nudges_created: int
    peak_before_kw: float
    peak_after_kw: float
    peak_reduction_pct: float
    kwh_shifted: float


class NudgeItem(BaseModel):
    id: int
    household_id: int
    appliance: str
    from_time: str
    to_time: str
    kwh_shifted: float
    points: int
    saving_rs: float
    message: str
    message_hi: Optional[str] = None
    message_te: Optional[str] = None
    status: str  # pending, accepted, skipped


class HouseholdNudgesResponse(BaseModel):
    household_id: int
    nudges: List[NudgeItem]


class NudgeRespondRequest(BaseModel):
    accept: bool


class NudgeRespondResponse(BaseModel):
    id: int
    status: str
    points_added: int
    saving_rs: float
    message: str


class KPIResponse(BaseModel):
    peak_reduction_pct: float
    kwh_shifted: float
    solar_self_use_pct: float
    solar_self_use_change_pct: float
    co2_kg: float
    participants: int
    households: int


class LeaderboardItem(BaseModel):
    rank: int
    household_id: int
    name: str
    points: int
    kwh_shifted: float


class LeaderboardResponse(BaseModel):
    leaderboard: List[LeaderboardItem]


class DREventRequest(BaseModel):
    start_slot: int = Field(default=74, ge=0, le=95)
    end_slot: int = Field(default=88, ge=0, le=95)
    target_kw: float = 170.0


class DREventResponse(BaseModel):
    success: bool
    nudges_created: int
    target_kw: float
    available_flexible_kw: float
    peak_after_kw: float
    message: str


class FlexCapacityResponse(BaseModel):
    window: str
    available_kw: float
    households_available: int
