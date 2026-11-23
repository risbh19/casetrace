"""Start an isolated synthetic API for browser tests; never reuse a real database."""

import os
import secrets
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

root = Path(__file__).resolve().parents[1]
with TemporaryDirectory(prefix="casetrace-browser-") as directory:
    env = {**os.environ, "ENVIRONMENT": "training", "DATABASE_URL": f"sqlite:///{Path(directory).as_posix()}/test.db",
        "JWT_SECRET": secrets.token_urlsafe(48), "DEMO_PASSWORD": "Casetrace-browser-check-2026",
        "OLLAMA_MODEL": "", "EMBEDDING_MODEL": "", "ALLOWED_ORIGIN": "http://127.0.0.1:15173"}
    for command in ([sys.executable, "-m", "alembic", "upgrade", "head"], [sys.executable, "-m", "app.seed"]):
        subprocess.run(command, cwd=root / "backend", env=env, check=True)
    subprocess.run([sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000", "--no-access-log"],
        cwd=root / "backend", env=env, check=True)
