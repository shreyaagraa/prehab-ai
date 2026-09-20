"""
app/core/storage.py
-------------------
Centralized storage path resolution helper for uploaded video files.
"""

from pathlib import Path
import os

# Base directory for uploads inside the container/environment.
UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "/app/uploads"))


def resolve_video_path(
    video_url_or_path: str | Path | None,
    base_dir: Path | None = None,
) -> Path:
    """
    Resolve a stored ``video_url`` (e.g., "/uploads/abc.mp4"), relative path,
    or filename to an absolute filesystem ``Path`` within ``base_dir`` (default: ``UPLOAD_DIR``).

    Handles:
    - URL paths starting with "/uploads/" or "uploads/" -> maps to base_dir / filename
    - Plain filenames ("abc.mp4") -> maps to base_dir / "abc.mp4"
    - Existing absolute path -> returns as Path object directly if it exists on disk
    - Non-existent absolute path under "/uploads/..." -> maps to base_dir / filename

    Parameters
    ----------
    video_url_or_path : str | Path | None
        The video URL, path, or filename stored in the database.
    base_dir : Path | None, optional
        Target directory on the filesystem (defaults to UPLOAD_DIR: Path("/app/uploads")).

    Returns
    -------
    Path
        Resolved filesystem path.

    Raises
    ------
    ValueError
        If video_url_or_path is None or empty.
    """
    if not video_url_or_path:
        raise ValueError("video_url_or_path cannot be None or empty")

    target_dir = base_dir if base_dir is not None else UPLOAD_DIR

    # If it's already a Path object that is absolute and exists on disk, return it directly
    if isinstance(video_url_or_path, Path):
        if video_url_or_path.is_absolute() and video_url_or_path.exists():
            return video_url_or_path
        url_str = str(video_url_or_path)
    else:
        url_str = str(video_url_or_path)

    # 1. Check if the raw input string is an existing absolute path on disk
    p = Path(url_str)
    if p.is_absolute() and p.exists():
        return p

    # 2. Extract relative string representation & clean slashes
    clean_str = url_str.replace("\\", "/").strip().lstrip("/")

    # Strip leading "uploads/" if present
    if clean_str.startswith("uploads/"):
        clean_str = clean_str[len("uploads/"):]

    filename = Path(clean_str).name
    if not filename:
        raise ValueError(f"Invalid video filename in URL: {video_url_or_path}")

    return target_dir / filename
