# 편집용 발표자료

`Project02_Ingredients_Menu_Assistant.pptx`는 PowerPoint에서 수정할 수 있는 16:9 발표자료다. 글자와 표는 편집 가능한 객체이고, 데이터셋 사진은 파일 안에 포함되어 있다. Mac에 PowerPoint가 없어도 이 파일을 다른 노트북으로 옮겨 열면 된다.

## 7장 구성

1. 표지 — 오늘 뭐 먹지?
2. 주제 선정 이유 — 어머니의 메뉴 고민을 줄이고 싶었다.
3. 사용한 수업 기술 — YOLO, Gemma VLM·LLM, Whisper STT, Piper TTS.
4. 동작 흐름 — 음성 인식, FP32 탐지, 조건부 VLM 확인, 최근 식사 제외, 메뉴 검증과 음성 안내.
5. 공개 데이터 — GitHub 링크와 저장소 사본의 실제 양파·양배추·레몬 사진.
6. 파인튜닝 — 공개 bbox 라벨 준비, 다각형 3개 변환, Mac 30 epoch 학습, `best.pt` 선택.
7. 기능 예시 — 재료 조회, 메뉴 추천, 다른 메뉴 요청, 식사 기록, 구매 재료 안내를 가상 대화로 설명.

`Project02_presentation.pdf`에도 같은 7장 구성을 반영했다. PPTX의 흐름도 도형과 화살표는 직접 편집할 수 있다.

슬라이드 노트에 짧은 발표 설명과 출처를 적었다. 사진은 실제 탐지 결과나 현장 사진이 아니라 데이터셋 원본 예시다.

## 다른 노트북에서 수정

- PowerPoint로 PPTX를 열고 텍스트 상자·표·사진을 직접 수정한다.
- 사용한 글꼴은 `Apple SD Gothic Neo`다. Windows에서 글꼴이 없거나 줄바꿈이 달라지면 PowerPoint의 글꼴 바꾸기로 `맑은 고딕`을 적용하고 위치를 확인한다.
- 데이터 출처와 원작자 표기는 유지한다. 실제 시연 결과를 추가할 때는 예시와 구분한다.
- 저장소 사본에서 파일을 수정했다면 저장 후 다음처럼 커밋·push한다. 먼저 `git status`로 다른 변경도 확인한다.

```bash
git add '[Project02]/presentation/Project02_Ingredients_Menu_Assistant.pptx'
git commit -m "docs: Project02 발표자료 수정"
git push origin main
```

## 데이터 출처

- 공개 사본: [ahmedalashii/Yolov11-Ingredients-Detection](https://github.com/ahmedalashii/Yolov11-Ingredients-Detection)
- 원본: Yaman E, [FOOD INGREDIENTS DETECTION v48](https://universe.roboflow.com/yaman-e/food-ingredients-detection-qfit7/dataset/48)
- 데이터 라이선스: CC BY 4.0. 원본 사진의 표시 크기만 조정했고, 탐지 상자나 모델 결과를 추가하지 않았다.
