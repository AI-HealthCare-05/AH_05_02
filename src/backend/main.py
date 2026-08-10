from fastapi import FastAPI


app = FastAPI(
    title="만성질환 생활습관 챌린지 웹서비스",
    description="만성질환 위험 선별과 생활습관 챌린지를 제공하는 API",
    version="0.1.0",
)


@app.get("/health", tags=["system"])
def health_check() -> dict[str, str]:
    return {"status": "ok"}

