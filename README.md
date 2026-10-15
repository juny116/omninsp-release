# OmniNSP

OmniNSP annotation을 바탕으로 YouTube 원본 영상에서 context와 target 구간을 재구성하는 도구입니다. 각 구간의 비디오·오디오·프레임을 추출하고 생성된 파일 경로를 annotation에 연결합니다.

## 처리 흐름

1. JSON annotation의 `video_id`를 기준으로 쌍을 묶습니다.
2. `yt-dlp`로 원본 영상을 한 번 내려받습니다.
3. FFmpeg로 각 쌍의 context/target 구간을 추출합니다.
4. 성공한 쌍의 `context`와 `target`에 `video_path`, `audio_path`, `image_path`를 추가해 새 annotation 파일에 저장합니다.

context 프레임은 구간 끝 시점, target 프레임은 구간 중간 시점에서 가져옵니다. `time_gap`은 target 중간 시점과 context 끝 시점의 차이(초)입니다. 비디오는 H.264/AAC, 오디오는 16 kHz WAV, 프레임은 JPEG로 추출합니다.

## 코드 구조

| 경로 | 역할 |
|---|---|
| `omninsp/annotations.py` | annotation 읽기, 영상별 그룹화, 경로 추가와 저장 |
| `omninsp/youtube.py` | yt-dlp 원본 영상 다운로드 |
| `omninsp/media.py` | FFmpeg 구간·프레임·오디오 추출과 기존 파일 재사용 |
| `omninsp/pipeline.py` | 영상 및 context/target 쌍 처리 순서와 성공 여부 관리 |
| `omninsp/dependencies.py` | FFmpeg·yt-dlp 실행 가능 여부 확인 |
| `omninsp/reports.py` | 영상·쌍·미디어 파일 수 집계와 보고서 저장 |
| `omninsp/cli.py` | 실행 옵션, 입력 처리와 진행 로그 |
| `tests/` | 추출 호출, annotation 연결과 통계 테스트 |

## 실행

Python 3.10 이상과 PATH에 등록된 `yt-dlp`, `ffmpeg`가 필요합니다. Python 코드 자체는 표준 라이브러리만 사용합니다. 저장소 루트에서 실행합니다.

```bash
python -m omninsp \
  --annotation /path/to/annotations.json \
  --base-dir /path/to/media \
  --output-annotation /path/to/local-annotations.json \
  --extract-items all
```

입력은 객체의 JSON 배열입니다. 각 객체에는 `video_id`, `pair_id`, 그리고 `start_time`·`end_time`(초)을 가진 `context`와 `target`이 들어갑니다. `scene_label`은 선택 항목입니다. `pair_id`는 파일명과 경로 연결 키로 사용하므로 입력 내에서 고유해야 합니다.

| 옵션 | 설명 |
|---|---|
| `--annotation` | 입력 annotation JSON |
| `--base-dir` | `videos/`, `audio/`, `frames/`를 생성할 위치 |
| `--output-annotation` | 경로가 추가된 annotation 저장 위치(필수) |
| `--extract-items` | `all` 또는 추출 유형을 쉼표로 구분 |
| `--limit` | 처리할 최대 영상 수 |
| `--force-extract` | 기존 구간 파일을 다시 추출 |

추출 유형은 `context_video`, `context_audio`, `context_frame`, `target_video`, `target_audio`, `target_frame`입니다. 경로는 `--base-dir` 기준 상대 경로이며, 추출 파일명에는 쌍 ID와 `_c` 또는 `_t`가 붙습니다. 선택하지 않은 미디어 경로는 `null`입니다. 요청한 추출 중 하나라도 실패하면 해당 쌍에는 새 경로를 붙이지 않습니다.

기존 원본 영상은 재사용합니다. 작업 디렉터리에 `cookies.txt`가 있으면 yt-dlp 다운로드에 사용합니다. 라이브러리에서는 `ReconstructionPipeline`으로 쌍을 처리하고 `generate_download_report()`로 결과를 집계할 수 있습니다.

## 테스트

```bash
python -m unittest discover -s tests -v
```

FFmpeg와 다운로드 호출을 대체한 테스트로, 실제 영상 다운로드 없이 추출 시점과 annotation 연결을 확인합니다.
