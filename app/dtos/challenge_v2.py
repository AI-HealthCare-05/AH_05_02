from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class V2Preferences(BaseModel):
    model_config = ConfigDict(extra="forbid")
    mode: Literal["diet_focus", "activity_focus", "balanced"] = "balanced"
    safety_confirmed: bool = False
    exercise_allowed: bool = False
    dietary_changes_allowed: bool = False
    planned_meals: int = Field(default=1, ge=0, le=3)
    sugary_drink_opportunities: int = Field(default=0, ge=0, le=3)
    fluid_restriction: bool = True
    swallowing_restriction: bool = True
    therapeutic_diet: bool = True
    food_allergy: bool = True
    photo_consent: bool = False
    photo_accessible: bool = False
    transition_consent: bool = False
    max_difficulty: Literal["E", "M", "H"] = "E"


class V2SessionInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    performed_at: datetime
    done: Literal[True]
    quantity: float | None = Field(default=None, ge=0, le=1440, allow_inf_nan=False)
    intake_ml: float | None = Field(default=None, ge=0, le=20000, allow_inf_nan=False)
    note: str = Field(default="", max_length=500)
    improvement: str = Field(default="", max_length=200)
    serving_amount: float | None = Field(default=None, gt=0, le=10000, allow_inf_nan=False)
    serving_unit: Literal["g", "mL"] | None = None
    sugar_g: float | None = Field(default=None, ge=0, le=10000, allow_inf_nan=False)
    carbohydrate_g: float | None = Field(default=None, ge=0, le=10000, allow_inf_nan=False)
    product_category: str = Field(default="", max_length=80)


class V2Replacement(BaseModel):
    model_config = ConfigDict(extra="forbid")
    template_code: str = Field(max_length=30)
    reason: Literal["accessibility", "too_hard", "preference", "safety"]


class V2Review(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: Literal["passed", "needs_retry", "inconclusive"]
    criteria_results: dict[str, bool]
    reason: str = Field(min_length=1, max_length=500)
    viewed_evidence: Literal[True]
    generation: int = Field(ge=1)
