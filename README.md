# OmniNSP — Reconstruction Code

OmniNSP의 원본 영상에서 context/target 구간, 음성, 프레임을 로컬에 재구성하는
코드입니다. 공개 대표 저장소는 이 프로젝트 하나로 정리합니다.

`NSP`, `OmniPred`, `omninsp-benchmark-private`의 초기 구현·검토 UI·비공개
평가 파이프라인을 이 저장소에 복사하지 않습니다. 이들은 비공개 보관본으로
남기며, 모델 예측 결과와 평가 자료도 분리합니다.

| 경로 | 역할 |
|---|---|
| `download/reconstruct.py` | annotation을 읽어 영상을 다운로드하고 구간·음성·프레임 추출 |

## 사용

Python, yt-dlp와 FFmpeg가 필요합니다. 아래 annotation 경로는 사용자가
별도로 제공하는 입력입니다. 이 코드 사본에는 annotation 자체도 포함하지 않습니다.

```bash
python download/reconstruct.py --help
python download/reconstruct.py \
  --annotation /path/to/annotations.json \
  --base-dir /path/to/local-media \
  --output-annotation /path/to/local-annotations.json \
  --extract-items all
```

개인 cookies, 로그인 자료, 원본 미디어, 모델 출력, 평가 결과와 분석 그림은
포함하지 않습니다. 다운로드 가능 여부는 각 원본의 접근 가능 상태에 따릅니다.
`--help`와 Python 문법 검사를 확인했으며 실제 다운로드는 실행하지 않았습니다.

서버의 `NSP/annotations_final.json`과 `omninsp-release/data/annotations_final.json`은
파일 해시가 달라 서로 덮어쓰지 않았습니다. 향후 annotation을 공개하려면 코드
공개와 별도로 버전과 배포 범위를 검토해야 합니다.
