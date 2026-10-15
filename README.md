# OmniNSP

OmniNSP annotation을 바탕으로 원본 영상에서 context와 target 구간을 재구성하는 도구입니다. YouTube 영상을 내려받고 각 구간의 비디오, 오디오와 프레임을 추출합니다.

## 주요 기능

- annotation의 video ID를 기준으로 원본 영상 수집
- context/target 쌍별 영상 구간, 음성 및 프레임 추출
- 필요한 미디어 유형만 선택하여 처리
- 생성된 로컬 파일 경로를 annotation에 추가
- 처리된 영상과 쌍의 성공·실패 집계

## 사용

Python, yt-dlp와 FFmpeg가 필요합니다. JSON annotation 파일을 입력으로 지정합니다.

```bash
python download/reconstruct.py \
  --annotation /path/to/annotations.json \
  --base-dir /path/to/local-media \
  --output-annotation /path/to/local-annotations.json \
  --extract-items all
```

| 옵션 | 설명 |
|---|---|
| `--annotation` | 입력 JSON annotation 경로 |
| `--base-dir` | 영상·음성·프레임을 저장할 디렉터리 |
| `--output-annotation` | 로컬 미디어 경로를 추가한 annotation 저장 경로 |
| `--extract-items` | 추출할 유형을 쉼표로 구분하거나 `all` 지정 |
| `--limit` | 처리할 최대 영상 수 |
| `--force-extract` | 기존 추출 파일을 다시 생성 |

추출 유형은 `context_video`, `context_audio`, `context_frame`, `target_video`, `target_audio`, `target_frame`입니다.

## 코드 구조

`download/reconstruct.py`의 `VideoDownloader`가 다운로드와 추출을 담당합니다. `extract_unique_videos()`가 annotation을 영상별로 묶고, `process_video()`와 `process_pair()`가 각 구간을 처리합니다. `enrich_annotation_with_paths()`는 생성된 파일 경로를 annotation에 연결합니다.
