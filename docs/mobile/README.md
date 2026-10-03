# 간당간당 모바일 앱 — 팀원 실행 안내

원격 `develop`의 `8364a21753fe5f55740423af92fc92af5f88e0ca`를 기준으로 기존 웹서비스를 Capacitor 8.5.2 Android/iOS 앱으로 패키징하고, 모바일 화면·당근의 숲·챌린지·분석 결과를 개선한 버전이다. 앱 ID는 `life.dangno.app`이다.

## 실행 문서

| 환경 | 문서 | 서버 연결 |
| --- | --- | --- |
| Android + 개발 PC | [Android 가이드](ANDROID_DEVICE_GUIDE.md) | 로컬 API + USB/무선 ADB reverse, 또는 팀 HTTPS API |
| iPhone + Mac/Xcode | [iOS 가이드](IOS_DEVICE_GUIDE.md) | 팀 HTTPS API 또는 인증서를 신뢰한 개발 HTTPS API |
| APK만 받는 Android 팀원 / 서버 담당자 | [별도 파일 목록·서버 준비](TEAM_HANDOFF.md) | APK에 빌드된 API 주소 확인 필수 |
| 날짜별 기존 작업 기록 | [LOCAL_DEVELOPMENT.md](LOCAL_DEVELOPMENT.md) | 당시 환경·검증 기록이며 최신 절차는 위 문서 우선 |

앱 화면과 게임 자산은 번들에 포함된다. **로그인·건강정보·예측·SHAP·사진 판정에는 실행 중인 서버가 필요하다.** 기본 빌드는 `https://dang-no.life`, 로컬 빌드는 `http://127.0.0.1:8000`을 사용한다. 기존 도메인의 현재 가용성을 보장하지 않으므로 서버의 `/api/v1/health`, `/api/v1/ready`부터 확인한다.

## 공통 준비

저장소를 clone하고 PR 브랜치를 checkout한다. 모든 명령은 저장소 루트에서 실행한다.

```sh
git clone https://github.com/AI-HealthCare-05/AH_05_02.git
cd AH_05_02
git fetch origin
git switch --track origin/codex/local-mobile-development
npm install --global pnpm@11.19.0
pnpm install --frozen-lockfile
pnpm test:mobile
```

Node.js 22 이상, pnpm 11.19.0을 사용한다. Android Studio 2025.2.1 이상, iOS는 macOS·Xcode 26 이상이 필요하다. [Capacitor 8 공식 환경 설정](https://capacitorjs.com/docs/getting-started/environment-setup).

## 구현 상태

- Android/iOS 프로젝트, API 경로 변환, 네이티브 카메라·사진 선택, 시스템 여백, 뒤로가기, 번들 빌드·동기화.
- 숲 로그인 필수, 같은 탭의 로그인 전달과 서버 검증, 로그인/가입 후 숲 복귀 및 서비스 홈 복귀. 토큰은 URL/localStorage에 넣지 않고 sessionStorage로 이동에 필요한 정보만 전달한다. 쿠키를 사용할 수 없는 환경에서 접근 토큰까지 만료되면 재로그인이 필요하다.
- 숲 전체 화면·인게임 메뉴·조이스틱·달리기 토글·Canvas 렌더링 보정, 아바타 프리셋 복원, 최초 진입 및 UI 숨기기 수정.
- 모바일 헤더·건강정보 탭·줄바꿈·박스·결과 게이지·인트로 스크롤·알림 버튼·챌린지 기록 완료 안내 개선.
- 오늘이/내일이 수치 상세보기와 SHAP 그래프 토글, 입력값·비교 기준 표시, Train 전용 참조 배경, 승인·가산성 검증 유지.
- OCR을 건강정보 입력 단계로 이동. 동의 → 추출 미리보기 → 사용자 확인 → 입력란 반영 → 건강정보 제출 순서로 저장한다.
- 승인 모델·음식 CV 모델의 Drive 다운로드·체크섬 검증, 독립 SQLite 서버 및 로컬 실행 도구.

Health Connect/HealthKit 실제 연결, OS 알림·백그라운드 동기화, 스토어 배포는 완료 범위에 포함되지 않는다. 웨어러블 샘플 버튼은 실제 기기 동기화가 아니다.

## 검증 범위

Android debug 빌드 및 BlueStacks·SM-S931N 설치를 확인했다. 최신 인증 수정본은 휴대폰에서 로드되는 것을 확인했으며, 쿠키 없는 로그인·숲 진입·홈 복귀는 합성 계정 API를 사용하는 브라우저 회귀 검사로 검증했다. **iOS는 프로젝트·동기화 설정을 준비했으며 Mac 컴파일·서명·실기기 검증은 미완료다.**

모델·원자료·사용자 DB·비밀키는 앱이나 Git에 포함하지 않는다. 디버그 APK는 약 401 MiB로 크므로 공유·설치 시 여유 공간이 필요하다. 모델 점수와 SHAP는 위험 선별·건강교육이며 진단·처방 또는 확정 발병 확률이 아니다.

전체 최종 차이와 검증 제한: [develop 대비 변경사항](CHANGELOG_DEVELOP.md).
