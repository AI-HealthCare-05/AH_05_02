# 외부 연동 운영 설정 — Kakao Local · Claude OCR

## 1. Kakao Local: 주변 의료기관 검색

이미 구현된 경로는 `GET /api/v1/medical-facilities/nearby`이며, 서버가 Kakao Local REST API를 호출한다. 위치는 검색 요청에만 사용하며, 진단·진료 가능 여부를 판정하지 않는다.

운영 `.env` 설정:

```ini
MEDICAL_FACILITY_SEARCH_PROVIDER=kakao
KAKAO_REST_API_KEY=<Kakao REST API 키>
KAKAO_JAVASCRIPT_KEY=<Kakao 지도 JavaScript 키>
MEDICAL_FACILITY_SEARCH_KEYWORDS=당뇨
```

- REST 키는 서버에만 둔다. 브라우저·Git·응답 본문에 넣지 않는다.
- JavaScript 키는 Kakao Developers에서 `https://dang-no.life`와 `https://www.dang-no.life`를 웹 도메인으로 제한한다.
- 결과는 지도 사업자 데이터의 장소 안내이며 의료기관의 진료 가능 여부·의료 품질을 보장하지 않는다.

## 2. Claude Vision: 건강검진 결과통보서 OCR

`POST /api/v1/ocr-drafts/from-image`는 Claude Vision 또는 Clova OCR을 선택해 **텍스트 전사만** 수행한다. 이후 서비스는 허용된 신체계측·검사 필드만 초안으로 남기며, 사용자가 확인하기 전 건강정보를 수정하지 않는다.

운영 `.env` 설정:

```ini
HEALTH_CHECKUP_OCR_PROVIDER=claude
ANTHROPIC_API_KEY=<Anthropic API 키>
CLAUDE_OCR_MODEL=claude-haiku-4-5-20251001
CLAUDE_OCR_TIMEOUT_SECONDS=25
CLAUDE_OCR_MAX_BYTES=10485760
```

- 업로드 전 `외부 OCR 처리 동의`를 명시적으로 받아야 한다.
- 지원 형식은 JPG, PNG, WebP, PDF이며 최대 10MB이다.
- 원본 검진표는 처리 중 메모리에만 두며 서비스 DB·Git에 저장하지 않는다.
- Claude에게 이름·주민번호·주소 등 식별정보를 반환하지 말고, 읽기 어려운 값은 추정하지 말도록 지시한다.
- OCR 결과는 진단·처방이 아니며 수동 확인 후에만 적용한다.

## 3. 배포 전 확인

1. `KAKAO_REST_API_KEY`, `KAKAO_JAVASCRIPT_KEY`, `ANTHROPIC_API_KEY`를 서버 `.env`에만 입력한다.
2. FastAPI 컨테이너를 재생성한 뒤 provider 값만 로그/환경에서 확인한다. 키 전문은 출력하지 않는다.
3. 테스트 계정·합성 검진표로 Kakao 장소 1건 이상과 Claude OCR 초안 생성을 각각 확인한다.
4. 실제 검진표는 배포 점검에 사용하지 않는다.
