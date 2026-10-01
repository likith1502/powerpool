"""Pydantic models = the API contract.

Naming note
-----------
The original internal names (e.g. /optimize, /kpis, /nudges) are kept.
The planned external names (/schedule/run, /metrics, /schedule/{home_id})
are served as additive aliases in main.py so both paths work.
"""
from typing import List, Literal, Optional
from pydantic import BaseModel, Field


class SlotPoint(BaseModel):
    slot: int
    time: str
    demand_kw: float


class ForecastSlot(BaseModel):
    slot: int
    time: str
    demand_kw: float
    solar_kw: float
    capacity_kw: float
    gap_kw: float
    is_stress: bool
    # 'mock' = seed_mock.py data; 'model' = Member A's ML pipeline.
    # Member C uses this to show a data-freshness badge.
    # ⚠ NEEDS TEAM AGREEMENT: field name and allowed values.
    data_source: Literal["mock", "model"] = "mock"


class OptimizeResponse(BaseModel):
    before: List[SlotPoint]
    after: List[SlotPoint]
    nudges_created: int
    peak_before_kw: float
    peak_after_kw: float
    peak_reduction_pct: float


class Nudge(BaseModel):
    id: int
    household_id: int
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


class RespondRequest(BaseModel):
    accept: bool


class RespondResponse(BaseModel):
    nudge_id: int
    status: str
    household_points: int


class KPIs(BaseModel):
    peak_before_kw: float
    peak_after_kw: float
    peak_reduction_pct: float
    kwh_shifted: float
    rs_saved: float
    co2_kg: float
    solar_self_use_pct_before: float
    solar_self_use_pct: float
    participants: int
    total_households: int
    transformer_risk: str


class LeaderRow(BaseModel):
    rank: int
    household_id: int
    name: str
    block: str
    points: int


class DREventRequest(BaseModel):
    start_slot: int = Field(ge=0, le=95)
    end_slot: int = Field(ge=0, le=95)
    target_kw: float = Field(gt=0)


class DREventResponse(BaseModel):
    nudges_created: int
    kw_reduced_expected: float
    after: List[SlotPoint]


class FlexHour(BaseModel):
    hour: int
    time: str
    flexible_kw: float


class Household(BaseModel):
    id: int
    name: str
    type: str
    block: str
    language: str
    points: int


# ── /nudge/send  (POST) ────────────────────────────────────────────────────────
# ⚠ NEEDS TEAM AGREEMENT: should this trigger real Telegram delivery,
# return a delivery receipt, or both? For now the backend assembles the
# nudge text and returns a preview without making any real Telegram calls.
class NudgeSendRequest(BaseModel):
    household_id: int = Field(gt=0, description="Target household")
    nudge_id: Optional[int] = Field(
        default=None,
        description="Specific nudge to send. Omit to send all pending nudges for the household.",
    )


class NudgeSendResponse(BaseModel):
    household_id: int
    nudges_queued: int
    # 'telegram' only when TELEGRAM_TOKEN is set AND bot is running externally.
    channel: Literal["telegram", "api_only"] = "api_only"
    # delivered=True only when an actual Telegram push was made.
    delivered: bool = False
    messages: List[str]  # preview of nudge text(s) that would be / were sent
