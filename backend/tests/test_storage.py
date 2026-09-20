"""
tests/test_storage.py
---------------------
Unit tests for centralized video path resolution in app.core.storage.
"""

from pathlib import Path
import pytest

from app.core.storage import resolve_video_path, UPLOAD_DIR


class TestStoragePathResolver:
    """
    Test suite for resolve_video_path helper.
    """

    def test_url_path_mapping(self, tmp_path: Path):
        """
        Verify '/uploads/<filename>' maps to base_dir / <filename>.
        """
        video_url = "/uploads/a57e0ce6-4b6f-4ed9-ac70-a34531849244_Lower-extremity_video.mp4"
        resolved = resolve_video_path(video_url, base_dir=tmp_path)
        expected = tmp_path / "a57e0ce6-4b6f-4ed9-ac70-a34531849244_Lower-extremity_video.mp4"
        assert resolved == expected

    def test_url_path_without_leading_slash(self, tmp_path: Path):
        """
        Verify 'uploads/<filename>' maps to base_dir / <filename>.
        """
        video_url = "uploads/sample_jump.mp4"
        resolved = resolve_video_path(video_url, base_dir=tmp_path)
        assert resolved == tmp_path / "sample_jump.mp4"

    def test_plain_filename_mapping(self, tmp_path: Path):
        """
        Verify plain filename 'sample_jump.mp4' maps to base_dir / 'sample_jump.mp4'.
        """
        resolved = resolve_video_path("sample_jump.mp4", base_dir=tmp_path)
        assert resolved == tmp_path / "sample_jump.mp4"

    def test_default_base_dir_app_uploads(self):
        """
        Verify default base_dir uses UPLOAD_DIR (/app/uploads).
        """
        video_url = "/uploads/test_run.mp4"
        resolved = resolve_video_path(video_url)
        assert resolved == UPLOAD_DIR / "test_run.mp4"
        assert str(resolved).replace("\\", "/").endswith("app/uploads/test_run.mp4")

    def test_existing_absolute_path(self, tmp_path: Path):
        """
        Verify an existing absolute file path is returned directly.
        """
        existing_file = tmp_path / "existing_video.mp4"
        existing_file.write_bytes(b"dummy")

        resolved = resolve_video_path(existing_file)
        assert resolved == existing_file
        assert resolved.exists()

    def test_missing_video_raises_on_process(self, tmp_path: Path):
        """
        Verify resolving a missing video yields the correct path, and processing it raises FileNotFoundError.
        """
        missing_url = "/uploads/non_existent_video.mp4"
        resolved = resolve_video_path(missing_url, base_dir=tmp_path)
        assert resolved == tmp_path / "non_existent_video.mp4"
        assert not resolved.exists()

    def test_empty_or_none_url_raises_value_error(self):
        """
        Verify None or empty string raises ValueError.
        """
        with pytest.raises(ValueError, match="cannot be None or empty"):
            resolve_video_path("")

        with pytest.raises(ValueError, match="cannot be None or empty"):
            resolve_video_path(None)  # type: ignore
