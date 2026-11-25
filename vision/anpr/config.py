"""Camera registry: loading and validating config/cameras.yaml."""

import os
import re
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field, field_validator, model_validator

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CAMERAS_FILE = REPO_ROOT / "config" / "cameras.yaml"

_VAR = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)(?::-([^}]*))?\}")


def expand_env(value: str, env: dict[str, str] | None = None) -> str:
    """Expand ${VAR} and ${VAR:-default}. An unset variable without a default is an error,
    so a missing camera password fails loudly instead of producing a broken URL."""
    env = os.environ if env is None else env

    def repl(m: re.Match) -> str:
        name, default = m.group(1), m.group(2)
        if env.get(name):
            return env[name]
        if default is not None:
            return default
        raise ValueError(f"environment variable {name} is not set")

    return _VAR.sub(repl, value)


class Camera(BaseModel):
    id: str = Field(pattern=r"^[a-z0-9_-]{1,32}$")
    name: str
    url: str
    region_hint: Literal["IN", "UAE", "auto"] = "auto"
    zone: list[tuple[float, float]]
    enabled: bool = True

    @field_validator("url")
    @classmethod
    def _expand_url(cls, v: str) -> str:
        v = expand_env(v)
        if not v.startswith(("rtsp://", "rtsps://", "http://", "https://", "file://", "/")):
            raise ValueError("url must be an rtsp/http(s) URL or a file path")
        return v

    @field_validator("zone")
    @classmethod
    def _check_zone(cls, v: list[tuple[float, float]]) -> list[tuple[float, float]]:
        if len(v) < 3:
            raise ValueError("zone needs at least 3 points")
        if any(not (0.0 <= x <= 1.0 and 0.0 <= y <= 1.0) for x, y in v):
            raise ValueError("zone points must be normalised to 0..1")
        return v

    def zone_pixels(self, width: int, height: int) -> list[tuple[int, int]]:
        return [(round(x * width), round(y * height)) for x, y in self.zone]


class CameraRegistry(BaseModel):
    cameras: list[Camera]

    @model_validator(mode="after")
    def _unique_ids(self) -> "CameraRegistry":
        ids = [c.id for c in self.cameras]
        dupes = {i for i in ids if ids.count(i) > 1}
        if dupes:
            raise ValueError(f"duplicate camera ids: {sorted(dupes)}")
        return self

    @property
    def enabled(self) -> list[Camera]:
        return [c for c in self.cameras if c.enabled]


def load_cameras(path: str | Path | None = None) -> CameraRegistry:
    path = Path(path or os.getenv("ANPR_CAMERAS_FILE") or DEFAULT_CAMERAS_FILE)
    with path.open() as f:
        return CameraRegistry.model_validate(yaml.safe_load(f))
