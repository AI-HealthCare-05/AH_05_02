from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


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
    diet_family: Literal["random", "D01", "D02", "D03"] = "random"
    activity_family: Literal["random", "A01", "A02"] = "random"
    routine_family: Literal["random", "H01", "H02", "R01"] = "random"
    # A cup is only a UI unit.  It never supplies a medical target by itself.
    water_goal_status: Literal["unconfirmed", "confirmed", "clinician_review_required"] = "unconfirmed"
    personal_drink_goal_ml: int | None = Field(default=None, ge=200, le=4000)
    water_cup_ml: int = Field(default=200, ge=100, le=500)

    @model_validator(mode="after")
    def confirmed_water_goal_requires_amount(self):
        if self.water_goal_status == "confirmed" and self.personal_drink_goal_ml is None:
            raise ValueError("개인 음료 목표를 확인한 경우 하루 목표량(mL)을 함께 입력해 주세요.")
        return self


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
