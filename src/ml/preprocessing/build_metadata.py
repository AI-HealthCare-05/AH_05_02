from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import pandas as pd

from .registry import build_registry, write_csv


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _inventory_row(dataset: str, kind: str, path: Path) -> dict[str, object]:
    present = path.exists()
    is_file = path.is_file()
    return {
        "dataset": dataset,
        "asset_kind": kind,
        "path": str(path),
        "present": present,
        "size_bytes": path.stat().st_size if is_file else "",
        "sha256": _sha256(path) if is_file else "",
        "status": "available_metadata_only" if present else "missing",
        "note": (
            "변수 목록이며 응답자 행 데이터가 아님"
            if present and kind in {"semantic_columns", "all_columns"}
            else "공식 자료 확보 필요"
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="KLoSA·KNHANES 통합 메타데이터 생성")
    parser.add_argument("--klosa-semantic", type=Path, required=True)
    parser.add_argument("--knhanes-semantic", type=Path, required=True)
    parser.add_argument("--klosa-all", type=Path)
    parser.add_argument("--knhanes-all", type=Path)
    parser.add_argument("--output-dir", type=Path, default=Path("data/metadata"))
    args = parser.parse_args()

    registry, review = build_registry(args.klosa_semantic, args.knhanes_semantic)
    write_csv(registry, args.output_dir / "unified_variable_registry.csv")
    write_csv(review, args.output_dir / "merge_review_queue.csv")

    inventory_rows = [
        _inventory_row("KLoSA", "semantic_columns", args.klosa_semantic),
        _inventory_row("KNHANES", "semantic_columns", args.knhanes_semantic),
    ]
    if args.klosa_all:
        inventory_rows.append(_inventory_row("KLoSA", "all_columns", args.klosa_all))
    if args.knhanes_all:
        inventory_rows.append(_inventory_row("KNHANES", "all_columns", args.knhanes_all))
    inventory_rows.extend(
        [
            _inventory_row("KLoSA", "respondent_raw_data", Path("data/raw/klosa")),
            _inventory_row("KLoSA", "official_codebook", Path("data/codebooks/klosa")),
            _inventory_row("KNHANES", "respondent_raw_data", Path("data/raw/knhanes")),
            _inventory_row("KNHANES", "official_codebook", Path("data/codebooks/knhanes")),
        ]
    )
    inventory = pd.DataFrame(inventory_rows)
    write_csv(inventory, args.output_dir / "source_inventory.csv")

    cohorts = pd.DataFrame(
        [
            ["model_19_plus", 19, "누적", "KNHANES 정상; KLoSA는 원 모집단 때문에 19~44세 대표 불가"],
            ["model_40_plus", 40, "누적", "KLoSA에서는 19+와 표본이 동일하거나 거의 동일할 수 있음"],
            ["model_65_plus", 65, "누적", "두 데이터 공통 비교 및 서비스 주 타깃 평가셋"],
        ],
        columns=["cohort_id", "minimum_age", "definition", "caution"],
    )
    write_csv(cohorts, args.output_dir / "cohort_definitions.csv")

    rules = pd.DataFrame(
        [
            ["Q01", "원본 불변", "원자료 해시를 기록하고 raw 파일을 덮어쓰지 않음", "block"],
            ["Q02", "코드북 승인", "approved가 아닌 변수는 모델 입력에 사용하지 않음", "block"],
            ["Q03", "결측코드", "변수별 공식 결측코드만 NA로 변환", "block"],
            ["Q04", "누수 차단", "target/target_component/진단/약물 변수를 입력에서 제외", "block"],
            ["Q05", "분할 선행", "대치·인코딩·스케일링은 학습 분할에서만 적합", "block"],
            ["Q06", "KLoSA 개인 분리", "동일 PID가 둘 이상의 split에 존재하지 않음", "block"],
            ["Q07", "KNHANES 설계", "가중치·층·PSU를 보존하고 모집단 추정 시 복합표본 반영", "warn"],
            ["Q08", "코호트 중복", "19+/40+/65+ 표본 동일 여부와 실제 최소 연령 보고", "warn"],
            ["Q09", "연도·차수", "KLoSA 차수와 연도, KNHANES 연도별 문항변경을 명시", "block"],
            ["Q10", "공통 평가", "세 모델을 동일 65+ 테스트셋에서도 비교", "block"],
        ],
        columns=["rule_id", "name", "acceptance_criterion", "severity"],
    )
    write_csv(rules, args.output_dir / "quality_rules.csv")

    summary = {
        "registry_rows": int(len(registry)),
        "approved_rows": int(registry["review_status"].isin(["approved", "approved_with_note"]).sum()),
        "blocked_until_codebook_review": int((registry["review_status"] == "needs_codebook").sum()),
        "merge_review_rows": int(len(review)),
        "high_priority_merge_reviews": int((review["review_priority"] == "high").sum()),
        "raw_data_present": False,
        "codebook_present": False,
        "pipeline_execution_status": "metadata_only_blocked",
    }
    (args.output_dir / "quality_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
