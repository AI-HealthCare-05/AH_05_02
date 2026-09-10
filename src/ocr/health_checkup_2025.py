from __future__ import annotations

import re
from datetime import datetime

FIELD_PATTERNS: dict[str, tuple[str, ...]] = {
    "height_cm": (r"(?:신장|키)\s*[:：]?\s*(\d+(?:\.\d+)?)\s*cm",),
    "weight_kg": (r"(?:체중|몸무게)\s*[:：]?\s*(\d+(?:\.\d+)?)\s*kg",),
    "waist_cm": (r"(?:허리둘레|허리)\s*[:：]?\s*(\d+(?:\.\d+)?)\s*cm",),
    "bmi": (r"(?:체질량지수|BMI)\s*[:：]?\s*(\d+(?:\.\d+)?)",),
    "fasting_glucose_mg_dl": (r"(?:공복혈당|공복혈당검사)\s*[:：]?\s*(\d+(?:\.\d+)?)\s*(?:mg/?dL)?",),
    "total_cholesterol_mg_dl": (r"(?:총콜레스테롤)\s*[:：]?\s*(\d+(?:\.\d+)?)\s*(?:mg/?dL)?",),
    "hdl_cholesterol_mg_dl": (r"(?:HDL(?:-?콜레스테롤)?)\s*[:：]?\s*(\d+(?:\.\d+)?)",),
    "triglycerides_mg_dl": (r"(?:중성지방|트리글리세라이드)\s*[:：]?\s*(\d+(?:\.\d+)?)",),
    "ldl_cholesterol_mg_dl": (r"(?:LDL(?:-?콜레스테롤)?)\s*[:：]?\s*(\d+(?:\.\d+)?)",),
    "creatinine_mg_dl": (r"(?:혈청크레아티닌|크레아티닌)\s*[:：]?\s*(\d+(?:\.\d+)?)",),
    "ast_u_l": (r"(?:AST|SGOT)\s*[:：]?\s*(\d+(?:\.\d+)?)",),
    "alt_u_l": (r"(?:ALT|SGPT)\s*[:：]?\s*(\d+(?:\.\d+)?)",),
    "gamma_gtp_u_l": (r"(?:감마[- ]?GTP|γ[- ]?GTP)\s*[:：]?\s*(\d+(?:\.\d+)?)",),
}


def extract_health_checkup_fields(ocr_text: str) -> dict[str, str | int | float]:
    """Extract an editable draft from OCR text; identity fields are never returned."""
    fields: dict[str, str | int | float] = {}
    date_match = re.search(r"(?:검진일|검진일자)\s*[:：]?\s*(20\d{2})[.\-/년]\s*(\d{1,2})[.\-/월]\s*(\d{1,2})", ocr_text)
    if date_match:
        fields["checkup_date"] = datetime(*map(int, date_match.groups())).date().isoformat()
    bp_match = re.search(r"(?:혈압|수축기\s*/\s*이완기)\s*[:：]?\s*(\d{2,3})\s*/\s*(\d{2,3})", ocr_text)
    if bp_match:
        fields["systolic_bp"] = int(bp_match.group(1))
        fields["diastolic_bp"] = int(bp_match.group(2))
    for field, patterns in FIELD_PATTERNS.items():
        for pattern in patterns:
            match = re.search(pattern, ocr_text, flags=re.IGNORECASE)
            if match:
                value = float(match.group(1))
                fields[field] = int(value) if value.is_integer() else value
                break
    return fields
