from __future__ import annotations

import sys
from pathlib import Path

import uvicorn

from wellnessbox_rnd.config import get_settings

REPO_ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    if str(REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(REPO_ROOT))

    settings = get_settings()
    uvicorn.run(
        "apps.inference_api.main:app",
        host=settings.host,
        port=settings.port,
        workers=settings.workers,
        log_level=settings.log_level.lower(),
        access_log=True,
        proxy_headers=True,
        server_header=False,
        timeout_keep_alive=30,
    )


if __name__ == "__main__":
    main()
