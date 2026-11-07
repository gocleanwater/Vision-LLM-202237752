# 식재료 탐지 YOLO11n 학습

가족의 식사 메뉴를 고민하는 부담을 줄이는 음성 메뉴 추천 프로젝트의 식재료 탐지 모델입니다.

## 실행

Python 3.12 가상환경에 `requirements-ingredients.txt`를 설치합니다.

```bash
python3.12 -m venv .venv-ingredients
.venv-ingredients/bin/python -m pip install -r requirements-ingredients.txt
.venv-ingredients/bin/python train_yolo_ingredients.py --epochs 1 --device mps --batch 8
```

`--device auto`가 기본값이며 CUDA, MPS, CPU 순서로 사용 가능한 장치를 선택합니다.
Jetson에서는 `--device 0 --batch 1`을 사용할 수 있습니다. 기본 입력 크기는 416입니다.
`--epochs 30`으로 학습 횟수를 바꿀 수 있습니다. 첫 시험 결과로 메모리와 소요 시간을 확인한 뒤 결정합니다.

결과는 `runs/ingredients/trial*/` 또는 `runs/ingredients/train*/`에 저장됩니다.
`weights/best.pt`가 검증 결과 기준 최적 가중치입니다. 1 epoch는 실행 확인용이며 정확도를 보장하지 않습니다.
Mac에서 얻은 `.pt`를 Jetson으로 옮겨 해당 Jetson에서 TensorRT로 변환합니다. 기존 INT8 엔진은 재사용하지 않습니다.

## 데이터 출처와 변경

- 원본: Yaman E, [FOOD INGREDIENTS DETECTION v48](https://universe.roboflow.com/yaman-e/food-ingredients-detection-qfit7/dataset/48), CC BY 4.0.
- 복사 출처: [ahmedalashii/Yolov11-Ingredients-Detection](https://github.com/ahmedalashii/Yolov11-Ingredients-Detection), 정확한 커밋은 데이터 폴더의 `SOURCE.json`에 기록되어 있습니다.
- 저장소 사본은 학습 1,425장, 검증 286장, 테스트 190장으로 총 1,901장입니다. 원본 페이지의 1,904장과 차이가 있습니다.
- 클래스 번호는 유지하고 다각형 라벨 3개를 외접 사각형으로 변환했습니다. `POLYGON_CONVERSION.json`에 기록했습니다.
- 경로는 YAML 위치를 기준으로 찾도록 변경했습니다. 테스트 세트는 학습·하이퍼파라미터 선택에 사용하지 않습니다.
- [CC BY 4.0 사용 조건](https://creativecommons.org/licenses/by/4.0/): 원작자와 출처를 표시하고 변경 사항을 명시합니다.

## 모델 출처

`src/models/YOLO/yolo11n.pt`는 식재료 전용으로 학습되기 전의 Ultralytics COCO 사전 학습 모델입니다.
[공식 YOLO11](https://docs.ultralytics.com/models/yolo11/), [모델 배포](https://github.com/ultralytics/assets), [Ultralytics 라이선스](https://www.ultralytics.com/license).
학습 환경, 로그, 생성된 가중치는 Git에 포함하지 않습니다.
