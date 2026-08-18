from __future__ import annotations

from datetime import UTC, date, datetime
from math import exp
from typing import Annotated, Literal
from uuid import uuid4

from fastapi import APIRouter, Header, HTTPException, Query, status
from pydantic import BaseModel, Field, field_validator

router = APIRouter(prefix="/api/v1", tags=["prototype"])


def now_iso() -> str:
    return datetime.now(UTC).isoformat()


def envelope(data: object) -> dict[str, object]:
    return {"data": data, "meta": {"request_id": f"req_{uuid4().hex[:12]}", "timestamp": now_iso()}}


class PrototypeStore:
    """Ephemeral prototype store. It must never be treated as a production database."""

    def __init__(self) -> None:
        self.users: dict[int, dict] = {}
        self.consents: dict[int, list[dict]] = {}
        self.eligibility: dict[int, dict] = {}
        self.checkups: dict[int, dict] = {}
        self.predictions: dict[int, dict] = {}
        self.jobs: dict[str, dict] = {}
        self.cycles: dict[int, dict] = {}
        self.logs: dict[int, dict[str, dict]] = {}
        self._sequences = {
            "user": 100,
            "consent": 10,
            "eligibility": 30,
            "checkup": 500,
            "prediction": 900,
            "cycle": 40,
            "user_challenge": 700,
        }

    def next_id(self, name: str) -> int:
        self._sequences[name] += 1
        return self._sequences[name]


store = PrototypeStore()


def current_user(authorization: Annotated[str | None, Header()] = None) -> int:
    if not authorization or not authorization.startswith("Bearer prototype-user-"):
        raise HTTPException(status_code=401, detail="프로토타입 로그인이 필요합니다.")
    try:
        user_id = int(authorization.rsplit("-", 1)[1])
    except ValueError as exc:
        raise HTTPException(status_code=401, detail="유효하지 않은 프로토타입 세션입니다.") from exc
    if user_id not in store.users:
        raise HTTPException(status_code=401, detail="세션 사용자를 찾을 수 없습니다.")
    return user_id


class SignupRequest(BaseModel):
    email: str
    password: str = Field(min_length=8, max_length=128)
    terms_agreed: Literal[True]

    @field_validator("email")
    @classmethod
    def validate_email_shape(cls, value: str) -> str:
        if "@" not in value or value.startswith("@") or value.endswith("@"):
            raise ValueError("이메일 형식을 확인해 주세요.")
        return value


@router.post("/auth/signup", status_code=status.HTTP_201_CREATED)
def signup(payload: SignupRequest) -> dict[str, object]:
    user_id = store.next_id("user")
    # The prototype validates but deliberately does not retain the password.
    store.users[user_id] = {"user_id": user_id, "email": str(payload.email), "created_at": now_iso()}
    return envelope(
        {
            **store.users[user_id],
            "access_token": f"prototype-user-{user_id}",
            "storage_notice": "프로토타입 메모리 세션이며 서버 재시작 시 삭제됩니다.",
        }
    )


class ConsentRequest(BaseModel):
    consent_item: str = "health_data"
    version: str = "1.0"
    is_agreed: Literal[True]


@router.post("/consents", status_code=status.HTTP_201_CREATED)
def create_consent(payload: ConsentRequest, authorization: str | None = Header(default=None)) -> dict[str, object]:
    resolved_user = current_user(authorization)
    consent = {"consent_id": store.next_id("consent"), **payload.model_dump(), "agreed_at": now_iso()}
    store.consents.setdefault(resolved_user, []).append(consent)
    return envelope(consent)


class EligibilityRequest(BaseModel):
    birth_date: date
    has_diabetes_diagnosis: bool = False
    has_hypertension_diagnosis: bool = False
    uses_glucose_lowering_drug: bool = False
    has_alarming_symptom: bool = False
    has_exercise_limitation: bool = False


def age_on_today(birth_date: date) -> int:
    today = date.today()
    return today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))


@router.post("/eligibility-checks", status_code=status.HTTP_201_CREATED)
def check_eligibility(
    payload: EligibilityRequest, authorization: str | None = Header(default=None)
) -> dict[str, object]:
    user_id = current_user(authorization)
    if not store.consents.get(user_id):
        raise HTTPException(status_code=403, detail="건강정보 처리 동의가 필요합니다.")
    age = age_on_today(payload.birth_date)
    reasons: list[str] = []
    if age < 19:
        reasons.append("만 19세 미만")
    if payload.has_diabetes_diagnosis or payload.uses_glucose_lowering_drug:
        reasons.append("당뇨병 진단 또는 혈당강하제 복용 확인")
    if payload.has_hypertension_diagnosis:
        reasons.append("고혈압 진단 확인")
    if payload.has_alarming_symptom:
        reasons.append("의료진 확인이 우선인 증상")
    eligible = not reasons
    result = {
        "eligibility_check_id": store.next_id("eligibility"),
        "age": age,
        "is_adult": age >= 19,
        "target_segment": "primary_senior" if age >= 65 else "adult",
        "is_eligible": eligible,
        "exclusion_reasons": reasons,
        "next_action": "health_checkup_input" if eligible else "medical_guidance",
        "guidance": "이 서비스는 진단 전 위험 선별용입니다. 증상이나 기존 진단이 있다면 의료기관과 상담해 주세요."
        if not eligible
        else "건강정보 입력을 계속할 수 있습니다.",
    }
    store.eligibility[user_id] = {**result, **payload.model_dump(mode="json")}
    return envelope(result)


class HealthCheckupRequest(BaseModel):
    checkup_type: Literal["initial", "reassessment"] = "initial"
    checkup_date: date
    gender: Literal["female", "male", "other"]
    height_cm: float = Field(ge=120, le=220)
    weight_kg: float = Field(ge=30, le=250)
    waist_cm: float = Field(ge=45, le=180)
    systolic_bp: int = Field(ge=70, le=250)
    diastolic_bp: int = Field(ge=40, le=150)
    fasting_glucose: float | None = Field(default=None, ge=40, le=500)
    smoking_status: Literal["never", "former", "current"]
    drinking_frequency: Literal["none", "monthly_or_less", "weekly", "frequent"] = "none"
    physical_activity_level: Literal["sufficient", "insufficient", "none"]
    has_family_history_diabetes: bool


@router.post("/health-checkups", status_code=status.HTTP_201_CREATED)
def create_checkup(
    payload: HealthCheckupRequest, authorization: str | None = Header(default=None)
) -> dict[str, object]:
    user_id = current_user(authorization)
    eligibility = store.eligibility.get(user_id)
    if not eligibility or not eligibility["is_eligible"]:
        raise HTTPException(status_code=403, detail="서비스 적합성 확인을 먼저 완료해 주세요.")
    checkup_id = store.next_id("checkup")
    bmi = round(payload.weight_kg / ((payload.height_cm / 100) ** 2), 1)
    item = {
        "checkup_id": checkup_id,
        "user_id": user_id,
        "bmi": bmi,
        "age": eligibility["age"],
        **payload.model_dump(mode="json"),
        "created_at": now_iso(),
    }
    store.checkups[checkup_id] = item
    return envelope({"checkup_id": checkup_id, "bmi": bmi, "created_at": item["created_at"]})


class MockDiabetesInferenceAdapter:
    """Deterministic mock for UI/API integration only; not a clinical model."""

    model_version = "mock-diabetes-3stage-v0.1"

    @classmethod
    def predict(cls, checkup: dict) -> tuple[dict, list[dict]]:
        contributions = [
            ("연령", max(0.0, (checkup["age"] - 45) / 90), "나이가 높을수록 생활습관 점검이 중요합니다."),
            ("체질량지수", max(0.0, (checkup["bmi"] - 23) / 16), "체중과 허리둘레를 함께 살펴보세요."),
            ("허리둘레", max(0.0, (checkup["waist_cm"] - 80) / 55), "허리둘레는 대사 건강과 관련된 지표입니다."),
            ("수축기 혈압", max(0.0, (checkup["systolic_bp"] - 120) / 90), "혈압은 반복 측정 후 의료진과 상의하세요."),
            (
                "가족력",
                0.45 if checkup["has_family_history_diabetes"] else 0.0,
                "가족력이 있으면 정기 검진이 더 중요합니다.",
            ),
            (
                "흡연",
                0.35 if checkup["smoking_status"] == "current" else 0.0,
                "금연은 여러 만성질환 위험을 낮추는 데 도움이 됩니다.",
            ),
            (
                "신체활동",
                0.4
                if checkup["physical_activity_level"] == "none"
                else 0.22
                if checkup["physical_activity_level"] == "insufficient"
                else -0.25,
                "가능한 범위에서 규칙적인 활동을 이어가세요.",
            ),
        ]
        linear = -2.8 + sum(value for _, value, _ in contributions)
        risk = 1 / (1 + exp(-linear))
        if risk < 0.22:
            stage = "normal"
            probs = (0.68, 0.25, 0.07)
        elif risk < 0.48:
            stage = "prediabetes"
            probs = (0.22, 0.63, 0.15)
        else:
            stage = "diabetes_screening_advised"
            probs = (0.08, 0.27, 0.65)
        ranked = sorted(contributions, key=lambda item: item[1], reverse=True)
        risk_factors = [
            {
                "factor_name": name,
                "direction": "protective" if value < 0 else "risk",
                "importance": round(abs(value), 2),
                "description": description,
            }
            for name, value, description in ranked[:5]
        ]
        prediction = {
            "disease_type": "diabetes",
            "predicted_stage": stage,
            "probabilities": {"normal": probs[0], "prediabetes": probs[1], "screening_advised": probs[2]},
            "risk_score": round(risk, 3),
            "model_version": cls.model_version,
            "is_mock": True,
            "model_notice": "화면·API 연동 검증용 mock 결과이며 실제 의료 예측이 아닙니다.",
            "medical_notice": "이 결과는 진단이나 처방이 아닙니다. 검진 결과와 증상은 의료진과 상담하세요.",
        }
        return prediction, risk_factors


class PredictionJobRequest(BaseModel):
    checkup_id: int
    disease_type: Literal["diabetes", "hypertension"] = "diabetes"


@router.post("/prediction-jobs", status_code=status.HTTP_202_ACCEPTED)
def create_prediction_job(
    payload: PredictionJobRequest, authorization: str | None = Header(default=None)
) -> dict[str, object]:
    user_id = current_user(authorization)
    checkup = store.checkups.get(payload.checkup_id)
    if not checkup or checkup["user_id"] != user_id:
        raise HTTPException(status_code=404, detail="건강정보 기록을 찾을 수 없습니다.")
    if payload.disease_type != "diabetes":
        raise HTTPException(
            status_code=409, detail="고혈압 모델은 확장 예정이며 현재 프로토타입에서는 사용할 수 없습니다."
        )
    prediction_id = store.next_id("prediction")
    prediction, factors = MockDiabetesInferenceAdapter.predict(checkup)
    item = {
        "prediction_id": prediction_id,
        "user_id": user_id,
        "checkup_id": payload.checkup_id,
        **prediction,
        "risk_factors": factors,
        "created_at": now_iso(),
    }
    store.predictions[prediction_id] = item
    job_id = f"job_{uuid4().hex[:10]}"
    store.jobs[job_id] = {"job_id": job_id, "status": "succeeded", "prediction_id": prediction_id, "is_mock": True}
    return envelope(store.jobs[job_id])


@router.get("/prediction-jobs/{job_id}")
def get_prediction_job(job_id: str, authorization: str | None = Header(default=None)) -> dict[str, object]:
    current_user(authorization)
    if job_id not in store.jobs:
        raise HTTPException(status_code=404, detail="예측 작업을 찾을 수 없습니다.")
    return envelope(store.jobs[job_id])


@router.get("/predictions/{prediction_id}")
def get_prediction(prediction_id: int, authorization: str | None = Header(default=None)) -> dict[str, object]:
    user_id = current_user(authorization)
    item = store.predictions.get(prediction_id)
    if not item or item["user_id"] != user_id:
        raise HTTPException(status_code=404, detail="예측 결과를 찾을 수 없습니다.")
    return envelope({key: value for key, value in item.items() if key not in {"risk_factors", "user_id"}})


@router.get("/predictions/{prediction_id}/risk-factors")
def get_risk_factors(prediction_id: int, authorization: str | None = Header(default=None)) -> dict[str, object]:
    user_id = current_user(authorization)
    item = store.predictions.get(prediction_id)
    if not item or item["user_id"] != user_id:
        raise HTTPException(status_code=404, detail="예측 결과를 찾을 수 없습니다.")
    return envelope({"items": item["risk_factors"]})


CHALLENGES = [
    {
        "challenge_id": 1,
        "title": "식후 10분 천천히 걷기",
        "category": "activity",
        "daily_goal": "10분",
        "reason": "식후 가벼운 활동 습관을 만들어 봅니다.",
        "safety": "통증·어지럼이 있으면 멈추고 의료진과 상담하세요.",
    },
    {
        "challenge_id": 2,
        "title": "하루 물 6잔 확인하기",
        "category": "hydration",
        "daily_goal": "6잔",
        "reason": "물을 마신 횟수를 기록하는 쉬운 습관입니다.",
        "safety": "수분 제한을 안내받았다면 의료진 지침을 우선하세요.",
    },
    {
        "challenge_id": 3,
        "title": "채소 반찬 한 접시 더하기",
        "category": "diet",
        "daily_goal": "1회",
        "reason": "균형 잡힌 식사를 실천하기 위한 기록입니다.",
        "safety": "개별 식이 제한이 있다면 의료진 지침을 우선하세요.",
    },
]


@router.get("/challenge-recommendations")
def challenge_recommendations(
    prediction_id: int = Query(), authorization: str | None = Header(default=None)
) -> dict[str, object]:
    user_id = current_user(authorization)
    if prediction_id not in store.predictions or store.predictions[prediction_id]["user_id"] != user_id:
        raise HTTPException(status_code=404, detail="예측 결과를 찾을 수 없습니다.")
    return envelope({"items": CHALLENGES, "recommendation_notice": "건강교육용 일반 제안이며 치료나 처방이 아닙니다."})


class ChallengeCycleRequest(BaseModel):
    prediction_id: int
    challenge_ids: list[int] = Field(min_length=1, max_length=3)


@router.post("/challenge-cycles", status_code=status.HTTP_201_CREATED)
def create_challenge_cycle(
    payload: ChallengeCycleRequest, authorization: str | None = Header(default=None)
) -> dict[str, object]:
    user_id = current_user(authorization)
    if payload.prediction_id not in store.predictions or store.predictions[payload.prediction_id]["user_id"] != user_id:
        raise HTTPException(status_code=404, detail="예측 결과를 찾을 수 없습니다.")
    cycle_id = store.next_id("cycle")
    user_challenges = []
    for challenge_id in payload.challenge_ids:
        match = next((item for item in CHALLENGES if item["challenge_id"] == challenge_id), None)
        if not match:
            raise HTTPException(status_code=422, detail=f"챌린지 {challenge_id}를 찾을 수 없습니다.")
        user_challenges.append({"user_challenge_id": store.next_id("user_challenge"), **match})
    item = {
        "cycle_id": cycle_id,
        "user_id": user_id,
        "prediction_id": payload.prediction_id,
        "week_number": 1,
        "duration_days": 28,
        "status": "active",
        "user_challenges": user_challenges,
        "created_at": now_iso(),
    }
    store.cycles[user_id] = item
    return envelope({key: value for key, value in item.items() if key != "user_id"})


class ChallengeLogRequest(BaseModel):
    is_completed: bool
    note: str | None = Field(default=None, max_length=200)


@router.put("/user-challenges/{user_challenge_id}/logs/{log_date}")
def upsert_challenge_log(
    user_challenge_id: int,
    log_date: date,
    payload: ChallengeLogRequest,
    authorization: str | None = Header(default=None),
) -> dict[str, object]:
    user_id = current_user(authorization)
    cycle = store.cycles.get(user_id)
    if not cycle or user_challenge_id not in {item["user_challenge_id"] for item in cycle["user_challenges"]}:
        raise HTTPException(status_code=404, detail="선택한 챌린지를 찾을 수 없습니다.")
    log = {
        "user_challenge_id": user_challenge_id,
        "log_date": log_date.isoformat(),
        **payload.model_dump(),
        "updated_at": now_iso(),
    }
    store.logs.setdefault(user_id, {})[f"{user_challenge_id}:{log_date.isoformat()}"] = log
    return envelope(log)


@router.get("/dashboard/summary")
def dashboard_summary(authorization: str | None = Header(default=None)) -> dict[str, object]:
    user_id = current_user(authorization)
    predictions = sorted(
        (p for p in store.predictions.values() if p["user_id"] == user_id), key=lambda p: p["created_at"]
    )
    latest = predictions[-1] if predictions else None
    first = predictions[0] if predictions else None
    risk_change = round(latest["risk_score"] - first["risk_score"], 3) if latest and first else None
    cycle = store.cycles.get(user_id)
    logs = list(store.logs.get(user_id, {}).values())
    completed = sum(1 for item in logs if item["is_completed"])
    return envelope(
        {
            "latest_prediction": None
            if not latest
            else {
                "prediction_id": latest["prediction_id"],
                "predicted_stage": latest["predicted_stage"],
                "risk_score": latest["risk_score"],
                "is_mock": True,
            },
            "risk_change_from_first": risk_change,
            "risk_change_calculation": "조회 시 최초·최신 예측값으로 계산",
            "active_cycle": None
            if not cycle
            else {
                "cycle_id": cycle["cycle_id"],
                "week_number": cycle["week_number"],
                "duration_days": cycle["duration_days"],
                "selected_count": len(cycle["user_challenges"]),
            },
            "challenge_completion": {"completed_logs": completed, "total_logs": len(logs)},
            "medical_notice": "위험도는 선별 참고값이며 진단 결과가 아닙니다.",
        }
    )


@router.get("/models/active")
def active_models() -> dict[str, object]:
    return envelope(
        {
            "items": [
                {
                    "disease_type": "diabetes",
                    "model_version": MockDiabetesInferenceAdapter.model_version,
                    "status": "mock",
                    "classes": ["normal", "prediabetes", "screening_advised"],
                },
                {"disease_type": "hypertension", "status": "planned"},
            ]
        }
    )
