# KNHANES 허리둘레 추정 결합 실험

## 결론

- 키·체중을 중심으로 나이·성별을 보조 입력한 허리둘레 추정기를 당뇨 선별 파이프라인 안에 추가했다.
- 실측 허리둘레는 절대 덮어쓰지 않고, 허리둘레가 없을 때만 훈련 fold에서 학습한 추정값으로 보완한다.
- `허리/키`, `추정 여부`, `실측 또는 보완 허리−기대 허리`를 내부 파생 변수로 사용한다.
- v0.6.1은 탐색적 Test에서 Recall 0.9385로 v0.5.0의 0.9308보다 0.77%p 높았고 FN은 27명에서 24명으로 감소했다.
- Validation Recall은 0.9614에서 0.9590으로 소폭 낮아져 v0.6.1을 운영 모델로 승격하지 않고 내부 challenger로 유지한다.

## 허리둘레 추정 성능

Train 2016~2020년을 조사연도 단위 OOF로 평가했다.

| 방법 | MAE | RMSE | R² | 평균 편향 |
|---|---:|---:|---:|---:|
| 학습 fold 중앙값 | 8.30cm | 10.34cm | -0.005 | -0.14cm |
| 신체계측 HGB 추정 | **3.06cm** | **3.97cm** | **0.852** | -0.004cm |

허리둘레 결측률은 Train 0.31%, Validation 2.49%, Test 2.51%였다. 결측 규모가 작아 추정기만으로 전체 성능이 크게 오를 수는 없다.

## 당뇨 선별 성능 비교

| 버전 | Validation Recall / Spec. | Test Recall / Spec. | Test AUPRC | TP / FN |
|---|---:|---:|---:|---:|
| v0.5.0 | **0.9614 / 0.4201** | 0.9308 / 0.4067 | 0.1122 | 363 / 27 |
| v0.6.0 | 0.9590 / 0.4219 | 0.9359 / 0.4149 | 0.1116 | 365 / 25 |
| v0.6.1 | 0.9590 / 0.4201 | **0.9385 / 0.4066** | **0.1138** | **366 / 24** |

Test는 이전 실험에서 이미 여러 차례 확인했으므로 위 차이는 독립적인 최종 검증 성능이 아니라 탐색적 감사 결과다. 다음 미사용 연도 또는 외부 코호트로 재검증해야 한다.

## 1조 방법론 반영

- 1조 공개 프로토콜의 시간 외부검증, OOF Platt 보정, Brier·AUPRC 동시 점검 원칙을 유지했다.
- 1조 6개 입력 complete-case 모델은 허리둘레를 사용하지 않으므로 별도 간소 입력 비교군으로만 다룬다.
- 타 조의 점수·모델 파일·원자료는 가져오지 않고 공개된 방법만 현재 KNHANES 분할에서 독립 재현한다.

## 안전 및 배포 조건

- 혈당, HbA1c, 당뇨 진단·투약 변수는 입력에서 제외했다.
- 결과는 현재 위험 신호 선별 보조용이며 진단이나 미래 발병확률이 아니다.
- 허리둘레 추정값을 사용자에게 실측값처럼 표시하지 않는다.
- 실제 허리둘레 입력이 가능하면 항상 실측값을 우선한다.
- v0.6.1은 추가 시간 외부검증 전까지 내부 challenger로 유지한다.

## 재현

```bash
python -m src.ml.modeling.knhanes_current_screening \
  --config configs/knhanes_current_screening_recall_v061.json \
  --output-dir experiments/diabetes_current_screening/challenger_v061 \
  --model-output-dir outputs/ml/knhanes_current_screening_recall_v061
python -m pytest tests/ml/test_knhanes_current_screening.py -q
```
