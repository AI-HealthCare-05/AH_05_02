# 작업 창구 2/5 — AI·DB

## 목적

당뇨 위험 선별·예측 모델과 AI 학습·분석에 사용하는 원천·가공 데이터를 관리한다. 여기서 DB는 서비스 운영 DB가 아니다.

## 담당과 브랜치

- 담당: 양준혁 (`Autobot1236`)
- 브랜치: `codex/ai-db-integration-20260914`
- 병합 대상: `develop`
- 선행 작업: PR #60

## 핵심 예측 모델

- **오늘이**: KNHANES 기반 현재 당뇨 신호 선별
- **내일이**: KLoSA 기반 미래 당뇨 신규 발병 위험 예측
- **모레노**: 이산시간 생존분석 기반 연령별 발병 위험 전망
  - 검증 상태에 따라 연구·선택 기능으로 구분
- **XAI**: SHAP 기반 위험·보호요인과 모델 간 결과 차이 설명

## 추가 AI·원천 데이터

- Vision AI 식단 인증: 음식·채소 포함 여부와 대략적인 시각 비율
- Clova OCR: 건강검진 결과표 추출, 구조화, 사용자 확인·수정
- KNHANES, KLoSA, Apple Health, Android Health Connect
- 건강검진 결과통보서와 검증용 합성·샘플 데이터

## 데이터·모델 관리

- 변수명·단위·범위 표준화, 결측·이상값 처리
- 학습·검증·테스트 분리와 데이터 누수 점검
- 연령·임계값·선택 입력별 성능 분석
- Recall·Specificity·PPV·NPV·Confusion Matrix
- 확률 보정·위험 범주, Artifact·전처리기·스키마·버전
- Model Registry·롤백·재현 명령

## 안전·완료 체크리스트

- [ ] 원본 의료 데이터·대용량 모델·개인정보를 Git에서 제외
- [ ] 오늘이·내일이 고정 입력 재현
- [ ] 혼동행렬과 임계값별 지표 비교
- [ ] 연령군·선택 입력 유무별 성능 확인
- [ ] OCR 결과의 사용자 확인·수정 흐름 검증
- [ ] Artifact 해시·모델 버전·입력 스키마 추적
- [ ] Model Release Gate와 관련 테스트 통과

## ver.5.6 모델 서비스 계약

PR #63의 `REQ-HC-003`, `REQ-PRED-001~005`, `NFR-001/004/006~010`을 구현 기준으로 사용한다.
Artifact·입력·출력·XAI·배포·롤백의 단일 인계 문서는
[`docs/model/V56_MODEL_SERVICE_INTEGRATION.md`](../model/V56_MODEL_SERVICE_INTEGRATION.md)다.
모델 바이너리는 Git 밖에서 SHA-256 검증 후 공급하며, 파일 존재만으로 공개 운영 상태를
활성화하지 않는다.