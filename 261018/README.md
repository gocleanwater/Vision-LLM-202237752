# 2강(2026.10.18) 컴퓨터 비전 실습

- 이름: 고정수
- 학번: 202237752

## 실습 개요

저장소 루트의 [`02_Computer-Vision.ipynb`](../02_Computer-Vision.ipynb)를 바탕으로, 실시간 카메라 입력에서 색상 기반 탁구공 검출과 추적, MediaPipe 손 랜드마크 검출을 각각 실행 가능한 Python 파일로 정리했습니다. 노트북의 **「실시간 카메라 피드」**, **「실시간 객체 검출」**, **「실시간 객체 추적」**, **「MediaPipe 실시간 신체 인식」** 부분과 연결됩니다. 앞부분의 색공간 변환, 색상 분할, 모폴로지 연산, 외곽선 검출도 탁구공 코드에 적용했습니다.

| 파일                         | 주요 기능                                                                       | 노트북과의 관계                                               |
| ---------------------------- | ------------------------------------------------------------------------------- | ------------------------------------------------------------- |
| `pingpong_circle_overlay.py` | 초록색 탁구공을 분할하고 가장 큰 외곽선의 영역·외곽선·최소 외접원을 영상에 표시 | 색상 분할, 모폴로지, 외곽선 검출 및 「실시간 객체 검출」 부분 |
| `pingpong_kalman_filter.py`  | 탁구공 검출 결과에 직접 정의한 Kalman Filter의 예측·보정을 추가                 | 「실시간 객체 검출」과 「실시간 객체 추적」 부분              |
| `mp_hand.py`                 | 최대 두 손의 랜드마크와 연결선, 손 개수 및 좌우 손 레이블 표시                  | 「MediaPipe 실시간 신체 인식」의 손 검출 예제                 |
| `mp_hand_rulebased.py`       | 손 랜드마크의 관절 각도로 펼친 손가락 수를 계산해 표시                          | 「MediaPipe 실시간 신체 인식」의 규칙 기반 손가락 개수 예제   |
| `README.md`                  | 이 폴더의 준비 사항, 실행 방법, 각 파일 설명                                    | 실습 안내                                                     |

## 실행 환경과 import

네 스크립트 모두 Linux의 `/dev/video0` 웹캠을 GStreamer 파이프라인(`v4l2src` → `videoconvert` → `appsink`)으로 읽으며, 640×480, YUY2, 30 fps 입력을 지정합니다. 따라서 **접근 가능한 `/dev/video0` 카메라, GStreamer와 관련 플러그인, GStreamer 지원이 포함된 OpenCV, 영상 창을 표시할 그래픽 환경**이 필요합니다. 노트북의 Jetson CSI 카메라 예시는 `nvarguscamerasrc`를 사용하지만, 이 폴더의 스크립트는 모두 `v4l2src` 웹캠용입니다. 다른 카메라를 쓰려면 각 파일의 `pipeline`을 환경에 맞게 수정해야 합니다.

| import                                      | 사용 파일                                                                         | 역할                                                                   |
| ------------------------------------------- | --------------------------------------------------------------------------------- | ---------------------------------------------------------------------- |
| `import cv2`                                | 네 파일 모두                                                                      | 카메라 입력, 색공간 변환, 마스크·외곽선 처리, 화면 표시 및 도형 그리기 |
| `import numpy as np`                        | `pingpong_circle_overlay.py`, `pingpong_kalman_filter.py`, `mp_hand_rulebased.py` | 색상 범위·마스크·행렬 생성 및 손가락 각도 계산                         |
| `from numpy.linalg import inv`              | `pingpong_kalman_filter.py`                                                       | Kalman 보정 단계의 행렬 역행렬 계산                                    |
| `import mediapipe as mp`                    | `mp_hand.py`, `mp_hand_rulebased.py`                                              | 입력 프레임을 MediaPipe `Image`로 전달                                 |
| `from mediapipe.tasks import python`        | 손 검출 두 파일                                                                   | 모델 경로를 지정하는 `BaseOptions`                                     |
| `from mediapipe.tasks.python import vision` | 손 검출 두 파일                                                                   | `HandLandmarker`, 옵션 및 랜드마크 연결 정보                           |

필요한 Python 패키지는 **NumPy, OpenCV(`cv2`), MediaPipe(손 검출 파일만)** 입니다. 이 네 스크립트는 노트북 앞부분에서 사용한 Matplotlib이나 scikit-image를 import하지 않습니다. 특히 Jetson에서는 노트북의 설명처럼 기존 시스템 OpenCV와 Python 환경의 호환성을 확인해야 합니다. `opencv-python`을 설치했다는 사실만으로 해당 빌드의 GStreamer 지원이 보장되지는 않습니다. 설치된 OpenCV에서 `cv2.getBuildInformation()`의 GStreamer 항목을 확인할 수 있습니다.

손 검출 파일은 저장소 루트를 현재 작업 디렉터리로 삼았을 때 `src/models/MediaPipe/hand_landmarker.task`를 찾습니다. **현재 저장소에는 이 모델 파일이 포함되어 있지 않으므로 별도로 준비해야 합니다.** 노트북의 「MediaPipe 실시간 신체 인식」 부분에는 MediaPipe 설치 명령과 모델 다운로드 예시가 있습니다. 두 손 검출 파일을 실행하기 전에 모델 파일을 위 경로에 배치하세요. 탁구공 파일에는 모델이 필요하지 않습니다.

## 실행 방법

저장소 루트에서 필요한 스크립트를 하나씩 실행합니다. 경로가 상대 경로인 손 모델도 이 위치를 기준으로 찾습니다.

```bash
python 2026.10.18/pingpong_circle_overlay.py
python 2026.10.18/pingpong_kalman_filter.py
python 2026.10.18/mp_hand.py
python 2026.10.18/mp_hand_rulebased.py
```

표시 창에서 `q`를 누르면 종료합니다. 카메라 프레임을 읽지 못하면 반복문이 끝나므로, 화면이 바로 닫힐 때는 카메라 장치·GStreamer 파이프라인·OpenCV 빌드를 확인하세요.

## 파일별 처리 과정

### `pingpong_circle_overlay.py`

1. 웹캠 프레임을 BGR에서 LAB로 변환하고, `green_lower=[30, 60, 90]`, `green_upper=[230, 115, 180]` 범위의 초록색을 `cv2.inRange()`로 이진 마스크화합니다. 이 임계값은 코드에 고정되어 있어 조명과 공 색에 따라 조정이 필요할 수 있습니다.
2. **5×5 타원형 커널로 `cv2.MORPH_OPEN`을 1회** 적용합니다. Open은 침식 뒤 팽창으로 작은 독립 잡음을 제거하는 모폴로지 연산입니다. 원형 탁구공에 맞는 타원형 커널을 사용했고, 일반 색상 마스크에 Gaussian blur까지 적용해야 할 만큼 큰 노이즈는 없었습니다. 공 영역도 비교적 잘 잡혔지만 자잘한 노이즈가 남아 있어 Open만 1회 수행했습니다. Close는 해본 결과 오토바이 예제처럼 이어야 할 부분이 없기 때문에 하지 않았습니다.
3. 정제된 마스크에서 외부 외곽선을 찾고 가장 큰 외곽선을 공 후보로 선택합니다. 해당 영역을 반투명 빨간색으로 칠하고 외곽선과 `cv2.minEnclosingCircle()`의 원·중심을 그립니다. **가장 큰 초록색 영역을 공으로 가정**하므로 비슷한 색의 큰 물체가 있으면 그 물체를 선택할 수 있습니다.

### `pingpong_kalman_filter.py`

위 파일과 동일한 LAB 색상 분할, 5×5 타원형 커널의 Open 1회, 최대 외곽선 검출·영역 표시를 수행한 다음 Kalman Filter 추적을 더합니다. 외곽선의 `cv2.moments()`로 무게중심을 측정하고 파란 원으로 표시합니다. 직접 정의한 `KalmanFilter()`는 상태 전이 행렬 `A_t`, 과정 잡음 `R_t`, 관측 행렬 `C_t`, 관측 잡음 `Q_t`를 사용합니다. 공이 검출되면 예측과 측정값 보정을 함께 수행하고, 검출되지 않으면 예측만 수행합니다. 추정 위치는 노란 원으로 표시하며, 반지름은 마지막 검출 값을 사용합니다. 노트북에는 `cv2.KalmanFilter` 예시도 있지만, **이 파일은 NumPy 행렬로 직접 정의한 함수**를 사용합니다.

### `mp_hand.py`

MediaPipe Tasks의 `HandLandmarker`를 `num_hands=2`로 생성합니다. BGR 카메라 프레임을 RGB로 바꾸어 손을 검출하고, 각 손의 랜드마크 연결선을 초록색, 손가락 끝 점을 빨간색, 나머지 관절 점을 파란색으로 표시합니다. 화면에는 감지된 손의 수와 Left/Right 텍스트도 나타납니다.

### `mp_hand_rulebased.py`

`mp_hand.py`의 랜드마크 시각화에 규칙 기반 손가락 수 계산을 더합니다. 각 손가락에서 지정된 세 랜드마크의 **3차원 좌표로 가운데 관절 각도**를 구하고, 각도가 `160°` 이상이면 펼쳐졌다고 세어 모든 검출 손의 개수를 합산합니다. 화면에 `Hands`, `Fingers`, Left/Right 레이블을 표시합니다. 이는 각도 임계값에 따른 단순 판정으로, 손의 회전·가림·엄지 자세에 따라 실제 펼친 손가락 수와 달라질 수 있습니다.
