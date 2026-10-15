import copy
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from omninsp.annotations import enrich_annotation_with_paths, extract_unique_videos
from omninsp.dependencies import check_dependencies
from omninsp.media import MediaExtractor
from omninsp.pipeline import ReconstructionPipeline
from omninsp.reports import generate_download_report


class ReconstructionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.pipeline = ReconstructionPipeline(self.root)
        self.pair = {
            "video_id": "sample",
            "pair_id": "pair",
            "context": {"start_time": 1, "end_time": 3},
            "target": {"start_time": 5, "end_time": 9},
        }

    def test_selected_frames_use_context_end_and_target_midpoint(self):
        self.pipeline.media = Mock()
        self.pipeline.media.extract_frame_for_pair.side_effect = [
            "frames/pair_c.jpg",
            "frames/pair_t.jpg",
        ]
        result = self.pipeline.process_pair(
            self.pair, self.root / "video.mp4", ["context_frame", "target_frame"]
        )
        self.assertTrue(result["success"])
        self.assertEqual(result["time_gap"], 4)
        self.assertEqual(
            [
                call.args[2]
                for call in self.pipeline.media.extract_frame_for_pair.call_args_list
            ],
            [3, 7],
        )
        self.pipeline.media.extract_audio_for_pair.assert_not_called()
        self.pipeline.media.extract_video_segment_for_pair.assert_not_called()
        original = copy.deepcopy(self.pair)
        enriched = enrich_annotation_with_paths(
            [self.pair], [{"pairs": [result], "video_id": "sample"}]
        )
        self.assertEqual(self.pair, original)
        self.assertEqual(enriched[0]["context"]["image_path"], "frames/pair_c.jpg")

    def test_failed_extraction_does_not_enrich(self):
        self.pipeline.media = Mock()
        self.pipeline.media.extract_frame_for_pair.return_value = None
        result = self.pipeline.process_pair(
            self.pair, self.root / "v.mp4", ["target_frame"]
        )
        self.assertFalse(result["success"])
        self.assertEqual(
            enrich_annotation_with_paths(
                [self.pair], [{"video_id": "sample", "pairs": [result]}]
            ),
            [self.pair],
        )

    def test_download_failure_skips_pairs(self):
        self.pipeline.downloader = Mock()
        self.pipeline.downloader.download_video.return_value = False
        self.pipeline.media = Mock()
        result = self.pipeline.process_video("sample", {}, [self.pair])
        self.assertFalse(result["downloaded"])
        self.assertEqual(result["pairs"], [])
        self.assertEqual(self.pipeline.media.mock_calls, [])

    def test_grouping_and_report(self):
        grouped = extract_unique_videos([self.pair, dict(self.pair, pair_id="second")])
        self.assertEqual(len(grouped["sample"]["pairs"]), 2)
        report = generate_download_report(
            [
                {
                    "downloaded": True,
                    "pairs": [
                        {
                            "success": True,
                            "context": {"audio_path": "a.wav", "image_path": "a.jpg"},
                            "target": {"video_path": "b.mp4"},
                        }
                    ],
                }
            ]
        )
        self.assertEqual(
            (
                report["successful_pairs"],
                report["audio_extracted"],
                report["total_frames_extracted"],
                report["total_segments_extracted"],
            ),
            (1, 1, 1, 1),
        )

    @patch("omninsp.dependencies.subprocess.run")
    def test_dependency_arguments_and_failure(self, run):
        check_dependencies()
        self.assertEqual(
            [call.args[0] for call in run.call_args_list],
            [["ffmpeg", "-version"], ["yt-dlp", "--version"]],
        )
        run.side_effect = subprocess.CalledProcessError(1, "ffmpeg")
        with self.assertRaises(RuntimeError):
            check_dependencies()

    @patch("omninsp.media.subprocess.run")
    def test_ffmpeg_frame_and_cache(self, run):
        extractor = MediaExtractor(self.root, {})
        output = self.root / "frames/pair_c.jpg"

        def extract(command, **kwargs):
            output.write_bytes(b"frame")
            return Mock(returncode=0)

        run.side_effect = extract
        self.assertEqual(
            extractor.extract_frame_for_pair("pair", self.root / "v.mp4", 3, "context"),
            "frames/pair_c.jpg",
        )
        command = run.call_args.args[0]
        self.assertEqual(command[command.index("-ss") + 1], "3")
        extractor.extract_frame_for_pair("pair", self.root / "v.mp4", 3, "context")
        self.assertEqual(run.call_count, 1)
        extractor.extract_frame_for_pair(
            "pair", self.root / "v.mp4", 3, "context", force=True
        )
        self.assertEqual(run.call_count, 2)


if __name__ == "__main__":
    unittest.main()
