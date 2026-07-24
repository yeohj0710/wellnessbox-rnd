from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import run_local_research_session as launcher


class LocalResearchSessionTest(unittest.TestCase):
    def test_existing_runtime_secrets_gain_stable_web_session_keys(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            runtime = Path(directory)
            secret_path = runtime / "local_secrets.json"
            stop_path = runtime / "stop.request"
            secret_path.write_text(
                json.dumps({"token": "token", "pseudonym_salt": "salt"}),
                encoding="utf-8",
            )
            with (
                patch.object(launcher, "RUNTIME_ROOT", runtime),
                patch.object(launcher, "SECRET_PATH", secret_path),
                patch.object(launcher, "STOP_PATH", stop_path),
            ):
                first = launcher._load_or_create_secrets()
                second = launcher._load_or_create_secrets()

            self.assertEqual(first, second)
            self.assertGreaterEqual(len(first["cookie_password"]), 32)
            self.assertGreaterEqual(len(first["jwt_secret"]), 32)

    def test_web_environment_uses_persisted_session_keys(self) -> None:
        environment = launcher._web_environment(
            3001,
            "http://127.0.0.1:8000",
            {
                "token": "token",
                "pseudonym_salt": "salt",
                "cookie_password": "cookie-password-at-least-thirty-two-bytes",
                "jwt_secret": "jwt-secret-at-least-thirty-two-bytes",
            },
        )
        self.assertEqual(
            environment["COOKIE_PASSWORD"],
            "cookie-password-at-least-thirty-two-bytes",
        )
        self.assertEqual(
            environment["JWT_SECRET"],
            "jwt-secret-at-least-thirty-two-bytes",
        )


if __name__ == "__main__":
    unittest.main()
