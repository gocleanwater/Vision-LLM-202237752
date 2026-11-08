"""04 notebook workflow on Jetson: ONNX, FP32, FP16, calibrated INT8."""

import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import random
import shutil
import subprocess
import sys
import time

os.environ["YOLO_AUTOINSTALL"] = "False"


def save_json(path, value):
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")
    temporary.replace(path)


def prepare(source, work):
    import yaml
    from PIL import Image

    cfg = yaml.safe_load((source / "data.yaml").read_text())
    pool = sorted((source / "train/images").glob("*.jpg"))
    random.Random(42).shuffle(pool)
    labels = {}
    for p in pool:
        rows = (source / "train/labels" / (p.stem + ".txt")).read_text().splitlines()
        labels[p] = {int(row.split()[0]) for row in rows if row.strip()}
    # Include every training class before filling the remaining slots.
    selected = []
    covered = set()
    for cls in sorted(range(len(cfg["names"])), key=lambda k: sum(k in v for v in labels.values())):
        if cls in covered:
            continue
        candidate = next(p for p in pool if cls in labels[p] and p not in selected)
        selected.append(candidate)
        covered.update(labels[candidate])
    selected.extend(p for p in pool if p not in selected)
    selected = selected[:500]
    assert len(selected) == 500
    assert set.union(*(labels[p] for p in selected)) == set(range(len(cfg["names"])))
    calibration = work / "calibration"
    (calibration / "images").mkdir(parents=True, exist_ok=True)
    (calibration / "labels").mkdir(exist_ok=True)
    manifest = []
    for p in selected:
        with Image.open(p) as image:
            image.verify()
        destination = calibration / "images" / p.name
        if not destination.exists():
            shutil.copy2(p, destination)
        digest = hashlib.sha256(p.read_bytes()).hexdigest()
        assert hashlib.sha256(destination.read_bytes()).hexdigest() == digest
        (calibration / "labels" / (p.stem + ".txt")).touch()
        manifest.append({"source": str(p.relative_to(source)), "sha256": digest,
                         "classes": sorted(labels[p])})
    assert len(list((calibration / "images").glob("*.jpg"))) == 500
    calibration_cfg = {"path": str(calibration), "train": "images", "val": "images", "names": cfg["names"]}
    (calibration / "calibration.yaml").write_text(yaml.safe_dump(calibration_cfg, allow_unicode=True, sort_keys=False))
    save_json(calibration / "manifest.json", {
        "source_dataset": "https://universe.roboflow.com/yaman-e/food-ingredients-detection-qfit7/dataset/48",
        "author": "Yaman E", "license": "CC BY 4.0", "count": 500, "seed": 42,
        "selection": "All 36 classes covered, then deterministic shuffled training images only",
        "limitation": "Public ingredient photos; not captured in the final deployment environment",
        "files": manifest,
    })
    print("Calibration ready: 500 training images, 36 classes; validation/test excluded", flush=True)


def model_stage(stage, work, source):
    from ultralytics import YOLO

    model_path = work / "ingredients.pt"
    if stage == "onnx":
        import onnx
        path = YOLO(str(model_path)).export(format="onnx", imgsz=640, batch=1,
                                          dynamic=False, simplify=True, opset=20)
        onnx.checker.check_model(onnx.load(str(path)))
    elif stage == "int8":
        model = YOLO(str(model_path))
        path = model.export(format="engine", imgsz=640, quantize=8,
                            data=str(work / "calibration/calibration.yaml"),
                            batch=1, dynamic=False, device=0, nms=False)
        engine = Path(path).replace(work / "ingredients_int8.engine")
        with engine.open("rb") as f:
            size = int.from_bytes(f.read(4), "little")
            assert 0 < size < 1024 * 1024
            metadata = json.loads(f.read(size))
            raw = f.read()
        assert raw and len(metadata["names"]) == 36
        (work / "ingredients_int8_raw.engine").write_bytes(raw)
        save_json(work / "int8_metadata.json", metadata)
    else:
        import yaml
        cfg = yaml.safe_load((source / "data.yaml").read_text())
        cfg.update(path=str(source), train="train/images", val="valid/images", test="test/images")
        data = work / "evaluation.yaml"
        data.write_text(yaml.safe_dump(cfg, sort_keys=False))
        path = model_path if stage == "validate_pt" else work / "ingredients_int8.engine"
        result = YOLO(str(path), task="detect").val(
            data=str(data), split="val", imgsz=640, batch=1, device=0,
            plots=False, verbose=False, workers=0,
            project=str(work / "validation"), name=stage, exist_ok=False)
        save_json(work / (stage + ".json"), {
            "metrics": {key: float(value) for key, value in result.results_dict.items()},
            "speed_ms": result.speed,
        })


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--work-dir", type=Path, required=True)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--prepare-only", action="store_true")
    parser.add_argument("--stage", choices=["onnx", "int8", "validate_pt", "validate_int8"])
    args = parser.parse_args()
    work = args.work_dir.resolve()
    source = args.dataset.resolve()
    work.mkdir(parents=True, exist_ok=True)
    if args.stage:
        model_stage(args.stage, work, source)
        return
    prepare(source, work)
    if args.prepare_only:
        return
    import fcntl
    with (work / "job.lock").open("w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        model = work / "ingredients.pt"
        expected = json.loads((work / "transfer.json").read_text())["sha256"]
        assert hashlib.sha256(model.read_bytes()).hexdigest() == expected
        trtexec = "/usr/src/tensorrt/bin/trtexec"
        assert Path(trtexec).is_file()
        status = {"status": "running", "started_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                  "model_sha256": expected, "imgsz": 640, "batch": 1, "steps": []}
        save_json(work / "optimization_status.json", status)

        def run(name, command):
            status["current_step"] = name
            save_json(work / "optimization_status.json", status)
            print("START", name, flush=True)
            start = time.monotonic()
            with (work / (name + ".log")).open("w") as log:
                subprocess.run(command, cwd=work, stdout=log, stderr=subprocess.STDOUT, check=True)
            status["steps"].append({"name": name, "seconds": round(time.monotonic() - start, 2)})
            save_json(work / "optimization_status.json", status)
            print("DONE", name, flush=True)

        def child(stage):
            return [sys.executable, "-u", str(Path(__file__).resolve()), "--work-dir", str(work),
                    "--dataset", str(source), "--stage", stage]

        try:
            run("onnx", child("onnx"))
            for precision in ["fp32", "fp16"]:
                command = [trtexec, "--onnx=" + str(work / "ingredients.onnx"),
                           "--saveEngine=" + str(work / ("ingredients_" + precision + ".engine"))]
                if precision == "fp16":
                    command.append("--fp16")
                run("build_" + precision, command)
            run("int8", child("int8"))
            for precision in ["fp32", "fp16", "int8_raw"]:
                engine = work / ("ingredients_" + precision + ".engine")
                run("benchmark_" + precision, [trtexec, "--loadEngine=" + str(engine),
                                              "--warmUp=500", "--duration=10"])
            run("validate_pt", child("validate_pt"))
            run("validate_int8", child("validate_int8"))
            status.update(status="completed", current_step="completed")
        except Exception as error:
            status.update(status="failed", error=str(error))
            raise
        finally:
            status["updated_utc"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
            save_json(work / "optimization_status.json", status)


if __name__ == "__main__":
    main()
