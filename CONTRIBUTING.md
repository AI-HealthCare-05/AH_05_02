# 기여 가이드

## Git Flow

1. 작업 전 Issue를 생성하거나 배정받습니다.
2. `develop`에서 작업 브랜치를 생성합니다.
3. 코드, 테스트, 문서를 함께 수정합니다.
4. `develop`을 대상으로 Pull Request를 생성합니다.
5. 최소 1명의 승인과 CI 통과 후 병합합니다.
6. 배포 준비는 `release/*`, 긴급 운영 수정은 `hotfix/*`를 사용합니다.

## 브랜치 이름

```text
feature/{issue}-{area}-{description}
fix/{issue}-{area}-{description}
docs/{issue}-{description}
release/v{major}.{minor}.{patch}
hotfix/{issue}-{description}
```

영역은 `pm`, `ml`, `be`, `fe`, `db`, `infra`를 사용합니다.

## Pull Request 완료 조건

- 관련 Issue가 연결되어 있습니다.
- 구현 내용과 테스트 방법이 설명되어 있습니다.
- 테스트와 정적 검사가 통과합니다.
- API 또는 데이터 구조가 바뀌면 문서도 수정되어 있습니다.
- 비밀정보와 개인정보가 포함되지 않았습니다.

