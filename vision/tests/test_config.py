import pytest
from pydantic import ValidationError

from anpr.config import DEFAULT_CAMERAS_FILE, CameraRegistry, expand_env, load_cameras


def cam(**overrides):
    base = {
        "id": "cam1",
        "name": "Gate",
        "url": "rtsp://localhost:8554/cam1",
        "zone": [[0, 0.5], [1, 0.5], [1, 1]],
    }
    return base | overrides


def test_repo_camera_file_is_valid(monkeypatch):
    monkeypatch.delenv("RTSP_HOST", raising=False)
    registry = load_cameras(DEFAULT_CAMERAS_FILE)
    assert [c.id for c in registry.enabled] == ["cam1", "cam2", "cam3"]
    assert registry.cameras[0].url == "rtsp://localhost:8554/cam1"


def test_expand_env_default_and_value():
    assert expand_env("rtsp://${H:-localhost}/a", {}) == "rtsp://localhost/a"
    assert expand_env("rtsp://${H:-localhost}/a", {"H": "10.0.0.5"}) == "rtsp://10.0.0.5/a"
    assert expand_env("rtsp://u:${PW}@h", {"PW": "s3cret"}) == "rtsp://u:s3cret@h"


def test_expand_env_missing_variable_fails():
    with pytest.raises(ValueError, match="CAM_PW"):
        expand_env("rtsp://u:${CAM_PW}@h", {})


@pytest.mark.parametrize(
    "overrides",
    [
        {"zone": [[0, 0], [1, 1]]},  # too few points
        {"zone": [[0, 0], [1.5, 0], [1, 1]]},  # not normalised
        {"id": "Cam 1"},  # invalid id
        {"region_hint": "US"},
        {"url": "ftp://x"},
    ],
)
def test_invalid_camera_rejected(overrides):
    with pytest.raises(ValidationError):
        CameraRegistry.model_validate({"cameras": [cam(**overrides)]})


def test_duplicate_ids_rejected():
    with pytest.raises(ValidationError, match="duplicate"):
        CameraRegistry.model_validate({"cameras": [cam(), cam()]})


def test_zone_pixels():
    c = CameraRegistry.model_validate({"cameras": [cam()]}).cameras[0]
    assert c.zone_pixels(1280, 720) == [(0, 360), (1280, 360), (1280, 720)]


def test_disabled_cameras_excluded():
    reg = CameraRegistry.model_validate({"cameras": [cam(), cam(id="cam2", enabled=False)]})
    assert [c.id for c in reg.enabled] == ["cam1"]
