# 프론트엔드 프로토타입

별도의 Node.js 설치 없이 FastAPI가 정적 파일을 제공합니다.

- `index.html`: 8단계 사용자 흐름과 접근성 마크업
- `styles.css`: 반응형 레이아웃, 고대비 색상, 44px 이상 조작 영역
- `app.js`: `/api/v1` API 연동과 화면 상태 관리

저장소 루트에서 다음 명령으로 백엔드와 프론트엔드를 함께 실행합니다.

```bash
python -m pip install -r requirements.txt
python -m uvicorn src.backend.main:app --reload
```

브라우저에서 `http://127.0.0.1:8000`을 엽니다. 상세한 범위와 주의사항은 [`docs/PROTOTYPE.md`](../../docs/PROTOTYPE.md)를 참고합니다.
