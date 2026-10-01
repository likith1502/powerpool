"""Pydantic models = the API contract.

Naming note
-----------
The original internal names (e.g. /optimize, /kpis, /nudges) are kept.
The planned external names (/schedule/run, /metrics, /schedule/{home_id})
are served as additive aliases in main.py so both paths work.
"""
from typing import List, Literal, Optional, Union
from pydantic import BaseModel, Field


class SlotPoint(BaseModel):
    slot: int
    time: str
    demand_kw: float
    capacity_kw: float = 170.0
    solar_kw: float = 0.0
    gap_kw: float = 0.0
    is_stress: bool = False


class OptimizeRequest(BaseModel):
    date: Optional[str] = None
    scenario: Optional[str] = None
    compliance_rate: Optional[float] = Field(default=None, ge=0.0, le=1.0)


class ForecastSlot(BaseModel):
    slot: int
    time: str
    timestamp: Optional[str] = None
    demand_kw: float
    solar_kw: float
    capacity_kw: float
    gap_kw: float
    is_stress: bool
    # 'mock' = synthetic seeded demo data; 'model' = Member A's pipeline precomputed scenario forecast; 'live_model' = real-time LightGBM inference.
    data_source: Literal["mock", "model", "live_model"] = "mock"
    model_type: Optional[str] = None


class ForecastResponse(BaseModel):
    date: str
    slots: List[ForecastSlot]


class FeasibilityReport(BaseModel):
    target_capacity_kw: float = 170.0
    baseline_peak_kw: float
    optimized_peak_kw: float
    peak_reduction_kw: float
    peak_reduction_pct: float
    remaining_overload_kw: float
    available_flex_kw: float
    stage2_curtailment_required_kw: float
    is_feasible: bool
    feasibility_status: str
    limiting_factors: List[str] = []


class OptimizeResponse(BaseModel):
    before: List[SlotPoint]
    after: List[SlotPoint]
    nudges_created: int
    peak_before_kw: float
    peak_after_kw: float
    peak_reduction_pct: float
    kwh_shifted: float = 0.0
    capacity_kw: float = 170.0
    remaining_overload_kw: Optional[float] = None
    is_feasible: Optional[bool] = None
    feasibility_status: Optional[str] = None
    feasibility: Optional[FeasibilityReport] = None
    stage2_after: Optional[List[SlotPoint]] = None
    stage2_peak_kw: Optional[float] = None


class Nudge(BaseModel):
    id: int
    household_id: Union[str, int]
    appliance_id: int
    appliance: str
    from_slot: int
    to_slot: int
    from_time: str
    to_time: str
    kwh_shifted: float
    points: int
    saving_rs: float
    status: str
    message: str
    message_hi: Optional[str] = None
    message_te: Optional[str] = None
    message_en: Optional[str] = None


class NudgesResponse(BaseModel):
    household_id: Union[str, int]
    nudges: List[Nudge]


class RespondRequest(BaseModel):
    accept: bool


class RespondResponse(BaseModel):
    id: int
    nudge_id: int
    status: str
    points_added: int = 0
    saving_rs: float = 0.0
    household_points: int
    message: str = ""


class KPIs(BaseModel):
    peak_before_kw: float
    peak_after_kw: float
    peak_reduction_pct: float
    kwh_shifted: float
    rs_saved: float
    co2_kg: float
    solar_self_use_pct_before: float
    solar_self_use_pct: float
    solar_self_use_change_pct: float = 0.0
    participants: int
    total_households: int
    households: int
    transformer_risk: str


class LeaderRow(BaseModel):
    rank: int
    household_id: Union[str, int]
    name: str
    block: str = ""
    points: int
    kwh_shifted: float = 0.0


class LeaderboardResponse(BaseModel):
    leaderboard: List[LeaderRow]


class DREventRequest(BaseModel):
    start_slot: int = Field(ge=0, le=95)
    end_slot: int = Field(ge=0, le=95)
    target_kw: float = Field(gt=0)
    date: Optional[str] = None
    scenario: Optional[str] = None


class DREventResponse(BaseModel):
    success: bool = True
    nudges_created: int
    target_kw: float
    available_flexible_kw: float
    peak_after_kw: float
    kw_reduced_expected: float
    after: List[SlotPoint]


class FlexHour(BaseModel):
    hour: int
    time: str
    flexible_kw: float


class FlexCapacityResponse(BaseModel):
    window: str = "next_hour"
    available_kw: float
    households_available: int
    hourly: Optional[List[FlexHour]] = None


class Household(BaseModel):
    id: Union[str, int]
    name: str
    type: str
    block: str
    language: str
    points: int


# ── /nudge/send  (POST) ────────────────────────────────────────────────────────
class NudgeSendRequest(BaseModel):
    household_id: Union[str, int] = Field(description="Target household")
    nudge_id: Optional[int] = Field(
        default=None,
        description="Specific nudge to send. Omit to send all pending nudges for the household.",
    )
    chat_id: Optional[Union[str, int]] = Field(
        default=None,
        description="Optional Telegram chat ID for direct push notification.",
    )


class NudgeSendResponse(BaseModel):
    household_id: Union[str, int]
    nudges_queued: int
    channel: Literal["telegram", "api_only"] = "api_only"
    delivered: bool = False
    messages: List[str]
