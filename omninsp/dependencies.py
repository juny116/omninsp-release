import logging
import subprocess

logger = logging.getLogger(__name__)


def check_dependencies():
    """Fail before processing if a required executable is unavailable."""
    for command in (["ffmpeg", "-version"], ["yt-dlp", "--version"]):
        try:
            subprocess.run(command, capture_output=True, timeout=5, check=True)
        except (OSError, subprocess.SubprocessError) as exc:
            raise RuntimeError(
                f"Cannot run {command[0]}; install it and check PATH"
            ) from exc
