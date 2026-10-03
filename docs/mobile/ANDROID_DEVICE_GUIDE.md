# 개인 Android 휴대폰 구동

## 1. 준비 및 서버

[공통 준비](README.md#공통-준비)를 완료한다. 휴대폰은 Android 7/API 24 이상, 무선 디버깅은 Android 11 이상이다. 프로젝트는 JDK 21, Android SDK 36, Gradle wrapper 8.14.3을 사용한다. Android Studio SDK Manager에서 SDK Platform 36·Build Tools·Platform Tools를 설치하고 Gradle JDK를 21로 설정한다.

로컬에서 전체 기능을 시험하려면 먼저 [로컬 서버 준비](TEAM_HANDOFF.md#로컬-서버-새로-준비하기)를 완료하고 서버를 실행한다. 로컬 서버와 운영 서버의 계정은 별개이므로 로컬에는 테스트 계정을 새로 가입한다.

## 2. APK 빌드

Windows PowerShell에서 로컬 서버용으로 빌드한다.

```powershell
pnpm build:mobile:local
pnpm exec cap sync android
# 실제 설치 경로에 맞게 지정한다.
$env:JAVA_HOME = 'C:\Program Files\Java\jdk-21'
$env:ANDROID_HOME = "$env:LOCALAPPDATA\Android\Sdk"
& src/frontend/native/android/gradlew.bat -p src/frontend/native/android :app:assembleDebug --console=plain
```

Android Studio를 이용할 경우 `pnpm exec cap open android` 후 `app` 구성과 실제 휴대폰을 선택해 Run한다. 아래 ADB reverse도 설정해야 한다.

팀 HTTPS 서버를 사용할 때는 로컬 빌드 대신 다음을 실행한다. 주소에는 `/api` 등 경로를 넣지 않는다.

```powershell
$env:MOBILE_API_ORIGIN = 'https://팀에서-정한-API-호스트'
pnpm build:mobile
pnpm exec cap sync android
& src/frontend/native/android/gradlew.bat -p src/frontend/native/android :app:assembleDebug --console=plain
Remove-Item Env:MOBILE_API_ORIGIN
```

API 주소는 **빌드 시 번들에 고정**된다. 환경변수만 바꾸거나 웹 서버 파일만 갱신하면 이미 설치한 앱이 바뀌지 않는다. 다시 빌드·동기화·설치한다.

## 3. 휴대폰 연결

개발자 옵션에서 USB 디버깅을 켜고 USB 연결 및 PC 허용을 선택한다. 다음 명령의 `adb`는 Android SDK의 `platform-tools/adb`이며 PATH에 없으면 전체 경로를 사용한다.

```sh
adb devices -l
```

무선이면 PC·휴대폰을 같은 Wi-Fi에 연결한다. 휴대폰 개발자 옵션 → 무선 디버깅 → 페어링 코드로 기기 페어링을 연다.

```sh
adb pair 휴대폰IP:페어링포트
# 터미널에 현재 화면의 6자리 코드를 입력한다.
adb connect 휴대폰IP:연결포트
adb devices -l
```

**페어링 포트와 연결 포트는 다르다.** 연결 포트는 무선 디버깅 기본 화면에서 확인한다. 점이 아니라 `IP:포트` 형식을 사용한다. PC 재시작·Wi-Fi 변경 시 연결을 다시 설정할 수 있다. [Android 공식 ADB 절차](https://developer.android.com/tools/adb).

## 4. 설치 및 실행

`기기시리얼`은 위 목록에서 선택한다. BlueStacks·mDNS 별칭과 동시에 나타나면 실제 휴대폰의 정확한 시리얼을 지정한다.

```sh
adb -s 기기시리얼 reverse tcp:8000 tcp:8000
adb -s 기기시리얼 install --no-streaming -r src/frontend/native/android/app/build/outputs/apk/debug/app-debug.apk
adb -s 기기시리얼 shell am start -n life.dangno.app/.MainActivity
```

`reverse`는 로컬 빌드에서만 필요하다. 휴대폰의 `127.0.0.1:8000`을 PC 서버에 연결하며, API는 PC loopback에만 바인딩한다. USB 또는 무선 ADB 연결이 끊기면 로컬 서버 기능도 끊긴다. HTTPS 서버 빌드는 해당 서버에 인터넷/Wi-Fi로 직접 연결한다.

APK만 받았다면 빌드 단계는 생략할 수 있다. 포함된 API 주소·SHA-256을 전달자에게 확인한다. **현재 로컬 APK는 PC 서버와 reverse 없이 완전히 동작하지 않는다.**

## 5. 실기기 확인

1. 테스트 계정 가입·로그인 → 숲 바로가기 → 서비스 홈에서 동일 로그인 상태 확인. 비로그인은 숲 앞에서 로그인 화면으로 연결되는지 확인.
2. 건강정보 입력·이용확인 저장 → 분석 탭에서 오늘이/내일이 저장 결과, 수치·SHAP 토글 확인.
3. 사진 촬영·선택·취소·동의·명시적 제출, 실패 시 미완료 유지, 완료 안내 중앙 표시 확인.
4. 숲 최초 진입·전체 화면·조이스틱·달리기 두 번 토글·아바타·프리셋·UI 숨기기/복구 확인.
5. 뒤로가기는 직전 화면으로, 숲에서는 서비스 홈 이동 확인문을 표시하는지 확인. 큰 글자·키보드·인트로 스크롤도 확인.

`INSTALL_FAILED_UPDATE_INCOMPATIBLE`은 다른 PC의 debug 서명으로 설치한 경우 발생할 수 있다. 동일 제작자의 APK를 받거나, 데이터 삭제에 동의한 뒤 기존 앱을 제거하고 설치한다. 제거를 첫 번째 해결책으로 실행하지 않는다.

Google Play 계정 없이 debug APK를 개인 기기에 설치할 수 있다. 스토어 배포는 별도 서명·심사 절차다.
