#!/usr/bin/env python3
"""
JSON-annotation-based video downloader and parser
- Download videos from YouTube
- Extract frames
- Extract audio
- Manage metadata
"""

import json
import os
import subprocess
import sys
from pathlib import Path
from collections import defaultdict
import argparse
from typing import List, Dict, Set, Optional
import logging

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class VideoDownloader:
    """Video download and processing class"""
    
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
    
    def _check_dependencies(self):
        """Check required tools"""
        tools = {
            'ffmpeg': 'Video processing',
            'yt-dlp': 'YouTube download',
        }
        
        logger.info("📋 Checking dependencies...")
        for tool, description in tools.items():
            try:
                subprocess.run(
                    [tool, '--version'] if tool == 'ffmpeg' else [tool, '--version'],
                    capture_output=True,
                    timeout=5
                )
                logger.info(f"  ✓ {tool}: {description}")
            except (subprocess.TimeoutExpired, FileNotFoundError):
                logger.warning(f"  ✗ {tool} not found: {description}")
                logger.warning(f"    Install with: apt-get install {tool}")
    
    def load_annotation_file(self, annotation_file: Path) -> List[Dict]:
        """Load JSON annotation file"""
        logger.info(f"📂 Loading annotation file: {annotation_file}")
        try:
            with open(annotation_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            logger.info(f"✓ Loaded {len(data)} pairs")
            return data
        except FileNotFoundError:
            logger.error(f"❌ File not found: {annotation_file}")
            sys.exit(1)
        except json.JSONDecodeError:
            logger.error(f"❌ Invalid JSON format: {annotation_file}")
            sys.exit(1)
    
    def extract_unique_videos(self, data: List[Dict]) -> Dict[str, Dict]:
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
                'yt-dlp',
                f'https://www.youtube.com/watch?v={video_id}',
                '-f', 'best[ext=mp4]',
                '-o', str(output_path),
                '--quiet',
            ]
            
            # Add cookies if the file exists
            if cookies_file.exists():
                cmd.extend(['--cookies', str(cookies_file)])
                logger.info(f"  (using cookies from: {cookies_file.resolve()})")
            
            result = subprocess.run(cmd, capture_output=True, timeout=3600)
            
            if result.returncode == 0 and output_path.exists():
                file_size_mb = output_path.stat().st_size / (1024 * 1024)
                logger.info(f"  ✓ Downloaded: {output_path.name} ({file_size_mb:.1f} MB)")
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
    
    def extract_video_segments(self, video_id: str, video_path: Path, pairs: List[Dict]) -> int:
        """Extract context and target video segments + audio for each pair from the video"""
        if not pairs:
            logger.info(f"  ✓ No pairs to extract")
            return 0
        
        try:
            logger.info(f"  ⏳ Extracting {len(pairs)*2} video segments + {len(pairs)*2} audio segments...")
            
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
                    if self._extract_segment(video_path, ctx_start, ctx_end, ctx_output):
                        extracted_count += 1
                else:
                    extracted_count += 1
                
                # Context audio
                ctx_audio_output = self.audio_dir / f"{pair_id}_c.wav"
                if not ctx_audio_output.exists():
                    if self._extract_audio_segment(video_path, ctx_start, ctx_end, ctx_audio_output):
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
                    if self._extract_segment(video_path, tgt_start, tgt_end, tgt_output):
                        extracted_count += 1
                else:
                    extracted_count += 1
                
                # Target audio
                tgt_audio_output = self.audio_dir / f"{pair_id}_t.wav"
                if not tgt_audio_output.exists():
                    if self._extract_audio_segment(video_path, tgt_start, tgt_end, tgt_audio_output):
                        extracted_count += 1
                else:
                    extracted_count += 1
            
            logger.info(f"  ✓ Extracted {extracted_count} items ({len(pairs)} context + {len(pairs)} target)")
            return extracted_count
        
        except Exception as e:
            logger.warning(f"  ✗ Segment extraction error: {e}")
            return 0
    
    def _extract_segment(self, video_path: Path, start_time: float, end_time: float, output_path: Path) -> bool:
        """Extract a video segment (helper function)"""
        try:
            duration = end_time - start_time
            cmd = [
                'ffmpeg',
                '-i', str(video_path),
                '-ss', str(start_time),
                '-t', str(duration),
                '-c:v', 'libx264',
                '-crf', '23',
                '-c:a', 'aac',
                '-q:a', '5',
                '-y',
                str(output_path),
                '-hide_banner',
                '-loglevel', 'error',
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
    
    def _extract_frame(self, video_path: Path, timestamp: float, output_path: Path) -> bool:
        """Extract a frame at a given timestamp from a video (helper function)"""
        try:
            cmd = [
                'ffmpeg',
                '-i', str(video_path),
                '-ss', str(timestamp),
                '-vframes', '1',
                '-q:v', '2',
                '-y',
                str(output_path),
                '-hide_banner',
                '-loglevel', 'error',
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
    
    def _extract_audio_segment(self, video_path: Path, start_time: float, end_time: float, output_path: Path) -> bool:
        """Extract audio for a given range from a video (helper function)"""
        try:
            duration = end_time - start_time
            cmd = [
                'ffmpeg',
                '-i', str(video_path),
                '-ss', str(start_time),
                '-t', str(duration),
                '-q:a', '9',
                '-af', 'aresample=16000',
                '-y',
                str(output_path),
                '-hide_banner',
                '-loglevel', 'error',
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
            logger.info(f"  ✓ Audio already extracted")
            return True
        
        try:
            logger.info(f"  ⏳ Extracting audio...")
            
            cmd = [
                'ffmpeg',
                '-i', str(video_path),
                '-q:a', '9',
                '-af', 'aresample=16000',
                str(output_path),
                '-hide_banner',
                '-loglevel', 'error',
            ]
            
            result = subprocess.run(cmd, capture_output=True, timeout=1800)
            
            if result.returncode == 0 and output_path.exists():
                file_size_mb = output_path.stat().st_size / (1024 * 1024)
                logger.info(f"  ✓ Audio extracted ({file_size_mb:.1f} MB)")
                return True
            else:
                logger.warning(f"  ✗ Audio extraction failed")
                return False
        
        except subprocess.TimeoutExpired:
            logger.warning(f"  ✗ Audio extraction timeout")
            return False
        except Exception as e:
            logger.warning(f"  ✗ Audio extraction error: {e}")
            return False
    
    def extract_frames(self, video_id: str, video_path: Path, target_times: List[float]) -> int:
        """Extract frames at target timestamps"""
        extracted_count = 0
        for idx, target_time in enumerate(target_times, 1):
            try:
                output_path = self.frames_dir / f"{video_id}_{idx:04d}.jpg"
                if output_path.exists():
                    extracted_count += 1
                    continue
                
                cmd = [
                    'ffmpeg',
                    '-i', str(video_path),
                    '-ss', str(target_time),
                    '-vframes', '1',
                    '-q:v', '2',
                    '-y',
                    str(output_path),
                    '-hide_banner',
                    '-loglevel', 'error',
                ]
                
                result = subprocess.run(cmd, capture_output=True, timeout=60)
                if result.returncode == 0 and output_path.exists():
                    extracted_count += 1
            except Exception as e:
                logger.warning(f"    Failed to extract frame: {e}")
        
        return extracted_count
    
    def extract_frame_for_pair(self, pair_id: str, video_path: Path, timestamp: float, segment_type: str, force: bool = False) -> Optional[str]:
        """Extract a per-pair frame (based on a timestamp)"""
        try:
            # segment_type: "context" or "target"
            output_path = self.frames_dir / f"{pair_id}_{segment_type[0]}.jpg"  # _c or _t

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
    
    def extract_audio_for_pair(self, pair_id: str, video_path: Path, start_time: float, end_time: float, segment_type: str, force: bool = False) -> Optional[str]:
        """Extract per-pair audio (context or target)"""
        try:
            # segment_type: "context" or "target"
            output_path = self.audio_dir / f"{pair_id}_{segment_type[0]}.wav"  # _c or _t

            # If force=False, reuse the existing file
            if not force and output_path.exists() and output_path.stat().st_size > 0:
                return str(output_path.relative_to(self.base_dir))

            # If force=True or no file exists, extract a new one
            if output_path.exists():
                output_path.unlink()
            
            if self._extract_audio_segment(video_path, start_time, end_time, output_path):
                if output_path.exists() and output_path.stat().st_size > 0:
                    return str(output_path.relative_to(self.base_dir))
            
            return None
        except Exception as e:
            logger.warning(f"    Failed to extract audio for {pair_id}: {e}")
            return None
    
    def extract_video_segment_for_pair(self, pair_id: str, video_path: Path, start_time: float, end_time: float, segment_type: str, force: bool = False) -> Optional[str]:
        """Extract a per-pair video segment (context or target)"""
        try:
            # segment_type: "context" or "target"
            output_path = self.videos_dir / f"{pair_id}_{segment_type[0]}.mp4"  # _c or _t

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
    
    def process_pair(self, pair: Dict, video_path: Path, extract_items: List[str] = None, force: bool = False) -> Dict:
        """Process an individual pair and return its path information"""
        if extract_items is None or "all" in extract_items:
            extract_items = ["context_video", "context_audio", "context_frame", "target_video", "target_audio", "target_frame"]
        
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
                ctx_video_path = self.extract_video_segment_for_pair(pair_id, video_path, ctx_start, ctx_end, "context", force=force)
            
            if "context_audio" in extract_items:
                ctx_audio_path = self.extract_audio_for_pair(pair_id, video_path, ctx_start, ctx_end, "context", force=force)
            
            if "context_frame" in extract_items:
                ctx_frame_path = self.extract_frame_for_pair(pair_id, video_path, ctx_end, "context", force=force)  # Last frame
            
            result["context"] = {
                "video_path": ctx_video_path,
                "audio_path": ctx_audio_path,
                "image_path": ctx_frame_path,
            }
            
            # Validate context extraction (only check the requested items)
            ctx_required = {
                "context_video": ctx_video_path if "context_video" in extract_items else True,
                "context_audio": ctx_audio_path if "context_audio" in extract_items else True,
                "context_frame": ctx_frame_path if "context_frame" in extract_items else True,
            }
            ctx_success = all(ctx_required.values())
            if not ctx_success:
                logger.warning(f"  ⚠️ Context is missing some files")
            
            # Process target
            target = pair.get("target", {})
            tgt_start = target.get("start_time", 0)
            tgt_end = target.get("end_time", 0)
            tgt_midtime = (tgt_start + tgt_end) / 2
            
            tgt_video_path = None
            tgt_audio_path = None
            tgt_frame_path = None
            
            if "target_video" in extract_items:
                tgt_video_path = self.extract_video_segment_for_pair(pair_id, video_path, tgt_start, tgt_end, "target", force=force)
            
            if "target_audio" in extract_items:
                tgt_audio_path = self.extract_audio_for_pair(pair_id, video_path, tgt_start, tgt_end, "target", force=force)
            
            if "target_frame" in extract_items:
                tgt_frame_path = self.extract_frame_for_pair(pair_id, video_path, tgt_midtime, "target", force=force)
            
            result["target"] = {
                "video_path": tgt_video_path,
                "audio_path": tgt_audio_path,
                "image_path": tgt_frame_path,
            }
            
            # Validate target extraction (only check the requested items)
            tgt_required = {
                "target_video": tgt_video_path if "target_video" in extract_items else True,
                "target_audio": tgt_audio_path if "target_audio" in extract_items else True,
                "target_frame": tgt_frame_path if "target_frame" in extract_items else True,
            }
            tgt_success = all(tgt_required.values())
            if not tgt_success:
                logger.warning(f"  ⚠️ Target is missing some files")
            
            # Compute time_gap (target midpoint frame - context end_time)
            result["time_gap"] = round(tgt_midtime - ctx_end, 2)
            
            # success=True only if all files succeed
            result["success"] = ctx_success and tgt_success
            
            if result["success"]:
                logger.info(f"  ✓ {pair_id}: all files extracted")
            
        except Exception as e:
            logger.warning(f"  ✗ Error processing pair {pair_id}: {e}")
        
        return result
    
    def process_video(self, video_id: str, video_info: Dict, pairs_data: List[Dict], extract_items: List[str] = None, force: bool = False) -> Dict:
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
        if self.download_video(video_id, video_path):
            result["downloaded"] = True
            result["video_path"] = str(video_path.relative_to(self.base_dir))
            
            # Process each pair
            logger.info(f"  ⏳ Processing {len(pairs_data)} pairs...")
            for pair in pairs_data:
                pair_result = self.process_pair(pair, video_path, extract_items, force=force)
                result["pairs"].append(pair_result)
        
        return result
    
    def enrich_annotation_with_paths(self, original_data: List[Dict], processing_results: List[Dict]) -> List[Dict]:
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
            enriched_pair = pair.copy()
            
            if pair_id in pair_results_map:
                pair_result = pair_results_map[pair_id]
                
                if pair_result["success"]:
                    # Add paths to context
                    if "context" not in enriched_pair:
                        enriched_pair["context"] = {}
                    enriched_pair["context"]["video_path"] = pair_result["context"].get("video_path")
                    enriched_pair["context"]["audio_path"] = pair_result["context"].get("audio_path")
                    enriched_pair["context"]["image_path"] = pair_result["context"].get("image_path")
                    
                    # Add paths to target
                    if "target" not in enriched_pair:
                        enriched_pair["target"] = {}
                    enriched_pair["target"]["video_path"] = pair_result["target"].get("video_path")
                    enriched_pair["target"]["audio_path"] = pair_result["target"].get("audio_path")
                    enriched_pair["target"]["image_path"] = pair_result["target"].get("image_path")
                    
                    # Add time_gap
                    enriched_pair["time_gap"] = pair_result["time_gap"]
            
            enriched_data.append(enriched_pair)
        
        return enriched_data
    
    def save_enriched_annotation(self, enriched_data: List[Dict], output_file: Path):
        """Save the enriched annotation to a new file"""
        output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(enriched_data, f, ensure_ascii=False, indent=2)
        logger.info(f"✓ Enriched annotation saved: {output_file}")
    
    def generate_download_report(self, results: List[Dict]) -> Dict:
        """Generate a download report"""
        report = {
            "total_videos": len(results),
            "downloaded": sum(1 for r in results if r["downloaded"]),
            "failed": sum(1 for r in results if not r["downloaded"]),
            "audio_extracted": sum(1 for r in results if r["audio_extracted"]),
            "total_frames_extracted": sum(r.get("frames_extracted", 0) for r in results),
            "total_segments_extracted": sum(r.get("segments_extracted", 0) for r in results),
            "results": results,
        }
        
        return report
    
    def save_report(self, report: Dict, output_file: Path):
        """Save the report"""
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        logger.info(f"✓ Report saved: {output_file}")


def main():
    parser = argparse.ArgumentParser(
        description="JSON-annotation-based video downloader"
    )
    parser.add_argument(
        "--annotation",
        type=str,
        default="data/annotations_final.json",
        help="Path to the annotation JSON file"
    )
    parser.add_argument(
        "--base-dir",
        type=str,
        default="results",
        help="Base directory"
    )
    parser.add_argument(
        "--output-annotation",
        type=str,
        default=None,
        help="Output path for the enriched annotation"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Maximum number of videos to process"
    )
    parser.add_argument(
        "--extract-items",
        type=str,
        default="all",
        help="Items to extract (comma-separated): context_video,context_audio,context_frame,target_video,target_audio,target_frame (default: all)"
    )
    parser.add_argument(
        "--force-extract",
        action="store_true",
        help="Re-extract and overwrite even if the file already exists"
    )
    
    args = parser.parse_args()
    
    # Set the default output annotation path
    if args.output_annotation is None:
        print("⚠️ No output annotation path provided checking if --output-annotation is provided")
        return
    
    # Parse extract items
    if args.extract_items.lower() == "all":
        extract_items = ["context_video", "context_audio", "context_frame", "target_video", "target_audio", "target_frame"]
    else:
        extract_items = [item.strip() for item in args.extract_items.split(",")]
    
    force_extract = args.force_extract
    
    logger.info(f"📋 Extract items: {', '.join(extract_items)}")
    if force_extract:
        logger.info(f"🔄 Force extract: ON (existing files will be overwritten)")
    else:
        logger.info(f"🔄 Force extract: OFF (existing files will be reused)")
    
    # Configuration
    config = {
        "videos_dir": "videos",
        "audio_dir": "audio",
        "frames_dir": "frames",
        "data_dir": "data",
    }
    
    # Create the downloader
    downloader = VideoDownloader(Path(args.base_dir), config)

    # Check dependencies
    downloader._check_dependencies()

    # Load annotation
    data = downloader.load_annotation_file(Path(args.annotation))

    # Extract unique videos
    videos = downloader.extract_unique_videos(data)

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
        video_list = video_list[:args.limit]
        logger.info(f"Limiting to {args.limit} videos")
    
    processing_results = []
    for idx, video_id in enumerate(video_list, 1):
        logger.info(f"[{idx}/{len(video_list)}]")
        video_info = videos[video_id]
        pairs_data = video_info.get("pairs", [])
        result = downloader.process_video(video_id, video_info, pairs_data, extract_items, force=force_extract)
        processing_results.append(result)
    
    # Annotation enriching
    logger.info("\n" + "=" * 80)
    logger.info("🔄 Enriching Annotation with Paths")
    logger.info("=" * 80)
    
    enriched_data = downloader.enrich_annotation_with_paths(data, processing_results)
    
    # Save enriched annotation
    downloader.save_enriched_annotation(enriched_data, Path(args.output_annotation))
    
    # Print final report
    logger.info("\n" + "=" * 80)
    logger.info("📋 Final Report")
    logger.info("=" * 80)
    
    total_processed = sum(1 for r in processing_results if r["downloaded"])
    total_failed = sum(1 for r in processing_results if not r["downloaded"])
    total_pairs_processed = sum(len(r.get("pairs", [])) for r in processing_results)
    successful_pairs = sum(sum(1 for p in r.get("pairs", []) if p["success"]) for r in processing_results)
    
    logger.info(f"Videos Downloaded: {total_processed}/{len(processing_results)}")
    logger.info(f"Videos Failed: {total_failed}")
    logger.info(f"Pairs Processed: {successful_pairs}/{total_pairs_processed}")
    logger.info(f"Output Annotation: {args.output_annotation}")
    
    logger.info("\n" + "=" * 80)


if __name__ == "__main__":
    main()
