# 만성질환 프로젝트 조사자료 및 전처리 종합본

> 정리 기준일: 2026년 8월 11일  
> 범위: 현재 확인 가능한 문헌·데이터·서비스 사례·전처리 기준과 2조의 기획 산출물  
> 주의: 논문, 데이터셋, 서비스 사례, 전처리 결과, 모델 성능을 서로 구분하여 정리함.

## 바로가기

- [2조 KLoSA 조사 기록](https://app.notion.com/p/2-3aacaf5650aa80898f5ad3e26fe844af?p=3b8caf5650aa80d78a72cb2af1c37598&pm=s)
- [2조 ERD 조사 기록](https://app.notion.com/p/2-3aacaf5650aa80898f5ad3e26fe844af?p=3b9caf5650aa806584ddfecd5804d3d7&pm=s)
- [2조 페르소나 조사 기록](https://app.notion.com/p/2-3aacaf5650aa80898f5ad3e26fe844af?p=3b9caf5650aa8026babec6759b6934ee&pm=s)
- [2조 요구사항 조사 기록](https://app.notion.com/p/2-3aacaf5650aa80898f5ad3e26fe844af?p=3b9caf5650aa808c8426c6f92064a6ff&pm=s)
- [2조 GitHub 저장소](https://github.com/J36-Ai-Editer/chronic-disease-lifestyle-challenge)

---

## 1. 프로젝트 공통 방향

### 프로젝트명

**만성질환 생활습관 챌린지 웹서비스**

### 목표

- 공개 의료·건강 데이터를 활용해 만성질환 발병 위험을 선별하는 AI 모델 개발
- 사용자의 건강검진·생활습관 입력을 기반으로 위험도와 주요 요인 제공
- 생활습관 챌린지 수행 기록과 재평가 결과를 대시보드로 시각화
- 고위험 또는 서비스 부적합 사용자는 검사·의료기관 방문 안내로 전환

### 의료·AI 안전 원칙

- 예측 결과는 **진단이나 처방이 아니라 위험 선별·건강교육**으로 표현함.
- 약물의 시작·중단·용량 변경을 추천하지 않음.
- 고위험 결과에는 검사 또는 의료기관 방문 권고를 함께 제공함.
- 모델이 사용한 근거와 주요 위험·보호 요인을 설명함.
- 건강정보 처리 동의, 최소수집, 계정정보·건강정보 분리, 암호화 저장을 반영함.

---

## 2. 데이터 후보 종합

### 2-1. 국내 공공데이터

| 데이터 | 성격 | 프로젝트 활용 | 주요 주의사항 |
| --- | --- | --- | --- |
| [국민건강영양조사(KNHANES)](https://knhanes.kdca.go.kr/knhanes/main.do) | 반복 단면조사 | 혈당·HbA1c·혈압·신체계측·생활습관 기반 위험 선별 | 연도별 코드북, 조사 가중치, 공복시간 확인 필요 |
| [고령화연구패널조사(KLoSA)](https://survey.keis.or.kr/klosa/klosa04.jsp) | 종단 패널조사 | 고령자의 건강 변화와 신규 만성질환 발생 추적 | 패널 탈락, 차수별 문항 차이, 개인 단위 데이터 분리 필요 |
| [지역사회건강조사(CHS)](https://chs.kdca.go.kr/chs/rawDta/rawDtaPrncplMain.do) | 지역 단위 단면조사 | 생활습관·진단 경험·지역별 현황 분석 | 자가보고 변수의 한계 확인 필요 |
| [국민건강보험 자료공유서비스](https://nhiss.nhis.or.kr/) | 검진·진료 행정자료 | 만성질환 발생과 의료이용의 장기 연구 | 신청·심의·분석환경·반출 제한 확인 필요 |
| [KOSIS](https://kosis.kr/) | 집계 통계 | 유병률·연령별 분포·정책 배경 근거 | 개인 단위 모델 학습자료와 구분해야 함 |
| [AIHub 만성질환 임상·생활습관 데이터](https://aihub.or.kr/aihubdata/data/view.do?srchOptnCnd=OPTNCND001&currMenu=115&topMenu=100&searchKeyword=%EB%A7%8C%EC%84%B1%EC%A7%88%ED%99%98&aihubDataSe=data&dataSetSn=71335) | 임상·생활습관 데이터 | 만성질환 모델 후보 | 신청 조건과 라이선스 확인 필요 |
| [AIHub 당뇨병·합병증 추적관찰 데이터](https://aihub.or.kr/aihubdata/data/view.do?srchOptnCnd=OPTNCND001&currMenu=115&topMenu=100&searchKeyword=%EB%A7%8C%EC%84%B1%EC%A7%88%ED%99%98&aihubDataSe=data&dataSetSn=600) | 추적관찰 임상자료 | 당뇨·합병증 분석 후보 | 서비스 타깃과 변수 공개 범위 확인 필요 |

### 2-2. 공개 실험 데이터

| 데이터 | 활용 | 주의사항 |
| --- | --- | --- |
| [당뇨·고혈압·뇌졸중 데이터](https://www.kaggle.com/datasets/prosperchuks/health-dataset) | 다질환 분류 예비 실험 | 원출처·대표성·라이선스 검토 |
| [Diabetes Health Indicators](https://www.kaggle.com/code/alexteboul/diabetes-health-indicators-dataset-notebook) | 당뇨 위험 베이스라인 | 원출처와 변수 정의 확인 |
| [Cardiovascular Disease Dataset](https://www.kaggle.com/datasets/sulianova/cardiovascular-disease-dataset) | 심혈관·고혈압 예비 분석 | 국내 적용 가능성과 임상 타당성 검토 |

---

## 3. KLoSA 1~10차 데이터 정리 — 양준혁

| 항목 | 내용 |
| --- | --- |
| 정식 명칭 | 고령화연구패널조사(KLoSA) 1~10차 기본조사 |
| 조사기관 | 한국고용정보원 |
| 조사기간 | 2006~2024년 짝수 연도, 총 10차 기본조사 |
| 최초 대상 | 2006년 당시 제주도를 제외한 지역의 일반가구 거주 45세 이상 중·고령자 |
| 조사 방식 | 동일 대상자를 반복 조사하는 종단 패널 |
| 조사 영역 | 인구학적 배경, 가족관계, 건강, 고용, 소득·소비, 자산, 기대감, 삶의 질 |
| 제공 자료 | 원자료, 구조변환 자료, 라이트 버전, 설문지, 코드북, 유저가이드 |
| 공식 링크 | [조사개요](https://survey.keis.or.kr/klosa/klosa04.jsp) · [자료받기](https://survey.keis.or.kr/klosa/klosadownload/List.jsp) · [유저가이드](https://survey.keis.or.kr/klosa/klosaguide/List.jsp) |

### 활용 방향

- 고령자의 만성질환과 건강·생활습관 변화를 차수별로 추적함.
- 고혈압·당뇨·심장질환·뇌혈관질환 등 다중 만성질환 분석에 활용함.
- 국민건강영양조사의 단면자료 한계를 보완하는 패널자료로 검토함.
- `person_id`, 조사 차수, 조사연도를 기준으로 long format을 구성함.

### 전처리 필수사항

- [ ] 차수별 코드북과 변수 대응표 작성
- [ ] 동일 개념이지만 이름이나 코드가 다른 변수 표준화
- [ ] 패널 탈락과 차수별 결측 패턴 확인
- [ ] 신규 발병 예측 시 예측 시점 이후 정보 제거
- [ ] 동일인이 서로 다른 학습·검증·테스트 세트에 포함되지 않도록 개인 단위 분리
- [ ] 현재 보유 질환 분류와 미래 신규 발병 예측을 구분
- [ ] 1~10차 전체 또는 최근 차수만 사용할지 결정

### 현재 판단

- 고령자·다중 만성질환을 핵심 타깃으로 확정하면 KLoSA가 적합함.
- 전당뇨·미진단 당뇨 위험 선별이 핵심이면 혈액검사 변수가 있는 KNHANES가 우선 후보임.
- 두 데이터를 단순 결합하기보다 **주 데이터셋과 보조 검증·근거 데이터셋으로 역할을 분리**하는 것이 안전함.

---

## 4. 국민건강영양조사 통합 및 전처리 참고

### 4-1. 1차 통합 현황

- 입력 파일: `hn98_all.csv`부터 `hn24_all.csv`까지 21개 파일
- 조사연도: 1998, 2001, 2005, 2007~2024년
- 전체 표본: 251,455행
- 결합 방식: 연도별 자료를 가로 결합하지 않고 세로 결합
- 결과 컬럼: 26개
- 추적용 컬럼: `record_key`, `source_survey_year`, `source_file`, `source_row_number`

> “연도마다 참여자 ID가 독립적이므로, 같은 사람을 기준으로 가로 결합하지 않았다. 모든 자료를 연도 정보와 함께 세로로 이어 붙였다.”

### 4-2. 공통 컬럼

| 영역 | 컬럼 |
| --- | --- |
| 기본정보 | `sex`, `age`, `region`, `town_t` |
| 신체측정 | `height_cm`, `weight_kg`, `bmi`, `waist_cm` |
| 혈압·혈액검사 | `systolic_bp`, `diastolic_bp`, `fasting_glucose_mg_dl`, `hba1c_pct`, `total_cholesterol_mg_dl`, `hdl_cholesterol_mg_dl`, `triglyceride_mg_dl` |
| 생활습관·가족력 | `aerobic_activity`, `current_smoking`, `stress_level`, `family_history_diabetes` |
| 영양 | `energy_kcal`, `sodium_mg`, `sugar_g` |

### 4-3. 2016~2024년·만 19세 이상 예비 표본

| 단계 | 조건 | 행 수 |
| --- | --- | --- |
| 원본 | 1998~2024년 전체 | 251,455 |
| 연도 필터 | 2016~2024년 | 67,019 |
| 연령 필터 | 만 19세 이상 | 55,342 |

> 2016~2024년·만 19세 이상 범위는 확정된 최종 기준이 아니라 검토용 권장안임.

### 4-4. 현재 결측 처리

| 컬럼 | 원래 값 | 처리 | 건수 | 근거 |
| --- | --- | --- | --- | --- |
| `family_history_diabetes` | `9` | `NaN` | 4,052 | 0·1 이진 변수에서 허용되지 않는 값으로 판단 |

- 처리 후 당뇨 가족력 결측률: 12.23%
- 전체 주요 변수의 결측률은 대체로 4~12% 수준
- 영양과 가족력 항목의 결측률이 상대적으로 높음

### 4-5. 결측 처리하지 않은 값

- 체중·허리둘레·혈당·HbA1c 등의 `66`, `77`, `88`, `99`는 실제 측정값일 수 있어 유지함.
- `region=9`는 정상 지역 코드이므로 유지함.
- `energy_kcal=26,079`, `triglyceride_mg_dl=3,367` 등의 극단값도 코드북과 임상 기준 확인 전까지 유지함.

> “값의 크기만 보고 지웠다면 실제 정상·경계·당뇨 범위의 표본을 대량으로 잘못 삭제했을 것이다.”

> “이 항목들은 연도별 코드북에서 해당 변수의 결측 코드가 몇 번인지 확인한 뒤에만 처리해야 한다.”

### 4-6. 전처리 확정 체크리스트

- [ ] 연도별 공식 코드북 확보
- [ ] 변수명·단위·응답 코드 대응표 작성
- [ ] 부·모·형제자매 당뇨 가족력 변수 분리 및 `family_history_any` 정의
- [ ] 공복시간 변수와 공복혈당의 유효성 확인
- [ ] 약물 복용·기진단 변수 확보
- [ ] 타깃 정의 후 진단·약물·검사 결과의 데이터 누수 검토
- [ ] 이상치 제거·클리핑·윈저라이징 기준 확정
- [ ] 조사 가중치 사용 여부 결정
- [ ] 학습·검증·테스트 분리 후 결측 대치·스케일링·특징 선택 수행
- [ ] 전처리 파이프라인과 처리 로그 저장

### 4-7. 원문 사본

- [통합 전처리 요약](https://drive.google.com/file/d/1ubXxXu94C8F18_OC-Jc0qewZt1mMc0H7/view)
- [2016~2024년·만 19세 이상 전처리 기준](https://drive.google.com/file/d/1lAmjmp3zuD54dzgn1_u-J6g7Yoq2cQVq/view)

---

## 5. 참고문헌

### 5-1. 당뇨·전당뇨

- 「기계학습과 딥러닝을 활용한 당뇨병 조기 예측 모델 개발 및 최적화 연구」
- 「빅데이터 기반 2형 당뇨 예측 알고리즘 개발」(심현·김현욱, 2023)
- [A Simple Screening Score for Diabetes for the Korean Population](https://diabetesjournals.org/care/article/35/8/1723/29861/A-Simple-Screening-Score-for-Diabetes-for-the)
- [Scientific Reports 2023 당뇨 예측 연구](https://www.nature.com/articles/s41598-023-40170-0)
- [Deep learning–based prediction using a nationwide cohort](https://e-dmj.org/journal/view.php?doi=10.4093/dmj.2020.0081)
- [Family history and diabetes risk](https://www.nature.com/articles/s41598-018-34411-w)

### 5-2. 고혈압·심뇌혈관·대사증후군

- 「만성질환 여부에 따른 운동이 심뇌혈관 진단에 미치는 영향」(김남수·김동욱, 2025)
- 「국민건강보험 빅데이터를 활용한 주요 만성질환 발생률 예측모형의 개발과 활용」(이상연 외, 2023)
- [2022 Korean Hypertension Guideline](https://pmc.ncbi.nlm.nih.gov/articles/PMC9930285/)
- [Korean Diabetes Association Clinical Practice Guidelines](https://pmc.ncbi.nlm.nih.gov/articles/PMC11307112/)
- [Korean Society for the Study of Obesity Guideline](https://pmc.ncbi.nlm.nih.gov/articles/PMC10088549/)
- [Korean Metabolic Syndrome Fact Sheet](https://pc.e-cmsj.org/DOIx.php?id=10.51789%2Fcmsj.2024.4.e14)
- [Harmonizing the Metabolic Syndrome](https://doi.org/10.1161/CIRCULATIONAHA.109.192644)
- [KNHANES 기반 대사증후군 연구](https://pmc.ncbi.nlm.nih.gov/articles/PMC10193438/)

### 5-3. 노인·다중 만성질환

- 「기계학습 기반 노인 건강 및 만성질환 예측에 관한 분석」
  - 데이터: 2020년 제8차 KLoSA
  - 분석 대상: 4,652명
  - 입력 변수: 약 143~144개
  - 예측 질환: 고혈압·당뇨병·암·폐질환·간질환·심장질환·뇌혈관질환·치매 등 12개

#### 해당 문헌의 모델 결과

| 모델 | 결과 |
| --- | --- |
| GA 특징 선택 + XGBoost | Macro F1 약 0.738 |
| GA 특징 선택 + Random Forest | Macro F1 약 0.724 |

> 위 표는 참고문헌이 아니라 해당 논문의 실험 결과임.

### 5-4. 파생지표

- [TyG index](https://pubmed.ncbi.nlm.nih.gov/20484475/)
- [HOMA index](https://pubmed.ncbi.nlm.nih.gov/3899825/)
- [Waist-to-height ratio review](https://pubmed.ncbi.nlm.nih.gov/22106927/)
- [Waist-to-height ratio comparison](https://pubmed.ncbi.nlm.nih.gov/19638708/)
- [한국인 생애주기별 혈압 연구](https://koreascience.or.kr/article/JAKO202231159523551.page)

---

## 6. 서비스 사례 및 생활습관 자료

| 자료 | 활용 |
| --- | --- |
| [Omada Health](https://www.omadahealth.com/) | 개인별 행동 변화·코칭·장기 추적 구조 |
| [CDC National DPP](https://www.cdc.gov/diabetes-prevention/hcp/lifestyle-change-program/program-details.html) | 전당뇨 위험군 생활습관 프로그램과 성과관리 기준 |
| [국민체력100 운동처방 동영상 API](https://www.data.go.kr/tcs/dss/selectApiDataDetailView.do?publicDataPk=15108938) | 챌린지 운동 콘텐츠 연동 |
| [고혈압 관리와 스마트워치 관련 연구](https://www.kci.go.kr/kciportal/ci/sereArticleSearch/ciSereArtiView.kci?sereArticleSearchBean.artiId=ART003038473) | 웨어러블 기반 건강 모니터링 |
| [생활습관과 혈당 관련 연구](https://www.kci.go.kr/kciportal/ci/sereArticleSearch/ciSereArtiView.kci?sereArticleSearchBean.artiId=ART002524486) | 혈당 관련 챌린지 근거 |
| [혈압 조절 관련 연구](https://www.kci.go.kr/kciportal/ci/sereArticleSearch/ciSereArtiView.kci?sereArticleSearchBean.artiId=ART002724952) | 고혈압 행동 목표 설계 |

---

## 7. 페르소나 및 와이어프레임 — 이수인

### 페르소나 분류

| 라벨 | 대상 | 화면 설계 시 고려사항 |
| --- | --- | --- |
| A-1 | 건강검진 결과가 있는 미진단 사용자 | 검진 결과 입력 후 위험 예측 |
| A-2 | 건강검진 결과가 없는 미진단 사용자 | 간편 설문과 검진 권고 |
| B-1 | 고령 사용자 | 큰 글씨·쉬운 용어·단순한 입력 |
| C-1 | 2형 당뇨병 미진단 고위험 사용자 | 혈당·HbA1c·가족력·비만 중심 결과 |
| C-2 | 고혈압 미진단 고위험 사용자 | 혈압·흡연·음주·활동·체중 중심 결과 |

### 1차 기준

- 주 페르소나: **A-1 + C-1**
- 보조 페르소나: **A-2 + C-1**
- 접근성 검토: **B-1 + C-1**

### 필수 화면

1. 서비스 소개와 의료적 한계 안내
2. 회원가입·건강정보 처리 동의
3. 대상자 적합성 확인
4. 건강검진 결과 보유 여부 선택
5. 건강검진·생활습관 입력
6. 위험도와 위험·보호 요인
7. 검사·의료기관 방문 안내
8. 추천 챌린지 선택
9. 일일 챌린지 기록
10. 위험도·생활습관 추적 대시보드

---

## 8. ERD — 박빛샘

### 핵심 엔터티

| 영역 | 엔터티 |
| --- | --- |
| 계정·동의 | `User`, `Consent`, `EligibilityCheck` |
| 건강정보 | `UserProfile`, `HealthCheckup` |
| AI 예측 | `Prediction`, `RiskFactor` |
| 챌린지 | `Challenge`, `ChallengeRecommendationRule`, `ChallengeCycle`, `UserChallenge`, `ChallengeLog` |
| 추적·안내 | `FollowUpAction`, `Recommendation` |

### 주요 설계 결정

- 건강검진 1건에 여러 모델 예측을 허용하고 최신 결과를 표시함.
- 위험도 변화는 최초·최신 예측값을 조회 시 계산함.
- 4주 챌린지는 `ChallengeCycle`로 별도 관리함.
- 기진단 확인 시 기존 기록을 삭제하지 않고 새 부적합 이력을 추가함.
- 적합성 확인·예측 결과 중 권고 발생 위치를 `trigger_source`로 구분함.
- 건강정보와 계정정보를 분리함.

### 보완사항

- [ ] `Prediction.checkup_id`와 최신 결과 판정 기준
- [ ] 컬럼명 오탈자와 명명 규칙 통일
- [ ] 민감정보 암호화·보관·삭제 정책
- [ ] 건강검진 입력 컬럼과 모델 입력 변수 일치
- [ ] 개인정보 최소수집 검토

---

## 9. 요구사항 정의 — 정세준

### 서비스 방향

- 사용자 후보: 40세 이상 만성질환 고위험군 및 초기 관리군
- 서비스 질환 범위: 당뇨병·고혈압
- MVP 예측 모델: 우선 질환 1개에 집중
- 문제 배경 후보 수치: 성인 고혈압 유병률 20.0%, 당뇨병 유병률 9.4%, 고혈압 조절률 50.4%, 당뇨병 조절률 24.2%

> 위 수치는 요구사항 정의서에 사용하기 전에 질병관리청 원문의 지표 정의·연령 기준·발표연도와 URL을 확인해야 함.

### 기능 우선순위

| 우선순위 | 기능 |
| --- | --- |
| 필수 | 만성질환 위험 예측 |
| 필수 | 위험도·생활습관 추적 대시보드 |
| 필수 | 생활습관 챌린지 |
| 축소 검토 | LLM 기반 설명·예방 행동 문구 |
| 후순위 | 앱 내부 알림 |
| 후순위 또는 제외 | 이미지 기반 식단 분석 |

### 비기능 요구사항

- 개인정보와 건강정보 보호
- 입력값 검증과 일관된 오류 응답
- 모델 버전·예측시각·입력기록 추적
- 접근성과 고령자 사용성
- 위험도 계산·대시보드 응답 성능
- 의료 안전 문구와 병원 방문 안내

---

## 10. AI 모델 및 평가 기준

| 영역 | 기준 |
| --- | --- |
| 베이스라인 | Logistic Regression |
| 비교 모델 | Random Forest, XGBoost, LightGBM |
| 설명 가능성 | SHAP 기반 위험·보호 요인 |
| 분류 성능 | AUROC, AUPRC, 민감도, 특이도, F1 |
| 확률 신뢰성 | Brier score, Calibration curve |
| 불균형 대응 | 클래스 비율 확인, AUPRC·민감도 중심 비교 |
| 하위집단 평가 | 연령·성별 등 집단별 성능 확인 |
| 안전성 | 진단·처방이 아닌 위험 선별로 출력 |

### 모델 개발 시 필수 점검

- [ ] 타깃 라벨을 먼저 명확히 정의
- [ ] 타깃을 직접 결정하는 검사·진단 변수를 입력에서 제외할지 검토
- [ ] 전처리 통계와 특징 선택은 학습 세트에서만 학습
- [ ] 모델 버전과 학습 데이터 버전 기록
- [ ] 재현 가능한 설정과 실험 결과 저장
- [ ] 하위집단별 성능과 오분류 사례 검토

---

## 11. 4개 기획 문서 반영표

| 문서 | 반영할 핵심 내용 |
| --- | --- |
| 요구사항 정의서 | 문제 정의, 사용자, 기능·비기능 요구사항, 의료 안전, 우선순위, 완료 조건 |
| ERD | 계정·동의·건강검진·예측·위험요인·챌린지·추적 엔터티와 관계 |
| API 명세서 | 적합성 확인, 건강정보 입력, 예측, 최신 결과, 챌린지, 대시보드, 오류 응답 |
| 와이어프레임 | 온보딩, 동의, 적합성, 입력, 예측 결과, 챌린지, 추적, 병원 안내 |

---

## 12. 현재 결정안과 남은 결정

### 현재 공통안

- 질환 범위는 당뇨병·고혈압으로 열어두되 MVP 모델은 1개 질환부터 구현함.
- 건강검진 결과가 있는 미진단 고위험 사용자를 주 사용자로 검토함.
- 검진 결과가 없는 사용자는 간편 설문 후 검진 권고를 제공함.
- 필수 기능은 위험 예측·추적 대시보드·생활습관 챌린지임.
- 과거 기록은 삭제하지 않고 이력으로 보존함.

### 회의에서 확정할 항목

- [ ] 핵심 질환: 당뇨병 또는 고혈압
- [ ] 핵심 사용자 연령과 미진단·초기관리 범위
- [ ] 예측 문제: 현재 위험 선별 또는 미래 신규 발병
- [ ] 주 데이터: KNHANES 또는 KLoSA
- [ ] 최종 타깃 라벨과 입력 변수
- [ ] 건강검진 자료가 없는 사용자의 예측 제공 범위
- [ ] LLM 설명 기능의 Sprint 포함 여부
- [ ] 개인정보 보관·철회·삭제 정책

---

## 13. 서지정보 보완 필요

- 「기계학습과 딥러닝을 활용한 당뇨병 조기 예측 모델 개발 및 최적화 연구」의 저자·연도·학술지·DOI
- 「기계학습 기반 노인 건강 및 만성질환 예측에 관한 분석」의 저자·연도·기관·원문 링크
- 질병관리청 「2025 만성질환 현황과 이슈」의 공식 원문 링크
- KLoSA 차수별 코드북과 통합 변수 대응표
- 비어 있는 ‘머신러닝 통풍 예측’ 자료의 정확한 문헌정보
- 접근권한이 없거나 첨부파일 내부에만 있는 문헌은 추가 확인 필요
