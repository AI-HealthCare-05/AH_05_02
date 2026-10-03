"""Run the isolated SQLite backend with verified approved model artifacts."""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# The signed embeddable interpreter can reuse the project environment when
# Windows blocks its unsigned virtual-environment launcher.
if os.name == "nt" and Path(sys.prefix).resolve() != (ROOT / ".venv").resolve():
    import site
    site.addsitedir(str(ROOT / ".venv" / "Lib" / "site-packages"))

from dotenv import dotenv_values
sys.path.insert(0, str(ROOT))

if __name__ == "__main__":
    os.chdir(ROOT)
    settings = dotenv_values(ROOT / ".env.local-mobile")
    if not settings.get("SECRET_KEY"):
        raise SystemExit("Missing .env.local-mobile secret; run local setup first.")
    os.environ.update({key: value for key, value in settings.items() if value is not None})
    if os.environ.get("DEMO_ARTIFACT_INFERENCE_ENABLED") != "true":
        raise SystemExit("Local mobile testing requires actual approved artifacts.")
    (ROOT / "storage").mkdir(exist_ok=True)
    import uvicorn

    # Loopback only. BlueStacks uses adb reverse, without exposing the PC to the LAN.
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True,
                reload_dirs=[str(ROOT / name) for name in ("app", "src", "ai_worker", "scripts")])
