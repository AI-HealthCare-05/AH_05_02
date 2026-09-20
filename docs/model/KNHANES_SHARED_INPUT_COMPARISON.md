# KNHANES 판정 모델의 미래 예측 공통 입력 축소 실험

> 아래는 최초 sklearn 1.9.0 실험 기록이다. 현재 서비스 연동 후보는
> `KNHANES_SHARED7_SK180_REPRODUCTION.md`의 1.8.0 재학습 모델을 사용한다.
> 후속 점검에서 공식 BMI와 키·체중 계산 BMI의 결측 상태 및 값이 일치했고,
> Validation/Test 선별 결과 변경은 0건이었다. 교육 1~4 매핑은 코드북으로 확인했다.
> 초기 기록의 미확인 항목과 최신 연동 상태를 구분한다.

## 목적과 고정 조건

KLoSA 서비스 입력과 공통화할 수 있는 변수로 KNHANES 현재 위험 선별 모델을
재학습했다. 미래 발병 모델로 변경한 것이 아니며 두 모델 점수를 합치지 않는다.

- 공통 7변수: age, height_cm, weight_kg, bmi, sex, current_smoker, education
- 추가 비교: 허리둘레, 당뇨 가족력, 두 항목 모두
- 공통 7변수의 BMI는 파생 가능하므로 사용자 질문 수 7개를 의미하지 않는다.
- 음주·운동·소득은 조사 정의의 일치를 가정하지 않고 제외했다.
- BMI는 원 학습과 같은 공식 HE_BMI를 유지했다. 서비스 계산 BMI와의 정합성은 별도 과제다.
- 성별·현재 흡연·교육 코드는 KNHANES 기준이다. KLoSA API 코드와 직접 호환되지 않는다.
- 기존 v0.6.1의 Logistic/RF 하이퍼파라미터와 가중 평균 0.7/0.3을 고정했다.
- 각 축소 후보는 새로 학습했다. Train 2016~2020의 연도 그룹 5-fold OOF로
  Platt 보정기를 적합하고, 최종 기본 모델과 전처리기는 전체 Train에만 적합했다.
- 허리둘레 포함 후보는 기존과 같은 Train-only 추정기 및 내부 파생 4개를 사용했다.
  허리둘레 없는 후보에서는 추정기와 파생 4개를 모두 제외했다.
- Validation 2021~2022에서 Specificity >=0.42 중 Recall 최대, 동률이면 Specificity 최대.
- 모든 후보의 임계값 확정 후 Test 2023~2024를 평가했다. Test로 재조정하지 않았다.

## 데이터 재현

2016~2024 원본 SAV 9개 해시는 팀 전달본과 모두 일치했다. 전처리 총 67,019행,
적격 Train 26,005명/양성 1,140, Validation 9,132명/양성 415,
Test 9,691명/양성 390을 확인했다.

CSV SHA-256의 차이는 줄바꿈뿐이다. 로컬 LF 파일은
`e34ce92eba2efaeab7503db1e1f4336ebaa2b4aff0a7a562b5784bb5412cd9f2`,
CRLF 정규화 시 팀 전달본의
`70c2e4a0d71e883a4181589bfb3042413f6f6e13104756b88d24e103e195ddfa`와 정확히 일치한다.
원본 ZIP은 보존했고 SAV/CSV는 Git 제외 데이터 폴더에 보관했다.
기존 22변수 Artifact의 Validation/Test Recall·Specificity·AUROC·AUPRC와 임계값을 재현했다.

## 결과

비가중 지표. 복합표본 가중 지표·Brier·혼동행렬은 상세 JSON에 함께 기록했다.

| 후보 | 외부 변수 | 임계값 | Validation R/S | Test R/S | Test Precision | Test AUROC | Test AUPRC | Test FN/FP |
|---|---:|---:|---|---|---:|---:|---:|---|
| 기존 v0.6.1 | 22 | 0.02323125 | 0.9590 / 0.4201 | 0.9385 / 0.4066 | 0.0622 | 0.7712 | 0.1138 | 24 / 5519 |
| 공통 입력 | 7 | 0.02581767 | 0.9422 / 0.4202 | 0.9308 / 0.4131 | 0.0624 | 0.7602 | 0.1060 | 27 / 5459 |
| 공통 + 허리둘레 | 8 | 0.02591520 | 0.9349 / 0.4303 | 0.9333 / 0.4252 | 0.0637 | 0.7706 | 0.1172 | 26 / 5346 |
| 공통 + 당뇨 가족력 | 8 | 0.02650796 | 0.9446 / 0.4420 | 0.9205 / 0.4269 | 0.0631 | 0.7639 | 0.1053 | 31 / 5330 |
| 공통 + 허리둘레·가족력 | 9 | 0.02571083 | 0.9518 / 0.4482 | 0.9205 / 0.4400 | 0.0645 | 0.7754 | 0.1171 | 31 / 5209 |

## 해석과 한계

- 공통 7변수의 Test Recall 손실은 기존 대비 약 0.77%p, FN은 3건 증가했다.
- 허리둘레 포함 8변수의 Test Recall 손실은 약 0.51%p, FN 2건 증가,
  FP 173건 감소다. 이는 사후 기술 비교이며 Test에서 우승 모델을 선택한 것이 아니다.
- Validation Recall 기준 축소 후보 1위는 공통+허리둘레+가족력 9변수다.
- 추가 변수가 항상 Recall을 높이지는 않는다. 점수 순위와 Validation 최적 임계값이
  함께 달라지므로 한 후보의 단일 지표 변화로 변수의 인과적 효과를 단정하지 않는다.
- 모든 축소 후보의 이번 Test Specificity는 0.40 이상이나 향후 표본에서 보장되지 않는다.
- 원 모델에 맞춘 고정 하이퍼파라미터 비교로, 각 축소 후보의 최적 성능 탐색은 아니다.
- 기존 22변수 기준점의 과거 튜닝 이력과 축소 후보의 고정 설정이 다르다.
- Test는 반복 조회된 historical holdout이며 새 외부 검증이 아니다.
- 서비스 입력의 결측 패턴, 키·체중 자가보고, 교육 코드 매핑, 연령별 성능과 보정 검증이 남았다.
- 연구용 위험 선별·건강교육 목적이며 운영 Registry/임계값/API는 변경하지 않았다.

## 산출물과 재현

### 교육 수준 제거 추가 실험

`--education-ablation` 옵션으로 공통 7변수를 재학습해 재현하고, 교육만 제외한
6변수 모델을 같은 연도 분할·모델 설정·OOF 보정·Validation Spec>=0.42로 비교했다.
교육 변수를 결측 대치한 것이 아니라 학습 특성에서 완전히 제거했다.

| 구성 | Validation R/S | Test R/S | Test Precision | Test AUROC | Test AUPRC | FN/FP |
|---|---|---|---:|---:|---:|---|
| 공통 7변수 | 0.9422 / 0.4202 | 0.9308 / 0.4131 | 0.0623 | 0.7602 | 0.1060 | 27 / 5459 |
| 교육 제외 6변수 | 0.9446 / 0.4212 | 0.9256 / 0.4173 | 0.0624 | 0.7589 | 0.1048 | 29 / 5420 |

6변수는 age, height_cm, weight_kg, bmi, sex, current_smoker이며 임계값은
`0.02625393069430992`다. Validation Recall은 약 0.24%p 증가했으나 Test Recall은
약 0.51%p 감소했다. Test FN 2건 증가, FP 39건 감소이며 유의성·비열등성을 검정한
결과는 아니다. 질문 축소 후보로 검토할 수 있으나 운영 승인이나 성능 동등성을 뜻하지 않는다.
원본 22변수 대비 Test Recall 차이는 약 -1.28%p, FN은 24에서 29건이다.
결과 및 모델: `outputs/ml/knhanes_shared_inputs_v001/education_ablation01/`.
재현 시 아래 명령에 `--education-ablation`을 추가하고 새 출력 경로를 지정한다.

- 코드: `src/ml/evaluation/compare_knhanes_shared_inputs.py`
- 규격 테스트: `tests/ml/test_knhanes_shared_inputs.py`
- 결과: `outputs/ml/knhanes_shared_inputs_v001/run01/results.json`
- 축소 후보 4개의 모델 번들: 같은 실행 폴더의 `shared7*.joblib` (Git 제외)
- 환경: Python 3.14.6, sklearn 1.9.0, numpy 2.4.6, pandas 2.3.3, joblib 1.5.3,
  lightgbm 4.7.0, pyreadstat 1.3.5. LightGBM은 전달 모듈 import 의존성이며 후보 모델은 아니다.

팀 전달 ZIP을 검증해 해제하고 해당 의존성 환경을 준비한 뒤 저장소 루트에서 실행한다.
전처리 CSV가 필요하며 출력 폴더는 기존 결과를 덮어쓰지 않도록 새 경로를 사용한다.

```bash
python src/ml/evaluation/compare_knhanes_shared_inputs.py \
  --handoff-dir /path/to/today_v061_team \
  --output-dir outputs/ml/knhanes_shared_inputs_v001/new_run
```
