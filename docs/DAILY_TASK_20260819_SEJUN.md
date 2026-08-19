# 데일리 뭐하징 Daily Task(8월 19일) - 세준

## 📝 목표

- 8월 18일까지 정리된 기획·데이터·화면·API 기준을 SP2-DATA-003 실험에 반영한다.
- KLoSA와 KNHANES를 행 단위로 합치지 않고 공통 변수 의미만 조화한다.
- KLoSA 미래 신규발병 모델과 KNHANES 현재 상태 선별 모델의 축소 표본 베이스라인을 재현 가능하게 실행한다.
- 전체·연령군별 성능과 19~44세 적용 가능성을 검토해 서비스 문구와 다음 작업을 확정한다.

## 뭐 했지⁉️

- 8월 18일 팀 산출물을 저장소 문서와 대조했다.
  - 빛샘: API 기본 경로, 공통 오류 형식, 비동기 작업, ERD↔API 연결 기준을 확인했다. 최신 ERD 원본이 브랜치에 없어 엔터티·필드는 추정하지 않았다.
  - 준혁: KLoSA t0→t1 약 2년 신규발병 라벨, 기진단·결측 제외, PID 그룹 분할, 누수 변수 제외, 연령군 EDA 기준을 반영했다.
  - 수인: 미진단/기진단 흐름, 기진단자 예측 차단, `낮음·주의·높음` 화면 표시 원칙을 반영했다.
  - 세준: 요구사항 v2.0, Sprint 2 백로그, 서비스 범위·안전 문구, API 명세 기준을 반영했다.
- 실제 전처리 산출물과 메타데이터를 확인했다.
  - KLoSA: 51,807개 person-period 관측, 8,730명, 신규 당뇨 1,299건, 관찰 연령 45~105세
  - KNHANES: 미진단 성인 44,828명, 현재 당뇨 상태 양성 1,945건, 관찰 연령 19~80세
- 공통 입력 변수 대응표를 만들었다.
  - 포함: 연령, 성별, BMI, 현재 흡연, 신체활동
  - 제외: 혈당·HbA1c·진단·복약 등 타깃 직접 결정 변수
  - 보류: 음주 문항은 두 조사 정의가 다르고 KNHANES 값 라벨 확인이 필요해 제외
- seed `20260819`로 연령군·라벨 비율을 보존한 축소 표본을 생성했다.
  - train 6,000 / validation 2,000 / test 3,000
  - KLoSA는 PID 그룹 분할, KNHANES는 조사연도 시간 분할 유지
  - 입력 파일과 선택 표본은 SHA-256으로 재현성을 기록하고 개인 ID는 저장하지 않았다.
- Dummy, Logistic Regression, Random Forest를 실행하고 전체·연령군별 지표와 혼동행렬을 저장했다.
- 원본 의료 데이터와 개인 단위 행은 Git에 추가하지 않았다.
- 검증 결과: Ruff 검사 통과, 포맷 검사 통과, 데이터 전용 테스트 9개 및 전체 테스트 17개 통과.

## 생성·수정 파일과 링크

- [Draft PR #4](https://github.com/AI-HealthCare-05/AH_05_02/pull/4)
- [실행 설정](https://github.com/AI-HealthCare-05/AH_05_02/blob/feature/3-age-baseline/configs/age_baseline.json)
- [공통 변수 대응표](https://github.com/AI-HealthCare-05/AH_05_02/blob/feature/3-age-baseline/data/metadata/common_baseline_variable_mapping.csv)
- [베이스라인 실행 코드](https://github.com/AI-HealthCare-05/AH_05_02/blob/feature/3-age-baseline/src/ml/baseline/age_baseline.py)
- [테스트 코드](https://github.com/AI-HealthCare-05/AH_05_02/blob/feature/3-age-baseline/tests/ml/test_age_baseline.py)
- [실험 실행 안내](https://github.com/AI-HealthCare-05/AH_05_02/tree/feature/3-age-baseline/experiments/sp2_data_003)
- [전체 성능표](https://github.com/AI-HealthCare-05/AH_05_02/blob/feature/3-age-baseline/experiments/sp2_data_003/overall_metrics.csv)
- [연령군별 성능표](https://github.com/AI-HealthCare-05/AH_05_02/blob/feature/3-age-baseline/experiments/sp2_data_003/age_group_metrics.csv)
- [표본·해시 기록](https://github.com/AI-HealthCare-05/AH_05_02/blob/feature/3-age-baseline/experiments/sp2_data_003/sample_manifest.json)
- [상세 결과 보고서](https://github.com/AI-HealthCare-05/AH_05_02/blob/feature/3-age-baseline/docs/SP2_DATA_003_BASELINE_REPORT.md)

## 모델 성능

### 축소 test 전체 결과

| 데이터 | 문제 정의 | 모델 | AUROC | AUPRC | Recall | Specificity | F1 | Brier |
|---|---|---|---:|---:|---:|---:|---:|---:|
| KLoSA | 약 2년 후 신규 당뇨 진단 | Dummy | 0.500 | 0.025 | 0.000 | 1.000 | 0.000 | 0.024 |
| KLoSA | 약 2년 후 신규 당뇨 진단 | Logistic Regression | 0.641 | 0.042 | 0.667 | 0.597 | 0.077 | 0.237 |
| KLoSA | 약 2년 후 신규 당뇨 진단 | Random Forest | 0.581 | 0.033 | 0.027 | 0.985 | 0.033 | 0.048 |
| KNHANES | 현재 미진단 성인의 당뇨 상태 선별 | Dummy | 0.500 | 0.040 | 0.000 | 1.000 | 0.000 | 0.038 |
| KNHANES | 현재 미진단 성인의 당뇨 상태 선별 | Logistic Regression | 0.745 | 0.108 | 0.775 | 0.598 | 0.136 | 0.227 |
| KNHANES | 현재 미진단 성인의 당뇨 상태 선별 | Random Forest | 0.697 | 0.101 | 0.125 | 0.950 | 0.107 | 0.074 |

두 데이터는 타깃과 관측 구조가 달라 성능을 같은 순위표로 비교할 수 없다. 로지스틱 회귀가 이번 축소 실험에서 AUROC·AUPRC는 가장 높았지만, 클래스 가중치와 고정 임계값 0.5에서 보정 성능이 좋지 않아 현재 확률을 개인 발병확률로 표시할 수 없다.

### 연령군별 Logistic Regression test

| 데이터 | 연령군 | N/양성 | AUROC | AUPRC | Recall | Specificity | F1 |
|---|---|---:|---:|---:|---:|---:|---:|
| KLoSA | 19~44세 | 관측 없음 | - | - | - | - | - |
| KLoSA | 45~64세 | 1,510/30 | 0.672 | 0.045 | 0.400 | 0.841 | 0.087 |
| KLoSA | 65세 이상 | 1,490/45 | 0.587 | 0.045 | 0.844 | 0.346 | 0.074 |
| KNHANES | 19~44세 | 1,040/14 | 0.793 | 0.067 | 0.286 | 0.882 | 0.058 |
| KNHANES | 45~64세 | 1,146/52 | 0.735 | 0.174 | 0.750 | 0.600 | 0.147 |
| KNHANES | 65세 이상 | 814/54 | 0.594 | 0.094 | 0.926 | 0.212 | 0.142 |

KNHANES 19~44세의 test 양성은 14건뿐이다. 수치가 높아 보여도 불확실성이 크고 미래 발병 타깃이 아니므로 서비스 성능으로 확정하지 않는다.

## 결정사항

- KLoSA와 KNHANES는 각각 전처리하며 행 단위로 합치지 않는다.
- KLoSA는 미래 신규발병 모델, KNHANES는 현재 위험 신호 선별 모델로 명확히 분리한다.
- KLoSA는 연령별 모델로 나누지 않고 전체 적격 표본의 단일 모델로 학습하며 연령군은 평가 슬라이스로만 사용한다.
- KLoSA에 없는 19~44세에는 KLoSA 미래 예측을 제공하지 않는다.
- KNHANES 19~44세 결과는 현재 위험 신호 선별 연구로만 사용하고 미래 발병 예측이라고 표현하지 않는다.
- 기진단자는 예측에서 제외하고 의료기관 안내 흐름으로 전환한다.
- 모델 검증과 보정 전에는 확률을 개인의 발병확률로 제시하지 않는다.
- 19~44세 KNHANES 화면 문구:
  - “입력한 현재 건강정보를 바탕으로 당뇨 위험 신호를 선별한 참고 결과입니다. 향후 발병을 예측하거나 당뇨병을 진단하는 결과가 아닙니다.”
- KLoSA 모델 연령 범위 밖 화면 문구:
  - “현재 모델의 검증 연령 범위에 포함되지 않아 개인화 예측을 제공하지 않습니다. 일반 건강정보와 생활습관 챌린지는 이용할 수 있습니다.”

## 미완료·다음 작업

- 전체 적격 표본으로 최종 후보 모델을 재학습하고 부트스트랩 신뢰구간을 산출한다.
- validation에서 임계값·불균형 처리·확률 보정을 선택하고 test는 최종 1회만 평가한다.
- KNHANES 복합표본 가중치 반영 방법을 통계적으로 검토한다. 현재 양성률은 가중치 없는 모델 입력 행의 단순 비율이다.
- 공식 코드북으로 음주·식생활 변수의 값 라벨과 결측코드를 확인한 뒤 후보 특성을 확장한다.
- 연령군별 calibration, decision curve 또는 합의된 비용 기준을 추가한다.
- 최신 수정 ERD 원본을 저장소에 버전 관리한 뒤 API 엔드포인트·오류 형식·작업 상태 필드와 다시 대조한다.
- `docs/SPRINT2_BACKLOG.md`의 SP2-DATA-003 상태를 PR 리뷰·병합 시점에 갱신한다.
- Draft PR #4는 리뷰·CI·승인·통합 브랜치 병합 전이므로 저장소 완료 기준상 아직 병합 대기 상태다.
