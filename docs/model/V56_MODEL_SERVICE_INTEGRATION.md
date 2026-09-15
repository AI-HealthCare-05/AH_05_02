# ver.5.6 모델 서비스 연동 계약

기준 문서는 PR #63의 요구사항 정의서·API 명세서 ver.5.6이다. 관련 요구사항은
`REQ-HC-003`, `REQ-PRED-001~005`, `NFR-001`, `NFR-004`, `NFR-006~010`이다.
결과는 당뇨 진단·치료·처방이 아니라 위험 신호 선별과 건강교육에만 사용한다.

## 고정 후보와 Artifact

| 구분 | 오늘이 | 내일이 |
|---|---|---|
| 목적 | KNHANES 현재 당뇨 관련 신호 선별 | KLoSA 다음 조사 시점 신규 의사진단 위험 선별 |
| 버전 | `knhanes-shared8-waist-sk180-research-v1` | `rf25-tuned-spec40-v1` |
| 파일 | `models/artifacts/candidates/diabetes_current_screening/knhanes-shared8-waist-sk180-v1/model.joblib` | `models/artifacts/candidates/diabetes_incidence/rf25-tuned-spec40-v1/model.joblib` |
| 크기 | 6,707,324 bytes | 2,290,145 bytes |
| SHA-256 | `aceafb1011afed055da727f63c996f1e35a711e0e01f3a38c349360d2f3ee8fc` | `e5067dacd50006b8d7681ef9e558a2a3488913ae1db58d15632c842623c05bf8` |
| sklearn | 1.8.0 | 1.8.0 |
| 공개 상태 | 연구 후보, 운영 미승인 | 후보 승인, 운영 미활성 |

바이너리와 원자료는 Git에 넣지 않는다. 배포 담당자는 승인된 비Git 저장소에서 파일을
받아 Manifest 해시를 검증하면서 배치한다.

```bash
python3 scripts/provision-models.py \
  --today-shared8 /secure-handoff/today/model.joblib \
  --tomorrow /secure-handoff/tomorrow/model.joblib
```

컨테이너에는 `models/`를 읽기 전용으로 마운트한다. 운영 전환 전에는
`MODEL_PRELOAD_ENABLED=true`로 Worker가 Artifact를 역직렬화·계약 검사한 뒤에만 ready
파일을 만들게 한다. 누락, 해시 불일치, sklearn 버전 불일치는 시작 실패로 처리하며 다른
모델이나 낮음 결과로 자동 대체하지 않는다.

## 입력 계약

공통 필수 외부 입력은 생년월일, 성별, 키(cm), 체중(kg), 흡연 상태, 현재 음주 여부,
규칙적 운동 여부, 주당 운동일, 회당 운동시간, 기존 당뇨 진단 여부다. BMI와 만 나이는
서버에서 계산한다. 기존 진단자는 모델 입력에서 제외하고 의료기관 안내로 분기한다.
기술적 적용 연령은 만 45~105세다.

오늘이는 허리둘레(cm)를 추가로 사용한다. 허용 범위는 45~160이며, 누락 시 Train fold에서만
학습된 추정기를 사용한다. 실측값은 덮어쓰지 않는다. 교육 `code_97`은 별도 학력으로 해석하지
않고 missing으로 전달한다.

내일이는 Manifest의 고정 25변수 순서를 사용한다. 선택 수치형은 Train 중앙값과 missing
indicator, 선택 범주형은 Train 최빈값으로 처리한다. 진단력 null은 `false`가 아니라 missing이다.
연소득 단위는 만원/년이고 범위는 0~123,500이다. 미래 차수 진단·치료 변수는 입력하지 않는다.

## 출력과 성능 계약

모델 내부 경계 이름 `caution`은 Artifact 재현을 위해 보존한다. ver.5.6 공개 API는
`low/moderate/high`를 반환하며 화면은 `낮음/주의/높음`으로 표시한다. 공개 직렬화 경계에서만
`caution -> moderate`로 변환한다. 점수는 진단 확률 또는 확정 발병률로 표시하지 않는다.

- 오늘이 경계: `0.025988709910244948`
- 내일이 moderate 경계: `0.017113354352510553`
- 내일이 high 경계: `0.021153602801262862`

| 모델 | N | prevalence | TP/FN/TN/FP | Recall | Specificity | PPV | NPV | Positive rate | AUROC | AUPRC |
|---|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|
| 오늘이 | 9,691 | 0.04024 | 364/26/3,985/5,316 | 0.93333 | 0.42845 | 0.06408 | 0.99352 | 0.58611 | 0.77115 | 0.11746 |
| 내일이 high | 7,903 | 0.02467 | 164/31/3,102/4,606 | 0.84103 | 0.40244 | 0.03438 | 0.99011 | 0.60357 | 0.66356 | 0.04855 |

데이터와 라벨이 달라 두 행을 동일 모집단의 직접 우열로 해석하지 않는다.

## XAI와 결과 충돌

오늘이는 최종 보정 앙상블 출력에 grouped Shapley, 내일이는 RF positive class에 TreeSHAP을
적용한다. 설명은 위험 방향 2개와 보호 방향 1개 또는 그 반대로 선택한다. 이는 인과관계,
치료효과 또는 약물 권고가 아니다. 설명 실패는 기본 예측을 실패시키지 않고 빈 요인과
`explanation_status=unavailable`을 반환한다.

현재 XAI는 연구용이며 `display_allowed=false`다. 공개 risk-factors API는 승인된 설명 저장
경로가 생기기 전까지 빈 목록을 반환한다. 두 모델이 다르면 현재 신호와 미래 신호의 목적이
다름을 설명하며 어느 한 결과로 다른 결과를 배제하지 않는다.

## 운영 설정과 Release Gate

기본값은 Artifact가 없는 환경을 중단시키지 않도록 유지한다. 실제 전환은 App과 Worker에
동일한 환경변수를 한 번에 배포하고 readiness를 확인한 뒤 수행한다.

```dotenv
PREDICTION_PROVIDER=artifact
MODEL_URI=/app/models/artifacts/candidates/diabetes_incidence/rf25-tuned-spec40-v1/model.joblib
MODEL_MANIFEST_URI=/app/models/registry/diabetes_incidence/candidates/rf25-tuned-spec40-v1.json
CURRENT_SCREENING_RUNTIME=shared8-waist
ML_SHARED8_MODEL_URI=/app/models/artifacts/candidates/diabetes_current_screening/knhanes-shared8-waist-sk180-v1/model.joblib
ML_RF25_MODEL_URI=/app/models/artifacts/candidates/diabetes_incidence/rf25-tuned-spec40-v1/model.joblib
MODEL_PRELOAD_ENABLED=true
PREDICTION_OPERATIONAL_MODEL_ACTIVATED=false
CURRENT_SCREENING_OPERATIONAL_MODEL_ACTIVATED=false
```

마지막 두 플래그는 Artifact 존재만으로 켜지지 않는다. 의료·운영 검토, 외부/wave 검증,
성능·공정성 검토와 롤백 훈련이 끝난 별도 승인 PR에서만 `true`로 바꾼다.

Release Gate는 다음을 모두 요구한다.

1. 파일 크기·SHA-256·sklearn 1.8.0 계약 일치
2. 고정 입력 반복 결과와 feature 순서 일치
3. App 요청 provenance와 Worker 실제 결과 provenance 일치
4. 누락·범위·기진단·지원 연령 밖 요청의 fail-closed 확인
5. 공개 category low/moderate/high와 화면 텍스트 라벨 병기
6. 기본 추론과 XAI 분리, cold-start·queue·DB 포함 end-to-end 시간 측정
7. 원본 데이터·Artifact·환경 비밀정보 Git 제외 확인
8. 직전 승인 버전과 Artifact URI로 되돌리는 롤백 절차 검증

현재 상태는 연구·서비스 연동 준비이며 공개 운영 승인은 보류다.
