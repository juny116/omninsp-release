import json
import logging
from pathlib import Path
from typing import Dict

logger = logging.getLogger(__name__)


def generate_download_report(results):
    """Summarize downloaded videos and the files returned for each pair."""
    pairs = [pair for result in results for pair in result.get("pairs", [])]
    segments = [pair.get(side, {}) for pair in pairs for side in ("context", "target")]
    return {
        "total_videos": len(results),
        "downloaded": sum(bool(result["downloaded"]) for result in results),
        "failed": sum(not result["downloaded"] for result in results),
        "total_pairs": len(pairs),
        "successful_pairs": sum(bool(pair["success"]) for pair in pairs),
        "audio_extracted": sum(bool(segment.get("audio_path")) for segment in segments),
        "total_frames_extracted": sum(
            bool(segment.get("image_path")) for segment in segments
        ),
        "total_segments_extracted": sum(
            bool(segment.get("video_path")) for segment in segments
        ),
        "results": results,
    }


def save_report(report: Dict, output_file: Path):
    """Save a processing summary as JSON."""
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with output_file.open("w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
