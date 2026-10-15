import logging
import subprocess
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class MediaExtractor:
    """Extract video clips, audio and frames with FFmpeg."""

    def __init__(self, base_dir: Path, config: Dict):
        self.base_dir = Path(base_dir)
        self.config = config
        self.videos_dir = self.base_dir / config.get("videos_dir", "videos")
        self.frames_dir = self.base_dir / config.get("frames_dir", "frames")
        self.audio_dir = self.base_dir / config.get("audio_dir", "audio")
        self.data_dir = self.base_dir / config.get("data_dir", "data")

        # Create directories
        self._create_directories()

    def _create_directories(self):
        """Create the required directories"""
        for directory in [self.videos_dir, self.frames_dir, self.audio_dir]:
            directory.mkdir(parents=True, exist_ok=True)
            logger.info(f"✓ Directory ready: {directory}")

    def extract_video_segments(
        self, video_id: str, video_path: Path, pairs: List[Dict]
    ) -> int:
        """Extract context and target video segments + audio for each pair from the video"""
        if not pairs:
            logger.info("  ✓ No pairs to extract")
            return 0

        try:
            logger.info(
                f"  ⏳ Extracting {len(pairs) * 2} video segments + {len(pairs) * 2} audio segments..."
            )

            extracted_count = 0

            # Extract context segments (video + audio)
            for pair in pairs:
                pair_id = pair.get("pair_id", "unknown")
                context = pair.get("context", {})

                ctx_start = context.get("start_time", 0)
                ctx_end = context.get("end_time", 0)

                # Context video
                ctx_output = self.videos_dir / f"{pair_id}.mp4"
                if not ctx_output.exists():
                    if self._extract_segment(
                        video_path, ctx_start, ctx_end, ctx_output
                    ):
                        extracted_count += 1
                else:
                    extracted_count += 1

                # Context audio
                ctx_audio_output = self.audio_dir / f"{pair_id}_c.wav"
                if not ctx_audio_output.exists():
                    if self._extract_audio_segment(
                        video_path, ctx_start, ctx_end, ctx_audio_output
                    ):
                        extracted_count += 1
                else:
                    extracted_count += 1

            # Extract target segments (video + audio)
            for pair in pairs:
                pair_id = pair.get("pair_id", "unknown")
                target = pair.get("target", {})

                tgt_start = target.get("start_time", 0)
                tgt_end = target.get("end_time", 0)

                # Target video
                tgt_output = self.videos_dir / f"{pair_id}_target.mp4"
                if not tgt_output.exists():
                    if self._extract_segment(
                        video_path, tgt_start, tgt_end, tgt_output
                    ):
                        extracted_count += 1
                else:
                    extracted_count += 1

                # Target audio
                tgt_audio_output = self.audio_dir / f"{pair_id}_t.wav"
                if not tgt_audio_output.exists():
                    if self._extract_audio_segment(
                        video_path, tgt_start, tgt_end, tgt_audio_output
                    ):
                        extracted_count += 1
                else:
                    extracted_count += 1

            logger.info(
                f"  ✓ Extracted {extracted_count} items ({len(pairs)} context + {len(pairs)} target)"
            )
            return extracted_count

        except Exception as e:
            logger.warning(f"  ✗ Segment extraction error: {e}")
            return 0

    def _extract_segment(
        self, video_path: Path, start_time: float, end_time: float, output_path: Path
    ) -> bool:
        """Extract a video segment (helper function)"""
        try:
            duration = end_time - start_time
            cmd = [
                "ffmpeg",
                "-i",
                str(video_path),
                "-ss",
                str(start_time),
                "-t",
                str(duration),
                "-c:v",
                "libx264",
                "-crf",
                "23",
                "-c:a",
                "aac",
                "-q:a",
                "5",
                "-y",
                str(output_path),
                "-hide_banner",
                "-loglevel",
                "error",
            ]

            result = subprocess.run(cmd, capture_output=True, timeout=600)

            if result.returncode == 0 and output_path.exists():
                return True
            else:
                logger.warning(f"    Failed to extract: {output_path.name}")
                return False

        except subprocess.TimeoutExpired:
            logger.warning(f"    Timeout: {output_path.name}")
            return False
        except Exception as e:
            logger.warning(f"    Error: {e}")
            return False

    def _extract_frame(
        self, video_path: Path, timestamp: float, output_path: Path
    ) -> bool:
        """Extract a frame at a given timestamp from a video (helper function)"""
        try:
            cmd = [
                "ffmpeg",
                "-i",
                str(video_path),
                "-ss",
                str(timestamp),
                "-vframes",
                "1",
                "-q:v",
                "2",
                "-y",
                str(output_path),
                "-hide_banner",
                "-loglevel",
                "error",
            ]

            result = subprocess.run(cmd, capture_output=True, timeout=60)

            if result.returncode == 0 and output_path.exists():
                return True
            else:
                logger.warning(f"    Failed to extract: {output_path.name}")
                return False

        except subprocess.TimeoutExpired:
            logger.warning(f"    Timeout: {output_path.name}")
            return False
        except Exception as e:
            logger.warning(f"    Error: {e}")
            return False

    def _extract_audio_segment(
        self, video_path: Path, start_time: float, end_time: float, output_path: Path
    ) -> bool:
        """Extract audio for a given range from a video (helper function)"""
        try:
            duration = end_time - start_time
            cmd = [
                "ffmpeg",
                "-i",
                str(video_path),
                "-ss",
                str(start_time),
                "-t",
                str(duration),
                "-q:a",
                "9",
                "-af",
                "aresample=16000",
                "-y",
                str(output_path),
                "-hide_banner",
                "-loglevel",
                "error",
            ]

            result = subprocess.run(cmd, capture_output=True, timeout=300)

            if result.returncode == 0 and output_path.exists():
                return True
            else:
                logger.warning(f"    Failed to extract: {output_path.name}")
                return False

        except subprocess.TimeoutExpired:
            logger.warning(f"    Timeout: {output_path.name}")
            return False
        except Exception as e:
            logger.warning(f"    Error: {e}")
            return False

    def extract_audio(self, video_id: str, video_path: Path) -> bool:
        """Extract audio from a video"""
        output_path = self.audio_dir / f"{video_id}.wav"

        if output_path.exists():
            logger.info("  ✓ Audio already extracted")
            return True

        try:
            logger.info("  ⏳ Extracting audio...")

            cmd = [
                "ffmpeg",
                "-i",
                str(video_path),
                "-q:a",
                "9",
                "-af",
                "aresample=16000",
                str(output_path),
                "-hide_banner",
                "-loglevel",
                "error",
            ]

            result = subprocess.run(cmd, capture_output=True, timeout=1800)

            if result.returncode == 0 and output_path.exists():
                file_size_mb = output_path.stat().st_size / (1024 * 1024)
                logger.info(f"  ✓ Audio extracted ({file_size_mb:.1f} MB)")
                return True
            else:
                logger.warning("  ✗ Audio extraction failed")
                return False

        except subprocess.TimeoutExpired:
            logger.warning("  ✗ Audio extraction timeout")
            return False
        except Exception as e:
            logger.warning(f"  ✗ Audio extraction error: {e}")
            return False

    def extract_frames(
        self, video_id: str, video_path: Path, target_times: List[float]
    ) -> int:
        """Extract frames at target timestamps"""
        extracted_count = 0
        for idx, target_time in enumerate(target_times, 1):
            try:
                output_path = self.frames_dir / f"{video_id}_{idx:04d}.jpg"
                if output_path.exists():
                    extracted_count += 1
                    continue

                cmd = [
                    "ffmpeg",
                    "-i",
                    str(video_path),
                    "-ss",
                    str(target_time),
                    "-vframes",
                    "1",
                    "-q:v",
                    "2",
                    "-y",
                    str(output_path),
                    "-hide_banner",
                    "-loglevel",
                    "error",
                ]

                result = subprocess.run(cmd, capture_output=True, timeout=60)
                if result.returncode == 0 and output_path.exists():
                    extracted_count += 1
            except Exception as e:
                logger.warning(f"    Failed to extract frame: {e}")

        return extracted_count

    def extract_frame_for_pair(
        self,
        pair_id: str,
        video_path: Path,
        timestamp: float,
        segment_type: str,
        force: bool = False,
    ) -> Optional[str]:
        """Extract a per-pair frame (based on a timestamp)"""
        try:
            # segment_type: "context" or "target"
            output_path = (
                self.frames_dir / f"{pair_id}_{segment_type[0]}.jpg"
            )  # _c or _t

            # If force=False, reuse the existing file
            if not force and output_path.exists() and output_path.stat().st_size > 0:
                return str(output_path.relative_to(self.base_dir))

            # If force=True or no file exists, extract a new one
            if output_path.exists():
                output_path.unlink()

            if self._extract_frame(video_path, timestamp, output_path):
                if output_path.exists() and output_path.stat().st_size > 0:
                    return str(output_path.relative_to(self.base_dir))

            return None
        except Exception as e:
            logger.warning(f"    Failed to extract frame for {pair_id}: {e}")
            return None

    def extract_audio_for_pair(
        self,
        pair_id: str,
        video_path: Path,
        start_time: float,
        end_time: float,
        segment_type: str,
        force: bool = False,
    ) -> Optional[str]:
        """Extract per-pair audio (context or target)"""
        try:
            # segment_type: "context" or "target"
            output_path = (
                self.audio_dir / f"{pair_id}_{segment_type[0]}.wav"
            )  # _c or _t

            # If force=False, reuse the existing file
            if not force and output_path.exists() and output_path.stat().st_size > 0:
                return str(output_path.relative_to(self.base_dir))

            # If force=True or no file exists, extract a new one
            if output_path.exists():
                output_path.unlink()

            if self._extract_audio_segment(
                video_path, start_time, end_time, output_path
            ):
                if output_path.exists() and output_path.stat().st_size > 0:
                    return str(output_path.relative_to(self.base_dir))

            return None
        except Exception as e:
            logger.warning(f"    Failed to extract audio for {pair_id}: {e}")
            return None

    def extract_video_segment_for_pair(
        self,
        pair_id: str,
        video_path: Path,
        start_time: float,
        end_time: float,
        segment_type: str,
        force: bool = False,
    ) -> Optional[str]:
        """Extract a per-pair video segment (context or target)"""
        try:
            # segment_type: "context" or "target"
            output_path = (
                self.videos_dir / f"{pair_id}_{segment_type[0]}.mp4"
            )  # _c or _t

            # If force=False, reuse the existing file
            if not force and output_path.exists() and output_path.stat().st_size > 0:
                return str(output_path.relative_to(self.base_dir))

            # If force=True or no file exists, extract a new one
            if output_path.exists():
                output_path.unlink()

            if self._extract_segment(video_path, start_time, end_time, output_path):
                if output_path.exists() and output_path.stat().st_size > 0:
                    return str(output_path.relative_to(self.base_dir))

            return None
        except Exception as e:
            logger.warning(f"    Failed to extract video segment for {pair_id}: {e}")
            return None
