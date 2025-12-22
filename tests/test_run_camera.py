import os
import sys
import tempfile
import pytest

from camera_follower_bot import run_camera as rc


def test_validate_model_path_fails_on_missing(tmp_path, monkeypatch):
    missing = tmp_path / 'no_model.tflite'
    # ensure file doesn't exist
    if missing.exists():
        missing.unlink()

    with pytest.raises(SystemExit) as excinfo:
        rc.validate_model_path(str(missing))
    assert excinfo.value.code == 2


def test_validate_model_path_passes_with_file(tmp_path):
    p = tmp_path / 'model.tflite'
    p.write_bytes(b'data')
    # should not raise
    rc.validate_model_path(str(p))
