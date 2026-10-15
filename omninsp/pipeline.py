import logging
from pathlib import Path
from typing import Dict, List

logger = logging.getLogger(__name__)

from .media import MediaExtractor
from .youtube import YouTubeDownloader


class ReconstructionPipeline:
    """Download each source once and reconstruct its annotated pairs."""

    def __init__(self, base_dir, config=None):
        self.media = MediaExtractor(base_dir, config or {})
        self.downloader = YouTubeDownloader()
        self.base_dir = self.media.base_dir
        self.videos_dir = self.media.videos_dir

    def process_pair(
        self,
        pair: Dict,
        video_path: Path,
        extract_items: List[str] = None,
        force: bool = False,
    ) -> Dict:
        """Process an individual pair and return its path information"""
        if extract_items is None or "all" in extract_items:
            extract_items = [
                "context_video",
                "context_audio",
                "context_frame",
                "target_video",
                "target_audio",
                "target_frame",
            ]

        pair_id = pair.get("pair_id", "unknown")
        result = {
            "pair_id": pair_id,
            "success": False,
            "context": {},
            "target": {},
            "time_gap": None,
        }

        try:
            # Process context
            context = pair.get("context", {})
            ctx_start = context.get("start_time", 0)
            ctx_end = context.get("end_time", 0)

            ctx_video_path = None
            ctx_audio_path = None
            ctx_frame_path = None

            if "context_video" in extract_items:
                ctx_video_path = self.media.extract_video_segment_for_pair(
                    pair_id, video_path, ctx_start, ctx_end, "context", force=force
                )

            if "context_audio" in extract_items:
                ctx_audio_path = self.media.extract_audio_for_pair(
                    pair_id, video_path, ctx_start, ctx_end, "context", force=force
                )

            if "context_frame" in extract_items:
                ctx_frame_path = self.media.extract_frame_for_pair(
                    pair_id, video_path, ctx_end, "context", force=force
                )  # Last frame

            result["context"] = {
                "video_path": ctx_video_path,
                "audio_path": ctx_audio_path,
                "image_path": ctx_frame_path,
            }

            # Validate context extraction (only check the requested items)
            ctx_required = {
                "context_video": ctx_video_path
                if "context_video" in extract_items
                else True,
                "context_audio": ctx_audio_path
                if "context_audio" in extract_items
                else True,
                "context_frame": ctx_frame_path
                if "context_frame" in extract_items
                else True,
            }
            ctx_success = all(ctx_required.values())
            if not ctx_success:
                logger.warning("  ⚠️ Context is missing some files")

            # Process target
            target = pair.get("target", {})
            tgt_start = target.get("start_time", 0)
            tgt_end = target.get("end_time", 0)
            tgt_midtime = (tgt_start + tgt_end) / 2

            tgt_video_path = None
            tgt_audio_path = None
            tgt_frame_path = None

            if "target_video" in extract_items:
                tgt_video_path = self.media.extract_video_segment_for_pair(
                    pair_id, video_path, tgt_start, tgt_end, "target", force=force
                )

            if "target_audio" in extract_items:
                tgt_audio_path = self.media.extract_audio_for_pair(
                    pair_id, video_path, tgt_start, tgt_end, "target", force=force
                )

            if "target_frame" in extract_items:
                tgt_frame_path = self.media.extract_frame_for_pair(
                    pair_id, video_path, tgt_midtime, "target", force=force
                )

            result["target"] = {
                "video_path": tgt_video_path,
                "audio_path": tgt_audio_path,
                "image_path": tgt_frame_path,
            }

            # Validate target extraction (only check the requested items)
            tgt_required = {
                "target_video": tgt_video_path
                if "target_video" in extract_items
                else True,
                "target_audio": tgt_audio_path
                if "target_audio" in extract_items
                else True,
                "target_frame": tgt_frame_path
                if "target_frame" in extract_items
                else True,
            }
            tgt_success = all(tgt_required.values())
            if not tgt_success:
                logger.warning("  ⚠️ Target is missing some files")

            # Compute time_gap (target midpoint frame - context end_time)
            result["time_gap"] = round(tgt_midtime - ctx_end, 2)

            # success=True only if all files succeed
            result["success"] = ctx_success and tgt_success

            if result["success"]:
                logger.info(f"  ✓ {pair_id}: all files extracted")

        except Exception as e:
            logger.warning(f"  ✗ Error processing pair {pair_id}: {e}")

        return result

    def process_video(
        self,
        video_id: str,
        video_info: Dict,
        pairs_data: List[Dict],
        extract_items: List[str] = None,
        force: bool = False,
    ) -> Dict:
        """Process a video and save the path information for each pair"""
        logger.info(f"\n▶ Processing video: {video_id}")

        result = {
            "video_id": video_id,
            "downloaded": False,
            "video_path": None,
            "pairs": [],
        }

        # Download the video
        video_path = self.videos_dir / f"{video_id}.mp4"
        if self.downloader.download_video(video_id, video_path):
            result["downloaded"] = True
            result["video_path"] = str(video_path.relative_to(self.base_dir))

            # Process each pair
            logger.info(f"  ⏳ Processing {len(pairs_data)} pairs...")
            for pair in pairs_data:
                pair_result = self.process_pair(
                    pair, video_path, extract_items, force=force
                )
                result["pairs"].append(pair_result)

        return result
