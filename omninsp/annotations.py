import json
import logging
import sys
from pathlib import Path
from typing import Dict, List

logger = logging.getLogger(__name__)

from copy import deepcopy


def load_annotation_file(annotation_file: Path) -> List[Dict]:
    """Load JSON annotation file"""
    logger.info(f"📂 Loading annotation file: {annotation_file}")
    try:
        with open(annotation_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        logger.info(f"✓ Loaded {len(data)} pairs")
        return data
    except FileNotFoundError:
        logger.error(f"❌ File not found: {annotation_file}")
        sys.exit(1)
    except json.JSONDecodeError:
        logger.error(f"❌ Invalid JSON format: {annotation_file}")
        sys.exit(1)


def extract_unique_videos(data: List[Dict]) -> Dict[str, Dict]:
    """Extract unique video_ids and their metadata from the annotation"""
    videos = {}

    for pair in data:
        video_id = pair.get("video_id")
        if video_id and video_id not in videos:
            videos[video_id] = {
                "video_id": video_id,
                "source": pair.get("scene_label", "unknown"),
                "pairs": [],  # All pairs belonging to this video
            }

        if video_id:
            videos[video_id]["pairs"].append(pair)

    logger.info(f"📹 Found {len(videos)} unique videos")
    return videos


def enrich_annotation_with_paths(
    original_data: List[Dict], processing_results: List[Dict]
) -> List[Dict]:
    """Enrich annotation data with processing results"""
    # video_id -> processing result mapping
    results_map = {}
    for video_result in processing_results:
        results_map[video_result["video_id"]] = video_result

    # pair_id -> pair result mapping
    pair_results_map = {}
    for video_result in processing_results:
        for pair_result in video_result.get("pairs", []):
            pair_results_map[pair_result["pair_id"]] = pair_result

    enriched_data = []

    for pair in original_data:
        pair_id = pair.get("pair_id")
        enriched_pair = deepcopy(pair)

        if pair_id in pair_results_map:
            pair_result = pair_results_map[pair_id]

            if pair_result["success"]:
                # Add paths to context
                if "context" not in enriched_pair:
                    enriched_pair["context"] = {}
                enriched_pair["context"]["video_path"] = pair_result["context"].get(
                    "video_path"
                )
                enriched_pair["context"]["audio_path"] = pair_result["context"].get(
                    "audio_path"
                )
                enriched_pair["context"]["image_path"] = pair_result["context"].get(
                    "image_path"
                )

                # Add paths to target
                if "target" not in enriched_pair:
                    enriched_pair["target"] = {}
                enriched_pair["target"]["video_path"] = pair_result["target"].get(
                    "video_path"
                )
                enriched_pair["target"]["audio_path"] = pair_result["target"].get(
                    "audio_path"
                )
                enriched_pair["target"]["image_path"] = pair_result["target"].get(
                    "image_path"
                )

                # Add time_gap
                enriched_pair["time_gap"] = pair_result["time_gap"]

        enriched_data.append(enriched_pair)

    return enriched_data


def save_enriched_annotation(enriched_data: List[Dict], output_file: Path):
    """Save the enriched annotation to a new file"""
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(enriched_data, f, ensure_ascii=False, indent=2)
    logger.info(f"✓ Enriched annotation saved: {output_file}")
