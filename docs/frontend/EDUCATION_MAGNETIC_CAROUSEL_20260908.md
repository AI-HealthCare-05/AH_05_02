# 건강교육 Magnetic Carousel

4주 건강교육·퀴즈 목록을 세로 막대 카드 캐러셀로 변경했다. 기존 교육 내용·근거 링크·퀴즈·완료 저장 API는 그대로 사용한다.

## 디자인 참고와 구현 범위

- 참고: https://www.originkit.dev/components/magneticcarousel
- 원본 공개 미리보기의 커서 근접 확대, 거리별 확대 감소, 클릭 확대, 비선택 카드 흐림, 재클릭 접기를 참고했다.
- 요청 명령은 `yarn dlx originkit@latest add magneticcarousel`이다. 공식 CLI는 React/Next.js 컴포넌트 소스를 설치한다. 현재 프로젝트에는 React 빌드나 package.json이 없으므로 CLI를 실행하거나 설치했다고 표시하지 않았다. 공개 미리보기의 상호작용을 기존 HTML/CSS/JavaScript에 독립 구현했다. Originkit의 인증이 필요한 소스는 복사하지 않았다.
- 1~4주차에는 기존 혈당이 안내·걷기·식사·응원 이미지를 사용한다.

## 동작

- 마우스 근접 시 smoothstep 거리 계산으로 주변 카드도 점차 확대된다.
- 클릭·터치·Enter로 교육·퀴즈 모달이 바로 열린다. 기존 교육 본문·출처·퀴즈·완료 피드백을 같은 팝업에서 표시하며, 카드 아래에 학습 화면을 펼치지 않는다.
- 닫기, 팝업 바깥 클릭 또는 Escape로 닫으면 선택했던 카드로 초점을 돌린다. 모달이 열린 동안 배경 스크롤과 배경 요소 조작을 막고, 긴 내용은 팝업 안에서 스크롤한다.
- 이전/다음, 좌우 방향키, Home/End로 선택할 수 있다. 모바일은 가로 스크롤로 이동한다.
- 자동 재생은 없다. 동작 줄이기 설정에서는 근접 확대와 전환 애니메이션을 끈다.
- 완료 후 목록이 다시 그려져도 content_id로 선택한 주차를 유지한다. 로딩·실패·빈 목록에서는 이전 선택과 이동 버튼을 정리한다.

## 검증

- `node --test tests/frontend/*.test.cjs`: 거리별 확대, 주차 이동 경계, 완료 후 선택 유지, 빈 목록 정리 등.
- `python -m pytest tests/test_prototype.py tests/test_frontend_integration_runtime.py -q`: HTML 구조와 기존 프론트 계약.
- 로컬 재방문 프리뷰에서 카드 펼침, 주차 이동, 교육 열기, 퀴즈 풀이·완료 및 복귀를 확인한다. 프리뷰의 완료 처리는 실제 서버 저장 성공을 뜻하지 않는다.
