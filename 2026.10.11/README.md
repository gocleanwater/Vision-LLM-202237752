# 2강(2026.10.11) 과제

## 과제 개요

2026년 10월 11일 수업의 Computer Vision 과제입니다.

OpenCV와 NumPy를 활용하여 색 공간 변환, 이미지 채널 조정, 샤프닝, 경계 처리 방식 비교 및 unsharp masking을 수행합니다.

## 제출 파일

- `[STUDENT]_02_Computer-Vision_Assignment.py`: Python 과제 실행 파일
- `src/images/sky.png`: unsharp masking에 사용하는 입력 이미지

## 폴더 구조

```text
2026.10.11/
├── [STUDENT]_02_Computer-Vision_Assignment.py
├── README.md
└── src/
    └── images/
        └── sky.png
```

## 실행 환경

- Python 3
- NumPy
- OpenCV
- Matplotlib
- scikit-image

## 의존성 설치

터미널에서 다음 명령어를 실행합니다.

```bash
python -m pip install numpy opencv-python matplotlib scikit-image
```

## 실행 방법

터미널에서 `2026.10.11` 폴더로 이동한 후 다음 명령어를 실행합니다.

```bash
python "[STUDENT]_02_Computer-Vision_Assignment.py"
```

## 참고 사항

- 프로그램은 `skimage.data.astronaut()` 예제 이미지와 `src/images/sky.png` 파일을 사용합니다.
- `sky.png`를 상대 경로로 불러오므로 반드시 과제 폴더에서 프로그램을 실행해야 합니다.
- 실행 결과는 Matplotlib을 이용한 이미지와 subplot으로 시각화됩니다.
- 실행 환경에 따라 그래프 창이 자동으로 표시되지 않을 수 있습니다.
- 한글이 포함된 파일은 UTF-8 인코딩으로 저장하는 것을 권장합니다.
