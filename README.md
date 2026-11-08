# 가천대학교 AI 부트캠프 "온디바이스 AI" 수업 레포지토리

## 강의 및 기간 등 세부사항

> **강의명:** &nbsp;&ensp; Physical AI의 Vision-LLM 융합 시청각 멀티모달 시스템<br>
> **강사:** &nbsp;&nbsp;&emsp; 김규래<br>
> **기간:** &nbsp;&nbsp;&emsp; 2026/10/10 - 2026/11/8<br>
> **시간:** &nbsp;&nbsp;&emsp; 토/일 13:00 - 17:30<br>
> **장소:** &nbsp;&nbsp;&emsp; 경기도 성남시 분당구 대왕판교로606번길 47 2층, 한컴 AX LAB (H 강의장)<br>
> **연락처:** &nbsp;&ensp; kkr.kyurae.kim<!---->@gmail.com<br>

---

## 폴더 구조

주요 파일과 폴더는 다음과 같다.

```text
Vision-LLM-202237752/
├── README.md
├── .gitignore
├── lecture_ipynb_files/               # 강의 실습 노트북
│   ├── 00_Initial-Setup.ipynb
│   ├── 01_Linux-and-Python.ipynb
│   ├── 02_Computer-Vision.ipynb
│   ├── 03_DL-and-GPU.ipynb
│   ├── 04_DL-Object-Detection.ipynb
│   ├── 05-LLM_and_Gemma.ipynb
│   └── 06-Vision_LLM_Multimodal_Systems.ipynb
├── 261010/                           # Linux·Python 과제
│   ├── README.md
│   ├── [Student] 01_Linux-and-Python_Assignment.py
│   ├── 맹구_개인정보.json
│   └── 맹구_개인정보.yaml
├── 261017/
│   ├── README.md
│   └── assignment02.py
├── 261018/                           # 손 인식·탁구공 추적 실습
│   ├── mp_hand.py
│   ├── mp_hand_rulebased.py
│   ├── pingpong_circle_overlay.py
│   └── pingpong_kalman_filter.py
├── 261101/                           # CNN·GPU 학습·IoU/NMS·NumPy/CuPy 과제
│   ├── README.md
│   ├── cnn_filter_assignment.py
│   ├── mnist_cnn_assignment.py
│   ├── MNIST_main_gpu.py
│   ├── CIFAR10_main_gpu.py
│   ├── iou_assignment.py
│   ├── nms_assignment.py
│   ├── motion_trail_assignment.py
│   ├── convolution_assignment.py
│   └── image.png
├── [Project01]/                      # 색깔 순발력 테스트
│   ├── README.md
│   ├── .gitignore
│   ├── main.py
│   ├── vision.py
│   ├── game.py
│   ├── contracts.py
│   └── assets/fonts/                 # 한글 폰트와 라이선스
│       ├── NotoSansKR-wght.ttf
│       └── OFL.txt
├── [Project02]/                      # 식재료 기반 음성 메뉴 추천
│   ├── README.md
│   ├── .gitignore
│   ├── main.py
│   ├── vision.py
│   ├── gemma.py
│   ├── speech.py
│   ├── ingredients_fp32.engine
│   ├── full_demo.mp4
│   ├── yolo_demo.mp4
│   └── presentation/                # 발표 자료
│       ├── README.md
│       ├── Project02_Ingredients_Menu_Assistant.pptx
│       └── Project02_presentation.pdf
├── yolo/                             # YOLO 추론·FPS 측정
│   ├── yolo_11_n.py
│   └── yolo_11_n_fps.py
├── optimized_model/                  # YOLO TensorRT·INT8 최적화
│   ├── calibration_data_set.py
│   ├── int8_yolo.py
│   └── tensor_rt_yolo.py
├── stt_tts/                          # 음성 인식·음성 합성
│   ├── stt.py
│   ├── tts.py
│   └── stt_tts.py
├── train_yolo_ingredients.py          # 식재료 YOLO 학습
├── optimize_yolo_ingredients.py       # 식재료 YOLO 최적화
├── optimize_yolo_ingredients.before_int8_only_20261107T094659Z.py
├── src/                              # 로컬 데이터·모델·입출력 리소스
│   ├── audio/
│   ├── datasets/
│   ├── images/
│   ├── models/
│   └── output/
└── runs/                             # 로컬 학습 결과
    └── ingredients/
```
