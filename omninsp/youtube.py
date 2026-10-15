import logging
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)


class YouTubeDownloader:
    """Download original videos with yt-dlp."""

    def download_video(self, video_id: str, output_path: Path) -> bool:
        """Download a video from YouTube"""
        if output_path.exists():
            logger.info(f"  ✓ Already exists: {output_path.name}")
            return True

        try:
            logger.info(f"  ⏳ Downloading {video_id}...")

            # Cookies file path (current working directory)
            cookies_file = Path("cookies.txt")

            cmd = [
                "yt-dlp",
                f"https://www.youtube.com/watch?v={video_id}",
                "-f",
                "best[ext=mp4]",
                "-o",
                str(output_path),
                "--quiet",
            ]

            # Add cookies if the file exists
            if cookies_file.exists():
                cmd.extend(["--cookies", str(cookies_file)])
                logger.info(f"  (using cookies from: {cookies_file.resolve()})")

            result = subprocess.run(cmd, capture_output=True, timeout=3600)

            if result.returncode == 0 and output_path.exists():
                file_size_mb = output_path.stat().st_size / (1024 * 1024)
                logger.info(
                    f"  ✓ Downloaded: {output_path.name} ({file_size_mb:.1f} MB)"
                )
                return True
            else:
                logger.warning(f"  ✗ Download failed: {video_id}")
                if result.stderr:
                    logger.warning(f"    Error: {result.stderr.decode()[:100]}")
                return False

        except subprocess.TimeoutExpired:
            logger.warning(f"  ✗ Download timeout: {video_id}")
            return False
        except Exception as e:
            logger.warning(f"  ✗ Download error: {e}")
            return False
