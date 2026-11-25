"""Create .env from .env.example, replacing every `change-me-*` value with a random secret.

An existing .env is never overwritten.
"""

import re
import secrets
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
example, target = ROOT / ".env.example", ROOT / ".env"

if target.exists():
    print(".env already exists - leaving it unchanged")
else:
    content = re.sub(
        r"change-me-[\w-]+",
        lambda _: secrets.token_urlsafe(24),
        example.read_text(),
    )
    target.write_text(content)
    target.chmod(0o600)
    print("created .env with random passwords")
