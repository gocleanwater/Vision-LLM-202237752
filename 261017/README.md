# 2강(2026.10.17) 컴퓨터 비전 과제

- 이름: 고정수
- 학번: 202237752

## 과제 개요

`02_Computer-Vision.ipynb`에서 실습한 농구공 영역 검출 코드를 독립된 Python 과제 파일로 정리했습니다. LAB 색상 분할, CLAHE 밝기 보정, 모폴로지 연산, 최대 외곽선 검출을 거쳐 농구공 영역과 외곽선을 초록색으로 표시합니다.

## 구조

```text
2026.10.17/
├── assignment02.py  # 과제 실행 파일
└── README.md        # 과제 설명 및 실행 방법
```

입력 이미지는 저장소의 `src/images/basketball_crop.jpg`를 사용합니다. 과제 폴더 안에는 이미지를 복사하지 않습니다.

## 실행 환경 및 의존성

- Python 3
- NumPy
- OpenCV (`opencv-python`)
- Matplotlib

```bash
python -m pip install numpy opencv-python matplotlib
```

## 실행 방법

저장소 루트에서 다음 명령을 실행합니다.

```bash
python 2026.10.17/assignment02.py
```

실행하면 농구공 영역과 외곽선이 표시된 이미지 창이 열립니다. 이미지 창을 닫으면 프로그램이 종료됩니다. 과제 폴더는 저장소의 `src` 폴더와 같은 상위 경로에 있어야 합니다.

## 참고 사항

- 모폴로지 연산은 5×5 타원형 커널로 열기 2회, 닫기 3회를 적용합니다.
- 검출된 외곽선 가운데 면적이 가장 큰 것만 농구공 영역으로 선택합니다.
- OpenCV 이미지의 BGR 채널 순서를 Matplotlib 표시 전에 RGB로 변환합니다.
