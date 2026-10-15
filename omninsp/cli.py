import logging
from collections import defaultdict
from pathlib import Path

logger = logging.getLogger(__name__)

import argparse

from .annotations import (
    enrich_annotation_with_paths,
    extract_unique_videos,
    load_annotation_file,
    save_enriched_annotation,
)
from .dependencies import check_dependencies
from .pipeline import ReconstructionPipeline


def main():
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    parser = argparse.ArgumentParser(
        description="JSON-annotation-based video downloader"
    )
    parser.add_argument(
        "--annotation",
        type=str,
        default="data/annotations_final.json",
        help="Path to the annotation JSON file",
    )
    parser.add_argument(
        "--base-dir", type=str, default="results", help="Base directory"
    )
    parser.add_argument(
        "--output-annotation",
        type=str,
        default=None,
        help="Output path for the enriched annotation",
    )
    parser.add_argument(
        "--limit", type=int, default=None, help="Maximum number of videos to process"
    )
    parser.add_argument(
        "--extract-items",
        type=str,
        default="all",
        help="Items to extract (comma-separated): context_video,context_audio,context_frame,target_video,target_audio,target_frame (default: all)",
    )
    parser.add_argument(
        "--force-extract",
        action="store_true",
        help="Re-extract and overwrite even if the file already exists",
    )

    args = parser.parse_args()

    # Set the default output annotation path
    if args.output_annotation is None:
        parser.error("--output-annotation is required")

    # Parse extract items
    if args.extract_items.lower() == "all":
        extract_items = [
            "context_video",
            "context_audio",
            "context_frame",
            "target_video",
            "target_audio",
            "target_frame",
        ]
    else:
        extract_items = [item.strip() for item in args.extract_items.split(",")]

    allowed = {
        f"{side}_{kind}"
        for side in ("context", "target")
        for kind in ("video", "audio", "frame")
    }
    if not extract_items or set(extract_items) - allowed:
        parser.error(
            "Unknown extraction type; use context/target_video, _audio or _frame"
        )
    if args.limit is not None and args.limit < 1:
        parser.error("--limit must be positive")

    force_extract = args.force_extract

    logger.info(f"📋 Extract items: {', '.join(extract_items)}")
    if force_extract:
        logger.info("🔄 Force extract: ON (existing files will be overwritten)")
    else:
        logger.info("🔄 Force extract: OFF (existing files will be reused)")

    # Configuration
    config = {
        "videos_dir": "videos",
        "audio_dir": "audio",
        "frames_dir": "frames",
        "data_dir": "data",
    }

    # Create the downloader
    downloader = ReconstructionPipeline(Path(args.base_dir), config)

    # Check dependencies
    check_dependencies()

    # Load annotation
    data = load_annotation_file(Path(args.annotation))

    # Extract unique videos
    videos = extract_unique_videos(data)

    # Print statistics
    logger.info("\n" + "=" * 80)
    logger.info("📊 Processing Statistics")
    logger.info("=" * 80)
    logger.info(f"Total unique videos: {len(videos)}")
    logger.info(f"Total pairs: {len(data)}")

    # Per-scene statistics
    scene_counts = defaultdict(int)
    for video_info in videos.values():
        for pair in video_info["pairs"]:
            scene_counts[pair.get("scene_label", "unknown")] += 1

    logger.info("\n▶ Pairs by Scene:")
    for scene, count in sorted(scene_counts.items()):
        logger.info(f"  - {scene}: {count} pairs")

    # Process videos
    logger.info("\n" + "=" * 80)
    logger.info("⏳ Processing Videos and Pairs")
    logger.info("=" * 80)

    video_list = list(videos.keys())
    if args.limit:
        video_list = video_list[: args.limit]
        logger.info(f"Limiting to {args.limit} videos")

    processing_results = []
    for idx, video_id in enumerate(video_list, 1):
        logger.info(f"[{idx}/{len(video_list)}]")
        video_info = videos[video_id]
        pairs_data = video_info.get("pairs", [])
        result = downloader.process_video(
            video_id, video_info, pairs_data, extract_items, force=force_extract
        )
        processing_results.append(result)

    # Annotation enriching
    logger.info("\n" + "=" * 80)
    logger.info("🔄 Enriching Annotation with Paths")
    logger.info("=" * 80)

    enriched_data = enrich_annotation_with_paths(data, processing_results)

    # Save enriched annotation
    save_enriched_annotation(enriched_data, Path(args.output_annotation))

    # Print final report
    logger.info("\n" + "=" * 80)
    logger.info("📋 Final Report")
    logger.info("=" * 80)

    total_processed = sum(1 for r in processing_results if r["downloaded"])
    total_failed = sum(1 for r in processing_results if not r["downloaded"])
    total_pairs_processed = sum(len(r.get("pairs", [])) for r in processing_results)
    successful_pairs = sum(
        sum(1 for p in r.get("pairs", []) if p["success"]) for r in processing_results
    )

    logger.info(f"Videos Downloaded: {total_processed}/{len(processing_results)}")
    logger.info(f"Videos Failed: {total_failed}")
    logger.info(f"Pairs Processed: {successful_pairs}/{total_pairs_processed}")
    logger.info(f"Output Annotation: {args.output_annotation}")

    logger.info("\n" + "=" * 80)
