"""Mac(MPS) 또는 Jetson(CUDA)에서 식재료 탐지용 YOLO11n을 파인튜닝합니다.

기본 실행은 1 epoch 시험 학습입니다.
    .venv/bin/python train_yolo_ingredients.py
    .venv/bin/python train_yolo_ingredients.py --epochs 30
"""

import argparse
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent
MODEL_PATH = ROOT_DIR / "src/models/YOLO/yolo11n.pt"
DATA_PATH = ROOT_DIR / "src/datasets/food_ingredients_v48/data.yaml"
OUTPUT_DIR = ROOT_DIR / "runs/ingredients"


def main():
    parser = argparse.ArgumentParser(description="식재료 탐지용 YOLO11n 학습")
    parser.add_argument("--epochs", type=int, default=1, help="학습 횟수 (기본: 1)")
    parser.add_argument("--imgsz", type=int, default=416, help="입력 이미지 크기 (기본: 416)")
    parser.add_argument("--batch", type=int, default=1, help="배치 크기 (기본: 1)")
    parser.add_argument("--device", default="auto", help="auto, mps, cpu 또는 CUDA GPU 번호 (기본: auto)")
    args = parser.parse_args()

    if min(args.epochs, args.imgsz, args.batch) < 1:
        parser.error("epochs, imgsz, batch는 모두 1 이상이어야 합니다.")
    for path in (MODEL_PATH, DATA_PATH):
        if not path.is_file():
            parser.error(f"파일을 찾을 수 없습니다: {path}")

    import torch
    from ultralytics import YOLO

    device = args.device
    if device == "auto":
        if torch.cuda.is_available():
            device = "0"
        elif torch.backends.mps.is_available():
            device = "mps"
        else:
            device = "cpu"
    print(f"학습 장치: {device}", flush=True)

    model = YOLO(str(MODEL_PATH))
    results = model.train(
        data=str(DATA_PATH),
        epochs=args.epochs,
        imgsz=args.imgsz,
        batch=args.batch,
        workers=0,
        cache=False,
        device=device,
        project=str(OUTPUT_DIR),
        name="trial" if args.epochs == 1 else "train",
        exist_ok=False,
    )

    print(f"학습 결과 폴더: {model.trainer.save_dir}")
    print(f"최적 가중치: {model.trainer.best}")
    print(results)


if __name__ == "__main__":
    main()
