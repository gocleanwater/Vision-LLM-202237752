# MacBook Codex 작업 인수인계

작성 기준일: 2026-10-21 (Asia/Seoul)

이 문서는 Windows의 현재 작업 폴더를 MacBook으로 복사한 뒤, 과거 채팅 기록이 없는 새 Codex 세션에서 개발을 이어가기 위한 진입점이다. 활성 프로젝트는 저장소 전체의 수업 자료가 아니라 **`[Project01]/`의 「Jetson 컬러 볼 리액션 챌린지」**다.

## 0. 먼저 알아야 할 현재 상태

- **코드에서 확인:** `[Project01]/`에는 Markdown 문서 5개와 UI 목업 1개만 있다. 게임 실행 코드, 테스트, 패키지 명세, 한글 폰트는 아직 없다.
- **Git에서 확인:** 2026-10-21 현재 브랜치는 `main`, HEAD는 `4992a02`이며 `origin/main`과 같다. 그러나 `[Project01]/` 전체가 Git 미추적 상태다. 이 `HANDOFF.md`도 새 파일이므로 생성 직후에는 미추적 상태다. 폴더를 직접 복사하지 않고 Git만 이용해 이동할 경우 두 항목이 누락된다.
- **문서에서 확인:** 프로젝트 상태는 “기획 및 규칙 명세 작성 단계”다. 구현이나 Jetson 실기 검증이 완료됐다고 해석하면 안 된다.
- **현재 대화에서 확인:** 사용자는 프로젝트 폴더 전체를 별도로 MacBook으로 옮기고, 기존 채팅 기록 없이 새 Codex 세션을 시작할 예정이다. 기존 소스는 수정하지 않고 이 인수인계 문서만 만들도록 요청했다.
- **과거 결정의 근거 한계:** 이 세션에 과거 채팅 원문 전체가 제공된 것은 아니다. 아래의 “대화에서 결정” 항목은 `[Project01]/documents/OPEN_DECISIONS.md` 등에 **사용자 채택 또는 사용자 보고**로 기록된 내용을 옮긴 것이다. 원문 대화가 필요한 세부사항은 `확인 필요`로 표시한다.

이 문서의 근거 표시는 다음과 같다.

- **[코드 확인]** 실제 파일·코드·Git 상태에서 직접 확인한 사실
- **[문서상 결정]** 프로젝트 문서에 채택안으로 기록된 설계
- **[사용자 보고/미검증]** 문서에 사용자 보고로만 남아 있고 현재 환경에서 검증하지 못한 내용
- **[확인 필요]** 증거가 없거나 장비·현장에서 확인해야 하는 내용

## 1. 프로젝트 개요

### 목적

Jetson에 연결한 고정 USB 카메라 영상에서 빨강·초록·파랑 탁구공과 사용자의 양손을 인식하고, 화면이 지정한 색 공을 **물리적 왼손과 오른손**에 올바르게 제시했는지 판정하는 반응 게임을 만든다. 정답 횟수와 반응 시간을 기록하고, 오답 또는 시간 초과 시 기회를 차감한다. **[문서상 결정]**

### 첫 완성 범위의 주요 기능

- 한 사람, 양손, USB 카메라 1대, 빨강·초록·파랑 공 각 1개를 사용한다.
- 라운드마다 서로 다른 두 색을 왼손과 오른손에 하나씩 무작위 배정한다.
- MediaPipe 손 랜드마크로 물리적 왼손·오른손, `hand_box`, `palm_box`를 구한다.
- LAB 기반 색상 분할, 모폴로지, 외곽선으로 공의 실제 위치를 찾는다.
- 지정 공 2개가 각 손에 연결되고 선택되지 않은 세 번째 공이 출발 영역에 실제로 보일 때만 정답 후보로 삼는다.
- 정답은 +1점, 확정 오답 또는 시간 초과는 기회 -1, 시작 기회는 3개다.
- 실제 검출과 Kalman 예측을 다른 스타일로 표시한다. 예측은 채점하지 않는다.
- 세로형 카메라 화면과 상·하 정보 띠를 하나의 `cv2.imshow()` 창에 표시한다.

### 기술 스택

| 구분 | 현재 계획 또는 기존 코드 |
| --- | --- |
| 언어 | Python 3. 정확한 버전은 **확인 필요** |
| 영상 처리 | OpenCV (`cv2`), NumPy |
| 손 인식 | MediaPipe Tasks `HandLandmarker` |
| 한글 UI | Pillow + 프로젝트에 포함할 한글 폰트. 아직 파일 없음 |
| 카메라 | Jetson/Linux의 GStreamer `v4l2src` + OpenCV GStreamer backend |
| 추적 | 색별 OpenCV `cv2.KalmanFilter` |
| 테스트 방향 | 카메라와 분리한 순수 게임 로직 + 가짜 관측 시퀀스. 테스트 프레임워크는 **확인 필요** |
| 참고 실습 | Jupyter Notebook, Matplotlib, 기존 직접 구현 Kalman filter |

패키지 버전은 고정되어 있지 않으며 `requirements.txt`, `pyproject.toml`, Conda 환경 파일도 없다. **[코드 확인]**

## 2. 아키텍처

### 현재 디렉터리 구조

```text
./
├── HANDOFF.md                         # 이 인수인계 문서
├── README.md                          # 저장소 최상위의 최소 설명
├── 00_Initial-Setup.ipynb             # 수업 초기 설정 노트북
├── 01_Linux-and-Python.ipynb          # Linux/Python 수업 노트북
├── 02_Computer-Vision.ipynb           # 프로젝트 기술의 원 수업 노트북
├── 2026.10.10/                        # Python 과제
├── 2026.10.17/                        # 정적 이미지 농구공 검출 과제
├── 2026.10.18/                        # 실시간 공/손 검출 실습 코드
│   ├── pingpong_circle_overlay.py
│   ├── pingpong_kalman_filter.py
│   ├── mp_hand.py
│   ├── mp_hand_rulebased.py
│   └── README.md
├── src/
│   ├── images/                        # 수업용 정적 이미지
│   ├── models/MediaPipe/.gitkeep      # 모델 디렉터리만 있고 .task 파일은 없음
│   ├── datasets/calibration/.gitkeep
│   └── output/.gitkeep
└── [Project01]/                       # 활성 프로젝트; 현재 전체가 Git 미추적
    ├── README.md
    └── documents/
        ├── PROJECT_PLAN.md
        ├── GAME_RULES.md
        ├── IMPLEMENTATION_CHECKLIST.md
        ├── OPEN_DECISIONS.md
        └── portrait_ui_mockup.png
```

### 예정 모듈과 책임

아래 파일은 `[Project01]/documents/PROJECT_PLAN.md`에 정한 **계획**이며 아직 존재하지 않는다. 역할 경계는 유지하되 구현 중 파일 수는 조정할 수 있다.

| 예정 파일 | 책임 |
| --- | --- |
| `[Project01]/main.py` | 실행 진입점, 프레임 루프, 모듈 조립 |
| `[Project01]/camera.py` | USB 카메라와 저장 영상의 공통 입력 인터페이스, 입력 오류 |
| `[Project01]/vision.py` | 색상 분할, 공 후보, 손 인식, 손과 공의 연결 |
| `[Project01]/tracking.py` | 색별 `cv2.KalmanFilter`, 보정·예측·재검출·lost 처리 |
| `[Project01]/game.py` | 프레임에 직접 의존하지 않는 상태 전이, 문제, 시간, 점수, 판정 |
| `[Project01]/overlay.py` | 손·공·영역 오버레이와 Pillow 기반 한글 정보 띠 |
| `[Project01]/config.py` | 색 임계값, 영역 좌표, 시간, 카메라 및 판정 설정 |

### 계획된 데이터 흐름

```text
USB 카메라 또는 저장 영상
  → 프레임 읽기
  → 즉시 시계방향 90° 회전
  → 공 관측: 전처리 → 색별 분할 → morphology → contour → 실제 중심/크기
  → 손 관측: BGR→RGB → MediaPipe → 물리적 손 보정 → hand_box/palm_box
  → 구조화된 FrameObservation
  → game.py 상태기계와 판정
  → tracking.py 예측 정보 결합(표시·재연결 보조만)
  → overlay.py가 영상과 상·하 정보 띠를 한 이미지로 합성
  → cv2.imshow() 단일 창
```

핵심 의존 방향은 **카메라/비전 → 구조화된 관측 → 게임 로직**이다. `game.py`가 OpenCV 프레임이나 카메라에 직접 의존하지 않게 만들어 가짜 관측으로 먼저 검증하는 것이 채택된 방향이다. **[문서상 결정]**

### 게임 상태기계

```text
SETUP → READY → COUNTDOWN → ACTIVE
                           ├→ RESULT_SUCCESS → RESET ─┐
                           ├→ RESULT_WRONG   → RESET ─┤→ READY
                           ├→ RESULT_TIMEOUT → RESET ─┘
                           └→ PAUSED → 현재 시도 무효 → READY

기회가 0이면 RESULT_WRONG/RESULT_TIMEOUT 또는 RESET → SUMMARY
```

정확한 전이 조건과 장애 우선순위는 이 문서에 복제하지 않고 `[Project01]/documents/GAME_RULES.md` 6절을 기준으로 삼는다.

## 3. 지금까지의 작업

### 구현 완료로 확인되는 것

- 활성 프로젝트의 목표, 촬영 배치, 화면 구성, 예정 모듈 및 구현 순서를 문서화했다.
- `GAME_RULES.md` v0.11에 용어, 좌표계, 준비 조건, 문제 생성, 관측 데이터, 손-공 연결, 상태 전이, 점수, 시간, 입력 장애와 화면 표시 규칙을 구체화했다.
- `IMPLEMENTATION_CHECKLIST.md`에 카메라 없는 개발부터 Jetson 현장 검증과 발표까지의 단계별 완료 조건을 작성했다.
- `OPEN_DECISIONS.md`에 채택안, 근거, 미확인 사항과 현장 조정값을 분리해 기록했다.
- `portrait_ui_mockup.png`로 세로 화면 배치 예시를 만들었다. 실제 실행 화면이 아니다.
- 프로젝트 밖의 `2026.10.18/`에 단일 초록 공 검출, 직접 구현 Kalman 추적, MediaPipe 양손 랜드마크, 규칙 기반 손가락 수 실습 코드가 있다. 이는 재사용 참고 코드이지 통합 게임 구현이 아니다.

### 아직 구현되지 않은 것

- `[Project01]/`의 Python 모듈 전부
- 상태기계와 가짜 관측 테스트
- 3색 공 검출 및 색별 OpenCV Kalman 추적
- 물리적 왼손·오른손 보정 UI와 `hand_box`/`palm_box` 연결
- 단일 창 한글 UI, 폰트 파일, 카메라/저장 영상 입력 추상화
- Jetson 실행, 실제 FPS·지연·정확도 측정, 시연 결과
- 의존성 잠금 파일과 실행 가능한 프로젝트 명령

### 진행 중인 작업

코드 관점에서 진행 중인 구현은 없다. 다음 단계는 카메라 없이 `game.py`와 구조화된 관측 타입을 설계하고 테스트하는 것이다. 문서의 체크박스 `[x]`는 주로 **설계 또는 기록 완료**를 뜻하며 장비 동작 성공을 뜻하지 않는다.

## 4. 주요 의사결정

### 채택한 설계와 이유

| 결정 | 이유/의도 | 근거 |
| --- | --- | --- |
| 원본 640×480 프레임을 받은 직후 시계방향 90° 회전하고 이후 모든 좌표를 회전 영상 기준으로 처리 | 출발·제시·손 대기 영역을 세로 화면의 위→중앙→아래로 일관되게 배치 | [문서상 결정] |
| 물리적 왼손/오른손을 SETUP에서 한 손씩 들고 `Space`로 확인하여 보정 | 미러링·카메라 방향에 따라 MediaPipe 레이블 의미가 달라질 수 있음 | [문서상 결정] |
| 21점 전체의 `hand_box`는 1차 후보, 손목 및 5·9·13·17점의 `palm_box`는 최종 위치 기준 | 손가락 모양에 의존하지 않으면서 손바닥 부근 공을 근사 | [문서상 결정] |
| 손가락 펴짐/각도는 채점하지 않음 | 사용자가 손바닥을 약간 오므린 자연스러운 자세를 허용하고 공·손 연결 자체에 집중 | [문서상 결정] |
| 실제 검출 공만 준비·손 연결·채점에 사용 | Kalman 예측은 가림 후 실제 위치를 보장하지 않음 | [문서상 결정] |
| 빨강·초록·파랑마다 OpenCV `cv2.KalmanFilter` 하나를 사용 | 색별 상태 분리, `x,y,vx,vy` 상태와 실제 `dt`를 반영하고 OpenCV 구현을 사용 | [문서상 결정] |
| 카메라 없는 순수 게임 로직부터 구현 | Mac에서도 가짜 관측으로 상태 전이와 시간 규칙을 검증하고 하드웨어 의존성을 격리 | [문서상 결정] |
| 영상과 위·아래 정보 띠를 합쳐 `cv2.imshow()` 창 하나만 사용 | 기존 실습의 단일 창 흐름을 확장하고 하나의 게임 화면을 제공 | [문서상 결정] |
| 성공/오답은 0.4초 이상이면서 최소 4개 유효 프레임, 인접 유효 프레임 간격 0.15초 이하일 때 확정 | 순간 오검출·이동 중 장면에 의한 오판 완화 | [문서상 결정, 수치 현장 검증 필요] |
| 매 라운드 10초 고정, 시작 전 3초 카운트다운, 시작 기회 3개 | 첫 버전을 단순하고 설명 가능하게 유지 | [문서상 결정, 수치 현장 검증 필요] |
| 입력이 0.5초 이상 끊기거나 모델 예외가 나면 PAUSED, 현재 시도는 무효이고 점수·기회 유지 | 장비 장애를 사용자 오답으로 벌하지 않음 | [문서상 결정] |
| 직전 라운드와 완전히 같은 `(왼손 색, 오른손 색)` 조합은 피함 | 연속 반복을 줄이되 3색 순열 범위 안에서 단순하게 유지 | [문서상 결정] |
| 공 색당 한 개, 해당 색의 유효 후보가 정확히 하나일 때만 사용 | 첫 버전의 데이터 연결 모호성을 제한 | [문서상 결정] |

### 기각했거나 현재 범위에서 제외한 대안

- `2026.10.18/mp_hand.py`처럼 MediaPipe 레이블을 항상 반전하는 방식: 실제 손 보정으로 대체한다.
- 화면의 왼쪽/오른쪽 위치만으로 물리적 손을 정하는 방식: 손 교차·미러링에서 잘못될 수 있어 사용하지 않는다.
- `mp_hand_rulebased.py`의 160° 손가락 각도와 손가락 개수로 채점하는 방식: 현재 게임 판정에는 사용하지 않는다.
- `pingpong_kalman_filter.py`의 직접 작성한 2상태 필터를 그대로 이식하는 방식: 프로젝트에서는 색마다 OpenCV 4상태 `cv2.KalmanFilter`를 사용한다.
- 가려진 공의 예측 위치로 정답을 주는 방식: 화면 표시와 재연결 참고에만 사용한다.
- 손·공 누락이나 모호함을 즉시 오답으로 처리하는 방식: 판정을 보류하고 타이머만 계속 진행한다.
- 여러 OpenCV 창으로 카메라와 정보를 나누는 방식: 하나의 합성 화면을 사용한다.
- 같은 색 공 여러 개, 2인 플레이, 추가 손동작, 온라인 순위표: 첫 완성 범위에서 제외한다.
- 제한 시간이 점점 짧아지는 난도 조절: 실측 전에는 적용하지 않고 10초 고정으로 시작한다.

## 5. 미해결 문제와 제약

### 높은 우선순위

1. **실제 장비가 전혀 검증되지 않았다.** Jetson 정확한 모델, USB 카메라 장치와 형식, GStreamer/OpenCV 호환성, MediaPipe 실행, GUI, 실제 FPS와 지연이 모두 **확인 필요**다.
2. **세 공과 양손을 동시에 관측할 수 있는지 확인되지 않았다.** 제시 공 2개와 출발 영역의 남은 공 1개가 같은 채점 프레임에서 보여야 현재 규칙으로 정답을 낼 수 있다.
3. **색 임계값과 형태 필터가 없다.** 빨강·파랑 도색, 초록 공, 광택, 컵, 배경과 조명에 맞춰 LAB 범위·면적·원형도·크기를 현장에서 정해야 한다.
4. **손-공 2D 겹침은 실제 접촉 증거가 아니다.** `palm_box` 안 공 중심은 손바닥 부근이라는 근사일 뿐이다. 손 옆 탁자 공이 잘못 연결되는지 반드시 시험해야 한다.
5. **손을 오므렸을 때 공·손바닥 랜드마크·레이블이 동시에 보이는지 미확인**이다. 공이 가려지면 현재 규칙은 판정을 보류한다.
6. **Mac과 Jetson의 실행 경로가 다르다.** 기존 `v4l2src device=/dev/video0` 파이프라인은 Linux/Jetson 전용이며 macOS에서 그대로 동작하지 않는다. Mac에서는 우선 가짜 관측과 저장 영상 입력을 사용해야 한다.

### 구현 전에 결정할 정책

- `RESULT_SUCCESS`, `RESULT_WRONG`, `RESULT_TIMEOUT` 결과 화면의 표시 시간: **확인 필요**.
- `PAUSED`로 무효가 된 문제 뒤에 동일한 색 조합을 즉시 다시 허용할지: **확인 필요**.
- 테스트 프레임워크, Python 버전, 패키지 버전과 의존성 파일 형식: **확인 필요**.
- 프로젝트에 넣을 한글 폰트와 라이선스: **확인 필요**.
- 실제 영역 정규화 좌표, 색 임계값, 재연결 거리: **확인 필요**.

### 임시값이며 현장 조정이 필요한 항목

- `hand_box` 확장 15%, `palm_box` 여유 10%
- 손 레이블 분류 점수 0.70
- 정답·오답 0.4초 / 최소 4프레임 / 최대 프레임 간격 0.15초
- 공 예측 표시 0.5초, 입력 장애 0.5초
- 라운드 10초, 준비 유지 0.5초, 카운트다운 3초

느린 Jetson에서 처리 간격이 0.15초를 넘으면 정답/오답 연속 기록이 계속 초기화되어 성공 자체가 어려울 수 있다.

### 기존 참고 코드에서 확인된 주의점

- `2026.10.18/mp_hand.py`와 `mp_hand_rulebased.py`는 프레임을 실제로 좌우 반전하지 않으면서 handedness 레이블을 항상 반전한다. 새 게임에 그대로 복사하지 않는다.
- 위 두 파일의 모델 경로는 현재 작업 디렉터리에 의존하는 문자열 `src/models/MediaPipe/hand_landmarker.task`다. 새 구현은 파일 자체 위치를 기준으로 절대 해석하고 누락 오류를 명확히 내야 한다.
- `2026.10.18/pingpong_circle_overlay.py`는 가장 큰 초록 영역을 공으로 가정하므로 같은 색의 큰 물체에 취약하다.
- `2026.10.18/pingpong_kalman_filter.py`는 고정 시간 간격의 직접 구현 필터이며 색 하나만 다룬다. 새 추적기 요구사항과 다르다.
- `2026.10.17/assignment02.py`는 이미지 경로를 `../src/...`로 하드코딩했는데 해당 폴더 README는 저장소 루트 실행을 안내한다. 루트에서 실행하면 경로가 부모 디렉터리를 가리키므로 안내와 코드가 불일치한다. 활성 프로젝트 코드는 실행 위치 독립 경로를 사용해야 한다.
- 기존 카메라 스크립트에는 `cap.isOpened()`의 명시적 진단과 구조화된 오류 처리가 없다.

### 외부 요구사항

- 과제의 공식 평가 비중, 제출 형식, 마감, 시연 길이는 현재 저장소에서 확인되지 않았다. 문서의 평가 표는 공식 채점 기준이 아니라 준비 계획이다.
- “토요일 10시 강의실 점검”은 계획으로 기록되어 있으나 정확한 날짜와 장소 조건은 **확인 필요**다.

## 6. 다음 작업: 권장 우선순위와 순서

### P0 — Mac으로 옮긴 직후 상태 보존

1. `[Project01]/`, `HANDOFF.md`, `src/models/MediaPipe/`를 포함해 전체 폴더가 복사됐는지 확인한다.
2. `git status --short --branch`로 `[Project01]/`와 `HANDOFF.md`가 존재하는지 확인한다. Git만으로 이동했다면 미추적 파일이 빠졌을 가능성이 크다.
3. 새 Codex는 먼저 이 파일과 `[Project01]/README.md`, `documents/PROJECT_PLAN.md`, `documents/GAME_RULES.md`, `documents/OPEN_DECISIONS.md`를 읽는다.

### P1 — 하드웨어 없는 핵심 로직

1. 미결정 정책 2개(결과 화면 시간, PAUSED 후 동일 조합 허용)를 정하고 `GAME_RULES.md`에 반영한다.
2. `config.py`에 시간·영역·박스 확장·신뢰도 값을 모으되 임시값임을 표시한다.
3. 공·손·프레임 상태를 표현하는 구조화된 관측 타입을 정의한다. OpenCV 이미지 객체를 게임 로직에 넣지 않는다.
4. `game.py` 상태기계와 문제 생성, 단조 시계 기반 타이머, 점수·기회, 유효 프레임 연속 판정을 구현한다.
5. 가짜 관측 시퀀스로 정답, 색 반대, 남은 공 이탈/누락, 공 소유 모호, 시간 초과, 프레임 공백, PAUSED 복구를 자동 검증한다.

### P2 — 입력과 화면 골격

1. `camera.py`에 저장 영상과 카메라가 같은 형태로 프레임을 내는 인터페이스를 만든다.
2. Mac에서는 저장 영상 또는 합성 프레임으로 회전 좌표와 UI를 개발한다. 현재 Linux GStreamer 문자열을 macOS 경로로 억지 재사용하지 않는다.
3. 라이선스를 확인한 한글 폰트를 프로젝트에 추가하고 실행 위치 독립 경로로 읽는다.
4. `overlay.py`에서 세 영역, 문제, 시간, 점수, 기회, 상태를 하나의 합성 화면에 표시한다.

### P3 — 비전과 손 연결

1. 저장 영상 또는 현장 영상으로 3색 마스크, morphology, contour, 후보 유일성, 중심/크기를 구현한다.
2. CLAHE와 블러를 각각 설정으로 켜고 끄며 실제 효과를 비교한다. 사용하지 않은 처리를 사용했다고 문서화하지 않는다.
3. MediaPipe 모델 경로 확인, `HandLandmarker`, 물리적 손 보정, `hand_box`/`palm_box`, 모호성 처리를 구현한다.
4. 실제 검출만으로 준비·채점이 되는 통합 경로를 먼저 안정화한다.

### P4 — 추적과 통합

1. 색별 OpenCV `cv2.KalmanFilter`를 구현하고 실제 프레임 간 `dt`를 반영한다.
2. 실제 검출, 0.5초 이내 예측, `lost`, 재검출 재초기화 표시를 구분한다.
3. 예측값이 어떤 코드 경로에서도 점수·준비·손 연결로 들어가지 않는지 테스트한다.
4. 키 입력 `q` 종료, `r` 새 판과 입력 오류 메시지를 통합한다.

### P5 — Jetson 현장 검증과 제출

1. `IMPLEMENTATION_CHECKLIST.md` 단계 1과 단계 4를 실제 장비에서 순서대로 실행하고 예상/실제 결과를 기록한다.
2. FPS·지연과 실패 사례를 근거로 임시값을 조정한다. 규칙 변경은 `GAME_RULES.md`, 설정, README에 동시에 반영한다.
3. `requirements.txt` 또는 선택한 환경 명세에 실제 검증 버전을 고정한다.
4. `[Project01]/README.md`의 실행 명령, 파일 구조, 구현 기능, 한계와 AI 활용 내역을 실제 상태로 갱신한다.
5. 공식 과제 안내를 확보해 제출 형식과 평가 요구사항을 별도로 검증한다.

## 7. 개발 환경과 실행 방법

### MacBook에서의 권장 시작 환경

아래는 새 격리 환경을 만드는 일반적인 시작 명령이다. 프로젝트의 검증된 고정 버전 명령이 아니므로 설치 성공과 버전 호환성은 확인해야 한다.

```bash
cd '<프로젝트를 복사한 디렉터리>/Vision-LLM-202237752'
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install numpy opencv-python mediapipe pillow matplotlib
```

- `matplotlib`은 `2026.10.17/assignment02.py`에 필요하지만 새 게임 런타임에는 현재 계획상 필수가 아니다.
- macOS의 일반 `opencv-python`이 Jetson용 GStreamer 동작을 재현한다고 가정하지 않는다.
- 새 게임에는 아직 실행할 `main.py`가 없다. 구현 후 예상 명령은 `python '[Project01]/main.py'`지만, 실제 진입점이 생기기 전까지 확정 명령이 아니다.
- 폴더 이름에 대괄호가 있으므로 셸에서 경로를 작은따옴표로 감싸는 편이 안전하다.

### 현재 존재하는 실습 실행 명령

```bash
python 2026.10.17/assignment02.py
python 2026.10.18/pingpong_circle_overlay.py
python 2026.10.18/pingpong_kalman_filter.py
python 2026.10.18/mp_hand.py
python 2026.10.18/mp_hand_rulebased.py
```

이 명령들은 해당 README의 안내를 옮긴 것이다. `2026.10.18/` 네 파일은 `/dev/video0`과 `v4l2src`를 사용하므로 macOS에서는 그대로 실행되지 않는다. `assignment02.py`의 상대 이미지 경로도 앞서 적은 불일치가 있다.

### Jetson 카메라와 시스템 의존성

기존 실습이 요청하는 첫 시험 파이프라인은 다음과 같다. 실제 장치가 이 형식을 지원하는지는 **확인 필요**다.

```text
v4l2src device=/dev/video0 !
video/x-raw,format=YUY2,width=640,height=480,framerate=30/1 !
videoconvert ! video/x-raw,format=BGR !
queue leaky=downstream max-size-buffers=1 max-size-bytes=0 max-size-time=0 !
appsink drop=true max-buffers=1 sync=false
```

Jetson에서는 다음이 필요하다.

- 접근 가능한 USB 카메라 장치
- GStreamer 및 필요한 플러그인
- GStreamer 지원이 포함된 OpenCV 빌드
- 화면을 열 수 있는 GUI 환경
- NumPy, MediaPipe, Pillow
- `src/models/MediaPipe/hand_landmarker.task`
- 프로젝트가 선택한 한글 폰트

OpenCV의 GStreamer 지원 여부는 다음처럼 빌드 정보를 확인한다.

```bash
python3 -c "import cv2; print(cv2.getBuildInformation())"
```

### MediaPipe 외부 모델 설정

현재 저장소에는 `src/models/MediaPipe/.gitkeep`만 있고 `.task` 모델은 없다. 문서에는 사용자가 Jetson에서 다음 명령으로 모델을 받았다고 보고한 것으로 기록돼 있다. **현재 Windows 환경에서는 Jetson 파일 존재, 크기, 로딩, 추론을 검증하지 못했다.**

```bash
mkdir -p src/models/MediaPipe
python3 -m pip install --no-deps mediapipe
python3 -m pip install absl-py flatbuffers sounddevice
wget https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/latest/hand_landmarker.task -O src/models/MediaPipe/hand_landmarker.task
wget https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_full/float16/latest/pose_landmarker_full.task -O src/models/MediaPipe/pose_landmarker_full.task
```

현재 게임에는 손 모델만 필요하며 pose 모델은 사용 범위가 아니다. 설치 명령은 수업 자료/프로젝트 문서의 기록이고, Mac 또는 Jetson의 실제 Python 버전과 wheel 호환성은 별도로 확인한다.

### 환경변수와 외부 서비스

- 필수 환경변수: **없음/문서화되지 않음**.
- API 키, 토큰, 클라우드 서비스: **사용하지 않음/문서화되지 않음**.
- 설정은 환경변수 대신 예정된 `[Project01]/config.py`에 둘 계획이다.
- 외부 네트워크는 MediaPipe 모델과 Python 패키지를 내려받을 때만 필요하다.
- 민감정보는 이 문서에 포함하지 않았으며 새 문서에도 넣지 않는다.

## 8. 반드시 지킬 주의사항과 불변 조건

1. **문서 완료를 구현 완료로 표시하지 않는다.** 실제 코드, 테스트, Jetson 시연 증거가 생긴 뒤에만 완료 상태를 바꾼다.
2. **Kalman 예측으로 채점하지 않는다.** 준비 확인, 손-공 연결, 남은 공 확인, 정답/오답은 모두 현재 프레임의 실제 검출만 사용한다.
3. **좌표계는 회전 후 영상 기준으로 통일한다.** 프레임 수신 직후 90° 시계방향 회전하고 공·손·영역 판정을 모두 같은 좌표계에서 한다.
4. **물리적 왼손·오른손을 채점한다.** 화면의 좌우나 무조건적인 MediaPipe 레이블 반전에 의존하지 않고 세션 보정을 거친다.
5. **손가락 개수와 관절 각도를 채점에 넣지 않는다.** `mp_hand_rulebased.py`는 학습 참고일 뿐 게임 규칙이 아니다.
6. **`hand_box`와 `palm_box`를 독립된 접촉 증거처럼 설명하지 않는다.** 작은 상자는 큰 상자 안에 있고 둘 다 2D 위치 근사다.
7. **누락·가림·모호함을 즉시 오답으로 만들지 않는다.** `GAME_RULES.md`의 완성된 제시 자세와 연속 조건이 있어야 오답을 확정한다.
8. **게임 로직과 하드웨어를 분리한다.** `game.py`는 프레임·OpenCV 카메라에 직접 의존하지 않고 구조화된 관측과 단조 시각을 입력받는다.
9. **현장 수치를 상수 진리로 취급하지 않는다.** 임시값을 설정에 모으고 실측 근거와 함께 바꾼다.
10. **규칙 변경을 한 파일에만 반영하지 않는다.** `GAME_RULES.md`, `PROJECT_PLAN.md` 또는 `OPEN_DECISIONS.md`, 설정, README와 테스트가 서로 일치해야 한다.
11. **사용하지 않은 수업 기술을 사용했다고 주장하지 않는다.** CLAHE·블러 등은 실제 최종 실행 경로와 시연 증거가 있을 때만 구현 항목으로 기록한다.
12. **모델·폰트·비밀값을 무심코 Git에 넣지 않는다.** 모델과 폰트는 크기·라이선스·배포 정책을 확인하고, 비밀번호·API 키·토큰은 어떤 Markdown에도 기록하지 않는다.
13. **Git 상태를 먼저 확인한다.** `[Project01]/`와 이 파일은 현재 미추적이므로 사용자 변경을 보존하고, 임의로 삭제·초기화하지 않는다.

## 9. 참고 문서와 관련 코드

### 가장 먼저 읽을 문서

- `[Project01]/README.md` — 제출용 README 초안, 현재 단계와 문서 안내
- `[Project01]/documents/PROJECT_PLAN.md` — 목표, 범위, 촬영 배치, 화면, 구현 순서와 예정 모듈
- `[Project01]/documents/GAME_RULES.md` — 구현의 최우선 규칙 명세 v0.11
- `[Project01]/documents/OPEN_DECISIONS.md` — 채택안, 사용자 보고, 미확인 사항과 남은 정책
- `[Project01]/documents/IMPLEMENTATION_CHECKLIST.md` — 구현 및 현장 검증 순서와 시나리오
- `[Project01]/documents/portrait_ui_mockup.png` — 실제 실행 화면이 아닌 세로형 UI 배치 목업

### 재사용 후보 및 기술 참고 코드

- `2026.10.18/README.md` — 실시간 카메라·공 추적·MediaPipe 실습의 환경과 한계
- `2026.10.18/pingpong_circle_overlay.py` — 단일 초록 공 LAB 분할과 contour 오버레이
- `2026.10.18/pingpong_kalman_filter.py` — 직접 구현한 단일 공 Kalman 실습; 프로젝트에 그대로 이식하지 않음
- `2026.10.18/mp_hand.py` — MediaPipe 두 손 랜드마크와 단일 창 표시 참고
- `2026.10.18/mp_hand_rulebased.py` — 손가락 각도 실습; 게임 채점에는 사용하지 않음
- `2026.10.17/assignment02.py` — LAB, CLAHE, morphology, contour의 정적 이미지 예시
- `2026.10.17/README.md` — 위 과제 설명. 실행 경로 안내와 코드 사이 불일치 주의
- `02_Computer-Vision.ipynb` — Section Project 요구와 컴퓨터 비전 수업 원자료. 특히 Color Segmentation, Kalman Filter, MediaPipe, Section Project 셀 참고

### 저장소 보조 경로

- `src/images/` — 수업 이미지. 실제 게임 정확도 검증 데이터가 아님
- `src/models/MediaPipe/` — 모델 예정 위치. 현재 `.gitkeep`만 존재
- `src/datasets/calibration/` — 향후 보정 데이터 위치로 보이나 사용 방식은 **확인 필요**
- `src/output/` — 향후 출력 위치로 보이나 사용 방식은 **확인 필요**

## 10. 새 Codex가 첫 응답 전에 확인할 체크리스트

1. `git status --short --branch`와 `rg --files`로 이 문서의 상태 설명이 복사 후에도 맞는지 확인한다.
2. `[Project01]/documents/GAME_RULES.md`와 `OPEN_DECISIONS.md`를 읽고 최신 버전·미결정 정책을 확인한다.
3. 사용자의 요청이 “Mac에서 하드웨어 없이 구현”인지 “Jetson에서 현장 통합”인지 구분한다.
4. 코드 작성 전, 결과 화면 시간과 PAUSED 후 문제 재사용 정책을 사용자에게 확인하거나 명시적인 기본안을 제안한다.
5. 새로 검증한 사실, 추정, 사용자 보고를 계속 구분한다. 장비에서 실행하지 않았다면 실행 성공을 주장하지 않는다.
