# 구현 및 검증 체크리스트

상태: 게임 연결·한글 화면·저장 영상·기본 OFF 추적 코드 추가 · 2026-10-23. 실제 수행한 항목만 완료로 표시한다. 2026-10-24 Jetson에서 실제 카메라·OpenCV·MediaPipe·영역 화면까지 확인했으며, 저장 영상·Kalman과 전체 게임 라운드는 아직 미검증이다.

## Jetson 현장 영역 설정 (2026-10-24)

- 카운트다운이 시작되지 않는 현상을 재현했다. 화면은 `준비 완료`였지만 `READY`에 머물렀고, 손+공 처리 12회의 프레임당 시간을 측정한 결과 최소 0.1779초, 중앙값 0.2205초, 최대 0.3239초로 모두 기존 0.15초 허용 간격을 넘었다.
- 사용자 승인으로 준비·정답/오답 연속 프레임의 최대 간격 `MAX_READY_GAP`을 0.35초로 변경했다. 0.22초 간격 프레임이 0.5초 준비 뒤 `COUNTDOWN`에 들어가는 RED→GREEN 테스트를 추가하고 기존 경계 테스트를 0.35/0.350001초로 갱신했다. Jetson 전체 unittest 107개 통과.
- 고정된 480×640 회전 카메라 화면에서 공 3개가 상단에 있고 양손 손바닥 중심이 하단에 들어오는 장면을 확인했다. MediaPipe 표시에서 화면 왼쪽 손은 `left 1.00`, 오른쪽 손은 `right 0.99`였다.
- `REGIONS`를 `start=(0.02, 0.00, 0.98, 0.30)`, `presentation=(0.02, 0.31, 0.98, 0.62)`, `waiting=(0.02, 0.63, 0.98, 1.00)`으로 설정했다. 세 영역은 겹치지 않으며 정보 띠를 제외한 카메라 영상 좌표다.
- Jetson에서 전체 unittest 106개가 통과했다. 수정 코드를 재실행해 영역 경계와 한글 이름이 한 창에 표시되고, `SETUP`에서 `READY`로 자동 전환되는 것을 확인했다. 캡처 시 손 하나가 프레임 밖에 있어 `다른 손을 보여주세요` 안내가 표시되는 것도 확인했다.
- 실제 양손 대기 유지 0.5초, 카운트다운, 공 이동에 따른 문제 제출·정답/오답 판정은 다음 현장 시험에서 계속 확인한다.

## 현재 하네스 검증 기록

### 손 모델 경로 사전 검사 제거 (2026-10-24)

- 사용자 결정에 따라 Jetson의 손 모델 파일 존재를 전제로 한다. `vision.py`의 `Path` import와 `is_file()` 사전 검사를 제거하고, `HAND_MODEL_PATH` 문자열을 `python.BaseOptions(model_asset_path=...)`에 바로 전달한다.
- TDD RED: 존재하지 않는 `"model.task"`도 MediaPipe 준비 함수에 바로 전달되어야 한다는 테스트가 기존 사전 검사에서 실패하는 것을 확인했다. 최소 변경 후 경로 문자열, `num_hands=2`, 생성 옵션과 반환 검출기가 그대로 이어지는 테스트가 통과했다.
- 아래의 `Path` import 복원과 모델 누락 테스트 기록은 당시 검토 이력이며 이번 사용자 결정으로 대체한다. 실제 Jetson 모델 로딩·추론 성공은 아직 검증하지 않았다.
- 최종 재검증: 순수 테스트 87개와 입력 재생·문법 검사·`git diff --check`는 exit 0. 전체 discovery는 89개 중 87개 통과와 Mac `.venv`의 `cv2` 부재 import 오류 2개로 exit 1이다. 독립 재검토의 README 테스트 설명 1건을 수정했으며 남은 Critical/Important 지적은 없다.

### 색별 가장 큰 외곽선 선택 (2026-10-24)

- 사용자 결정으로 실제 공 검출을 `pingpong_circle_overlay.py`와 같은 흐름으로 단순화했다. 각 색의 마스크에서 면적이 가장 큰 외곽선 하나를 고르며 최소 면적 필터는 두지 않는다. 외곽선이 없을 때만 해당 색을 미검출로 처리한다.
- 첫 TDD RED에서는 면적 150·99·240인 같은 색 외곽선을 전달했을 때 기존 구현이 150과 240을 모두 반환하여, 240 하나만 기대한 테스트가 실패했다. 이후 최소 면적도 제거한다는 사용자 결정에 맞춰 면적 50·99·80 중 99 하나를 기대하도록 바꿨고, 기존 함수가 `min_area` 인자를 요구하여 실패하는 것을 확인한 뒤 해당 인자와 필터를 제거했다.
- 이 결정은 2026-10-23의 "색별 모든 유효 후보 보존" 결정을 대체한다. 다만 가짜 `Frame`과 순수 게임 판정은 누락·복수 후보를 계속 받을 수 있으므로 해당 경계 테스트는 유지한다.
- 외부 비전 모듈을 메모리에서 빈 모듈로만 제공한 한정 실행으로 `BallObservationTests.test_only_largest_same_color_candidate_is_kept`를 실행했다. 실제 `make_ball_candidates()`를 사용해 면적 50·99·80 중 99 하나가 선택되는 테스트 1개가 통과했다. 이는 OpenCV 색 변환·외곽선 검출 실행 결과가 아니다.
- `.venv/bin/python -m unittest tests.test_game tests.test_contracts tests.test_support -v` — 순수 테스트 87개 통과, exit 0. `.venv/bin/python -m tests.support` — 가짜 입력 재생 완료, exit 0.
- `.venv/bin/python -m py_compile contracts.py game.py main.py vision.py tests/test_game.py tests/test_main.py tests/test_vision.py` — 문법 검사 통과, exit 0.
- `.venv/bin/python -m unittest discover -s tests -t . -v` — 89개 집계: 87개 통과, `tests.test_main`·`tests.test_vision`은 `cv2` 부재로 import 오류 2개, exit 1. 전체 통과가 아니다.
- 저장소 루트 `git diff --check` — 출력 없음, exit 0. 실제 OpenCV·MediaPipe·카메라·저장 영상 실행과 현장 마스크 확인은 하지 않았다.
- 독립 읽기 전용 검토에서 가장 큰 외곽선 흐름 자체의 Critical/Important 문제는 없었다. 다만 같은 `vision.py`의 `create_hand_detector()`가 `Path`를 import하지 않아 실제 시작 시 `NameError`가 나는 기존 Critical 문제를 발견했다. 빈 외부 모듈을 제공한 한정 실행에서 기존 `test_missing_hand_model_is_reported_before_loading_mediapipe`가 `NameError`로 실패하는 것을 재현한 뒤 `from pathlib import Path`를 복원했고, 같은 테스트가 통과했다. 계획 문서의 형태·크기 필터 추가 가능 문구도 이번 확정 규칙에 맞춰 색 범위·모폴로지 조정으로 고쳤다.
- 리뷰 수정 후 최종 재검증: 순수 테스트 87개와 입력 재생·문법 검사·`git diff --check`는 모두 exit 0. 한정 비전 테스트는 가장 큰 외곽선 선택과 모델 파일 누락 처리 2개가 통과했다. 전체 discovery는 89개 중 87개 통과와 `cv2` 부재 import 오류 2개로 exit 1이며, 실제 비전 실행으로 간주하지 않는다.
- 같은 독립 검토자가 수정 내용을 다시 확인했으며 남은 Critical/Important 지적은 없다. 실제 `test_vision` 전체 실행은 OpenCV 미설치 한계로 여전히 현장 검증 대상이다.

### 별도 설정 확인 제거 (2026-10-24)

- 사용자 결정에 따라 `SETUP_CONFIRMED`와 `setup_complete` 인자를 제거했다. 현장에서 `REGIONS`와 `HAND_MAPPING` 값을 코드에 맞춘 뒤 실행하면, 설정된 영역과 첫 정상 프레임을 받은 `update_game()`이 자동으로 `READY`로 이동한다.
- `r` 재시작은 점수·기회·기록을 초기화하고, 다음 정상 프레임에서 같은 설정 영역으로 자동 준비한다. SETUP 화면에는 개발자용 설정 지시를 표시하지 않는다.
- TDD RED: 자동 READY 테스트는 `SETUP`에 머물러 실패했고, 인자 없는 `restart_game(state)` 테스트는 `TypeError`로 실패했다. 구현 뒤 두 테스트와 순수 전체 테스트를 재실행한다.
- `.venv/bin/python -m unittest tests.test_game tests.test_contracts tests.test_support -v` — 87개 통과, exit 0.
- `.venv/bin/python -m unittest discover -s tests -t . -v` — 89개 집계: 87개 통과, `tests.test_main`·`tests.test_vision`은 기존과 같이 cv2 부재로 import 오류 2개, exit 1. 전체 통과가 아니다.
- `.venv/bin/python -m tests.support` — 가짜 입력 재생 완료, exit 0.
- `.venv/bin/python -m py_compile contracts.py game.py main.py vision.py tests/test_game.py tests/test_main.py tests/test_vision.py` — 문법 검사 통과, exit 0.
- 저장소 루트 `git diff --check` — 출력 없음, exit 0. 새 의존성 설치 없음.

### 전체 검토 후 중복·안내·문서 정리 (2026-10-24)

- 사용자 요청으로 같은 프레임의 중복 판정을 제거했다. `update_game`에서 만든 결과를 준비·채점 함수에 전달하고, 단독 호출에서만 해당 함수가 판정한다.
- 프레임 번호 기록을 딕셔너리로 바꿔 반복적인 목록 전체 검색을 줄였다. 라운드별/판별 수명과 비인접 중복 차단은 유지한다. 기록 자체는 누적되며 새 판에서 초기화된다. 중복된 마지막 번호 상태는 제거했다.
- 테스트에만 사용하던 `read_failed`/`has_read_failure`, 사용되지 않는 예측 Ball 반환 목록, 모폴로지 함수의 cv2 인자를 제거했다. 추적은 입력 Ball을 수정하지 않고 별도 추적 상태만 갱신한다.
- 남은 공 위치 안내, 준비 중 관측 사유, 기회 수/아이콘과 상태 표시를 추가했다. 완성 자세·시간·점수 규칙은 유지한다. 주석 오류와 폰트·한글 화면·저장 영상·필터·overlay 관련 문서 불일치를 정리했다.
- TDD RED: `.venv/bin/python -m unittest tests.test_game.ScreenTextTests -q` — 새 테스트 2개에서 안내 누락으로 4개 실패(하나는 3개 subTest). 수정 후 순수 테스트 전체 86개 통과.
- `.venv/bin/python -m unittest tests.test_game tests.test_contracts tests.test_support -q` — 86개 통과, exit 0.
- `.venv/bin/python -m unittest discover -s tests -t . -q` — 88개 집계: 86개 통과, `tests.test_main`·`tests.test_vision`은 cv2 부재로 import 오류 2개, exit 1. 전체 통과가 아니다.
- `.venv/bin/python -m tests.support` — 정상 관측·손 누락·읽기 실패·모델 오류·EOF 재생 완료, exit 0.
- `.venv/bin/python -m py_compile game.py main.py vision.py tests/test_game.py tests/test_main.py tests/test_vision.py` — 문법 검사 통과, exit 0.
- `.venv/bin/python -` 제한 진단: 실제 `inspect_frame`을 감싼 호출 계측에서 READY/ACTIVE 새 프레임 각각 1회 확인. `main.py`의 CameraReader 클래스 정의만 AST로 추출해 실제 threading/time으로 기존 카메라 전달 테스트 4개 통과. main 모듈 전체 import·실제 카메라 검증을 대신하지 않는다.
- 저장소 루트 `git diff --check` — 출력 없음, exit 0.
- 모폴로지 테스트는 주입한 가짜 연산 대신 실제 OpenCV 마스크의 점 잡음·구멍 처리를 검사하도록 변경했다. 실제 Kalman 테스트도 반환 목록 대신 추적 상태·입력 불변성을 확인한다. 둘 다 cv2 부재로 이번 환경에서 실행하지 못했으며 통과로 표시하지 않는다. 새 의존성 설치 없음. Jetson의 화면 높이·기호 표시·실제 검출은 미검증이다.
- 독립 검토에서 RESET→READY 시 이전 문제의 제시 안내가 남는 문제를 발견했다. 해당 전환 테스트의 실패를 확인한 뒤 ACTIVE에서만 문제를 판정에 전달하도록 수정했다. 상태 전이 시점·채점은 유지하고 판정을 반복하지 않는다.
- 검토 수정 후 최종 재실행: 순수 테스트 명령은 **87개 통과**, exit 0. 전체 discover는 **89개 집계(87개 통과·동일한 cv2 import 오류 2개)**, exit 1. 새로운 비전 실행 성공을 주장하지 않는다.

### 남은 구현 — 8·9·10단계 코드 (2026-10-23)

- 사용자 요청으로 남은 연결·한글 화면·저장 영상 입력·선택형 추적을 추가했다. 추가 답변으로 Noto Sans KR+SIL OFL 포함과 추적 기본 OFF를 확정했다. 영역·좌우·재연결 거리는 현장 설정을 요구한다. 모델 작업은 기존 승인대로 메인에 두며 실제 추론 중단 대응은 미검증이다.
- 적용: brainstorming으로 기존 결정과 미결정을 대조하고, writing-plans로 기존 계획에 구체화했다. executing-plans로 직접 구현하며 TDD·verification-before-completion·단계별 requesting-code-review를 적용했다. 기존 작업 공간·기존 체크리스트를 사용하고 커밋·별도 worktree는 만들지 않았다.
- 8단계 RED: `.venv/bin/python -m unittest tests.test_game.GameConnectionTests -v`에서 `update_game` 미구현 AttributeError 3개. 구현 후 3개 통과. 준비→문제 제출→정답·한 번의 점수 반영, 입력 오류·복구, 영역 미설정 SETUP 유지를 검증했다.
- 실제 연결: `main.py`가 새 Frame을 `game.update_game`에 전달한다. 읽기 실패는 한 번 발생해도 소비 전까지 보존하고 채점 전에 다시 확인한다. 관측 예외는 model_error로 전달한다. 새 프레임이 없어도 결과·장애·화면·키를 갱신한다. 문제 화면 imshow 호출 직전 단조 시각을 시작 시각으로 전달한다. r은 새 판, q는 종료다.
- 9단계 RED: `ScreenTextTests` 3개에서 `get_screen_lines` 미구현 AttributeError. 구현 후 통과. 문제의 물리적 좌우·색, 남은 시간, 결과·장애 사유, 성공 없는 요약을 확인했다. 당시 실물 좌표 없는 임의 구역을 확정하지 않고 `REGIONS=None`, `SETUP_CONFIRMED=False`로 유지했으며, `SETUP_CONFIRMED`는 2026-10-24 결정으로 제거했다.
- 폰트: Google Fonts 원본 `https://raw.githubusercontent.com/google/fonts/main/ofl/notosanskr/NotoSansKR%5Bwght%5D.ttf`에서 폰트를 받았고 OFL 원문을 함께 포함했다. SHA-256은 README에 기록했다. 패키지를 설치한 것은 아니다. 웹 열기는 제한 오류가 있었으며 실제 파일 확보는 curl로 성공했다.
- 화면 보조 확인: 앱 번들 Python/Pillow 12.3.0·NumPy에서 실제 `make_text_band` 함수를 AST로 추출해 Noto 한글 5상태의 띠를 렌더링했다. 480px 너비·RGB 3채널을 확인하고 생성 PNG를 직접 열어 줄바꿈·한글을 확인했다. Regular(400) 설정도 해당 환경에서 확인했다. 이는 프로젝트 .venv·OpenCV 합성·Jetson GUI 실행 결과가 아니다.
- 저장 영상 RED: 실제 `CameraReader` 클래스만 AST로 추출한 제한 실행에서 is_video 인자 미구현 TypeError를 확인했다. 구현 후 EOF와 카메라 장애 구분·해제 테스트가 통과했다. 첫 실패 후 정상 입력이 와도 실패 신호를 보존하는 테스트는 기존 구현에서 이미 통과했으므로 RED로 세지 않는다. 원본 FPS 간격·최신 프레임 방식이며 느린 처리에서는 프레임을 건너뛸 수 있다. 고정 문제 리스트는 완료 시도 순서로 반복하며 실제 게임 영상 대조는 하지 못했다.
- 10단계 RED: `TrackingDecisionTests` 3개를 제한 실행해 `choose_tracking_action` 미구현 AttributeError를 확인했다. 구현 후 0.5초 경계·복수 후보·유일 후보·먼 재등장·lost 재초기화 판단이 통과했다. 실제 cv2.KalmanFilter는 실행하지 못했다. 실제 필터용 `KalmanTrackingTests`를 추가했으며 로컬 실행 통과로 표시하지 않는다. 예측 Ball은 채점 Frame에 넣지 않는다.
- 독립 검토: 8단계에서 확정 P1/P2 없음. 9·10단계에서 프레임 사이마다 피드백이 사라지는 P2 1건. 회귀 테스트가 오래된 피드백을 계속 표시해 실패하는 RED를 확인한 뒤, 0.15초까지 유지하고 이후 관측 갱신 대기로 표시해 GREEN을 확인했다. 그 밖에 확정 P1/P2 없음. 모델 메인 처리·실장비 검증 한계는 명시했다.
- 최종 프로젝트 `.venv/bin/python --version`: Python 3.10.12. `.venv/bin/python -m unittest tests.test_contracts tests.test_support tests.test_game -q`: **84개 통과**, 종료 코드 0. `.venv/bin/python -m tests.support`: 기존 입력 순서 뒤 재생 종료, 종료 코드 0.
- `.venv/bin/python -m py_compile contracts.py game.py main.py vision.py tests/test_game.py tests/test_main.py tests/test_vision.py`: 성공. 기본 `.venv/bin/python -m unittest discover -s tests -t . -v`: **84개 통과 + cv2 부재로 test_main/test_vision import 오류 2건**, 종료 코드 1. 전체 통과로 보고하지 않는다.
- 비전 의존성 없는 한정 확인: `.venv/bin/python - <<'PY'`에서 실제 vision.py의 상수·함수와 CameraReader를 AST로 읽어 표준 라이브러리·contracts만 제공하고 HandObservationTests·BallObservationTests·TrackingDecisionTests·CameraReaderTests를 실행했다. **14개 통과**. 실제 비전 함수·필터를 가짜 구현으로 대체하지 않았고, 이 결과를 실제 OpenCV·MediaPipe·기본 discover 통과로 세지 않는다.
- 저장소 루트 `git diff --check`: 통과. 기존 사용자 변경과 루트 HANDOFF 삭제를 보존했다. 의존성 설치·commit·push·다른 수업 코드 변경은 하지 않았다.

현장에 남은 필수 확인: Jetson Python·기존 패키지 버전과 GStreamer, 손 모델 경로·로딩, 영역과 물리적 좌우, LAB/면적/모폴로지·전처리, 저장 영상별 검출 사유 대조, 한글 최종 창과 문제 제출 시각·키, 실제 Kalman·재연결 거리, 여러 라운드·가림·오답·시간 초과·카메라 중단·종료, FPS·인식 정확도. 이 항목은 완료 처리하지 않았다.

### 리뷰 3·4·5번 수정 — 2026-10-23

- 3번: `CameraReader.read_frames`의 `finally`에서 카메라를 해제한다. 메인 종료 경로의 중복 `cap.release()`를 제거했다. 읽기 지연 중 `stop()`이 반환해도 읽기가 끝나기 전에는 해제하지 않는다. 열린 카메라의 읽기·해제는 같은 스레드가 맡는다. `stop()`의 1초 대기는 유지하며 영구 중단된 읽기를 강제로 취소하지는 않는다.
- 4번: 정상 입력 번호를 `input_frame_ids`에 따로 보관한다. 라운드 초기화·장애 후에도 유지하고 새 판에서 초기화한다. `1 → 2 → PAUSED → 과거 1`은 복구하지 않고 새 `3`에서만 복구한다.
- 5번: HARNESS_DESIGN의 외부 패키지 import 문장은 앞선 손 등록 제거 작업에서 이미 상단 import로 고쳐져 있음을 확인했다. 이번에는 카메라 해제 주체와 입력 번호 이력 수명도 문서에 반영했다.
- TDD RED: `.venv/bin/python -m unittest tests.test_game.InputFailureTests.test_earlier_duplicate_cannot_recover_after_active_pause -v`가 `READY != PAUSED`로 실패했다. 카메라 지연 종료 테스트는 해제 횟수 `0 != 1`로 실패했다. 카메라 검사는 `.venv/bin/python - <<'PY'`에서 AST로 실제 `CameraReader` 클래스만 추출하고 표준 `threading`·`time`과 함께 실행한 뒤 `tests.test_main.CameraReaderTests`를 실행했다. 외부 비전 모듈을 가짜로 구현하거나 실제 비전 실행으로 주장하지 않는다.
- GREEN: 수정 후 `InputFailureTests` 14개 통과. 같은 AST 한정 실행으로 CameraReader 테스트 2개 통과(지연 중 미해제, 읽기 종료 뒤 한 번 해제, 기존 최신 프레임 복사 확인).
- 최종 `.venv/bin/python --version`: Python 3.10.12. `.venv/bin/python -m unittest tests.test_contracts tests.test_support tests.test_game -q`: 77개 통과·종료 코드 0. `.venv/bin/python -m tests.support`: 재생 종료·종료 코드 0.
- `.venv/bin/python -m py_compile contracts.py game.py main.py vision.py tests/test_main.py tests/test_game.py`: 성공. 기본 `.venv/bin/python -m unittest discover -s tests -t . -v`: 77개 통과 외에 `tests.test_main`·`tests.test_vision`에서 `cv2` 부재 import 오류 두 건, 종료 코드 1. 실제 비전·Jetson 실행은 미검증이다.
- 읽기 전용 독립 검토: 3·4·5번 범위에서 추가 결함 없음. 검토자가 `tests.test_game` 67개를 별도 실행해 통과했다. 저장소 루트 `git diff --check`: 통과. 설치·commit·push는 하지 않았다. 기존 변경과 HANDOFF 삭제를 보존했다.

### 실행 중 손 등록 제거 — 2026-10-23

- 사용자 결정으로 Space 확인·양손 순차 등록·0.5초 안정 관측 함수와 변수·화면 안내를 제거했다. 삭제된 기능의 테스트 세 개도 제거했다. 기본 `HAND_MAPPING`은 `Left→left`, `Right→right`이며 실제 방향을 확인한 값은 아니다. 현장에서 실제 양손을 보고 값만 수정한다.
- GAME_RULES의 매핑·SETUP 기준, README, 설계·계획·결정·작업 안내를 현재 방식에 맞췄다. 아래 과거 Space 보정 구현·검증 기록은 당시 이력이다.
- `.venv/bin/python -m unittest tests.test_contracts tests.test_support tests.test_game -q`: 76개 통과, 종료 코드 0. `.venv/bin/python -m tests.support`: 재생 종료, 종료 코드 0.
- `.venv/bin/python -m py_compile main.py vision.py tests/test_main.py`: 성공. 전체 discover는 76개 통과와 별도로 `cv2` 부재에 따른 test_main/test_vision import 오류 두 건, 종료 코드 1. 실제 비전 실행이나 삭제 후 비전 테스트 통과로 보고하지 않는다.
- 저장소 루트 `git diff --check`: 통과. 실제 카메라·모델·Jetson 검증과 의존성 설치는 하지 않았다. 앞선 리뷰의 카메라 종료 순서·과거 중복 프레임 문제는 이번 변경 범위에 포함하지 않았다.

### 6·7단계 이후 import 위치 정리 — 2026-10-23

- 사용자 요청으로 `vision.py`의 OpenCV·MediaPipe·NumPy import와 `main.py`의 OpenCV import를 파일 상단으로 옮겼다. 함수 내부 import는 제거했다.
- `.venv/bin/python -m py_compile vision.py main.py`: 성공. 전체 unittest는 기존 76개가 통과했으나 `tests.test_main`·`tests.test_vision` 로딩에서 `ModuleNotFoundError: No module named 'cv2'` 두 건이 발생했다. 이전 87개 통과는 위치 변경 전 기록이다.
- `.venv/bin/python -m tests.support`: 정상 재생 종료. 저장소 루트 `git diff --check`: 통과. 의존성 설치·테스트 skip·가짜 모듈 추가는 하지 않았다.

사용자 요청으로 이전 A–D의 엄격한 구조를 일반 클래스·함수 중심으로 대체했다. 현재 설계는 [HARNESS_DESIGN.md](HARNESS_DESIGN.md), 변경 순서와 완료 조건은 [HARNESS_IMPLEMENTATION_PLAN.md](HARNESS_IMPLEMENTATION_PLAN.md)를 따른다.

- [x] Python 3.10.12 arm64 프로젝트 `.venv` 준비. pyenv로 정확한 버전을 설치했고 전역 Python·셸 시작 설정은 바꾸지 않았다. 외부 Python 패키지는 설치하지 않았다.
- [x] `contracts.py`를 일반 `Ball`·`Hand`·`Frame` 클래스로 변경. 자료형 검사·데코레이터·Protocol·전용 시계 클래스 제거.
- [x] 입력을 딕셔너리 목록, 문제를 튜플, 시각을 초 단위 숫자로 변경. 도우미는 `get_event`·`pick_question` 두 함수만 유지.
- [x] 변경된 사용법의 테스트를 먼저 실행했을 때 기존 코드에 `Ball`·`Frame`이 없어 import 실패함을 확인(RED).
- [x] 변경 후 저장소 루트에서 `'[Project01]/.venv/bin/python' -m unittest discover -s '[Project01]/tests' -t '[Project01]' -v`: **8개 통과, 0 skipped** (2026-10-22, Mac arm64, Python 3.10.12).
- [x] 변경 후 저장소 루트 `git diff --check`: 출력 없음·종료 코드 0. GAME_RULES는 이번 단순화 전 스냅샷과 일치하며 기존 HANDOFF 삭제를 보존했다.
- [x] 프로젝트에서 `.venv/bin/python -I -S`로 프로젝트 경로를 추가한 뒤 데이터 클래스·도우미 import 성공. 외부 패키지를 로딩하지 않았다.

당시 테스트 범위: 공 정보 저장·수정, 손 정보 저장, 누락·복수/예측 후보 전달, 0.15·0.4·0.5·10초 입력 시각의 직전·경계·직후, 동일 시각 순서·중복 프레임·오류, EOF와 빈 목록 구분, 고정 문제 순서, seed 재현·전역 난수 상태 분리. 경계 전후는 0.000001초 차이로 확인한다. 이 하네스 구축 당시에는 게임의 채점·상태 전이 테스트가 없었다. 후속 진척은 아래 게임 구현 1단계 절을 따른다.

### 하네스 마무리 — 2026-10-22

- [x] `mp_hand.py`의 모델 준비·카메라 읽기·RGB 변환·손 검출·표시·종료 흐름과 관측 클래스의 연결 위치를 HARNESS_DESIGN에 기록했다.
- [x] 기존 `tests/support.py`에 가짜 공·양손 → 손 누락 → 읽기 실패 → 모델 오류 → EOF를 재생하는 실행 예제를 추가했다. 별도 실행 파일이나 의존성은 추가하지 않았다.
- [x] 실행 예제 검증 테스트는 구현 전 출력이 없어 실패했고, 예제 추가 후 통과했다.
- [x] 프로젝트에서 `.venv/bin/python --version`: Python 3.10.12.
- [x] 프로젝트에서 `.venv/bin/python -m unittest discover -s tests -t . -v`: **당시 10개 통과·0 skipped**, 종료 코드 0. 이전 8개에 관측 장면 연속 재생과 실행 예제 검증이 더해졌다.
- [x] 프로젝트에서 `.venv/bin/python -m tests.support`: 콘솔에 가짜 프레임과 오류·EOF를 순서대로 출력하고 `재생 종료`, 종료 코드 0. 저장소 루트에서 모듈을 실행하면 tests를 찾지 못하므로 README처럼 프로젝트 내부에서 실행한다.
- [x] 저장소 루트 `git diff --check`: 종료 코드 0. GAME_RULES는 구축 전 스냅샷과 동일하다.

위 결과는 카메라 없는 하네스의 완료 기록이다. 실제 MediaPipe 추론, 공 검출, 게임 채점·상태 전이, 영상·한글 화면, Jetson 검증은 아래 미완료 항목으로 남긴다. commit·push는 하지 않았다.

### 완료 후 재검증 — 2026-10-22

사용자 요청으로 현재 파일과 문서를 다시 대조했다. 현재의 간단한 하네스 범위에서 실행을 막는 문제나 누락은 발견하지 못했다.

- 프로젝트 `.venv/bin/python --version` 및 일반 실행의 prefix 확인: Python 3.10.12, 프로젝트 전용 가상환경.
- `.venv/bin/python -m unittest discover -s tests -t . -v`: 10개 통과, 0 skipped, 종료 코드 0.
- `.venv/bin/python -m tests.support`: 정상·손 누락·읽기 실패·모델 오류·EOF 순으로 출력하고 종료, 종료 코드 0.
- `.venv/bin/python -I -S`에서 프로젝트 경로를 추가한 격리 import: 외부 패키지 없이 성공, import 시 콘솔 출력 없음. 코드 확인에서도 Enum·데코레이터·Protocol·명시적 예외 처리 없이 일반 클래스·함수를 유지한다.
- `.venv/`와 Python 캐시는 git ignore 대상. GAME_RULES는 기존 스냅샷과 동일하며 HANDOFF 삭제를 유지한다.
- 문서의 과거 8개를 현재 결과로 가리키던 문장과 남아 있던 가상 시계 표현을 수정했다. 코드 변경은 없었다. 저장소 루트 `git diff --check`: 종료 코드 0.

이 재검증은 실제 카메라/MediaPipe 연결이나 게임의 0.4초 판정·점수·시간 초과·PAUSED 정책을 검증한 것이 아니다. 이들은 기존 계획대로 후속 구현 대상이다. 원래 계획에서 사용자가 단순화로 제외한 엄격한 타입·입력 순서 검사도 누락으로 세지 않는다.

### 이전 작업 이력

처음 구축한 엄격한 계약은 24개, 도우미까지는 48개가 통과했다. A 문서와 B 계약의 독립 리뷰는 당시 코드를 대상으로 통과했다. 이후 Enum 제거 시 48개, 데이터 검사 제거 시 35개가 통과했다. 이 결과는 현재 코드에 대한 완료 증거가 아니다. 사용자의 이해 우선 요청으로 구조와 테스트 범위를 다시 정리했으므로 현재 결과는 위 하네스 마무리의 10개를 기준으로 한다. 이전 C/D 독립 리뷰를 완료했다고 주장하지 않으며 예전 계획의 리뷰 절차를 현재 작업의 필수 단계로 유지하지 않는다.

환경 설치 명령: `brew install pyenv openssl@3 readline sqlite3 xz zlib pkgconf`, `PYTHON_CONFIGURE_OPTS='--with-openssl=/opt/homebrew/opt/openssl@3' PYTHON_BUILD_HOMEBREW_OPENSSL_FORMULA=openssl@3 pyenv install -s 3.10.12`, 프로젝트에서 `PYENV_VERSION=3.10.12 pyenv exec python -m venv .venv`. 재현 방법은 README에 있다. 초기 상세 보고서는 `/private/tmp/vision-harness-build/`에 작성했다.

## 게임 구현 1단계 — 한 프레임 판정 (2026-10-22)

승인 범위는 `game.py`의 일반 함수 두 개와 행동 테스트, 관련 문서다. 시간·상태·점수·카메라·설치 작업은 포함하지 않는다. 이 절은 아래 전체 게임 체크리스트의 일부 진척이며, 하네스 완료나 한 프레임 판정만으로 전체 항목을 완료 처리하지 않는다.

- [x] 계획 단계의 기준 실행: 프로젝트 Python 3.10.12, unittest 10개 통과·0 skipped, 입력 재생 정상 종료, 루트 `git diff --check` 종료 코드 0을 실제 확인했다. 과거 기록으로 대체하지 않았다.
- [x] `tests/test_game.py`를 먼저 추가하고 `.venv/bin/python -m unittest tests.test_game -v` 실행: 종료 코드 1, `ModuleNotFoundError: No module named 'game'`. 새 모듈이 없는 미구현 실패를 확인했으며 assertion 실패로 기록하지 않는다.
- [x] `point_in_box`와 `inspect_frame` 구현 후 프로젝트 `.venv/bin/python -m unittest discover -s tests -t . -v`: **22개 통과, 0 skipped**, 종료 코드 0. 기존 10개와 새 행동 테스트 12개다. 문서 갱신 중 재실행도 같은 결과(0.017초)였다.
- [x] 프로젝트 `.venv/bin/python --version`: Python 3.10.12, 종료 코드 0.
- [x] 프로젝트 `.venv/bin/python -m tests.support`: 문제 예시 → 공 3개·손 2개 → 공 3개·손 0개 → read_failure → model_error → end_of_stream → 재생 종료, 종료 코드 0.
- [x] 저장소 루트 `git diff --check`: 출력 없음, 종료 코드 0(문서 갱신 중 실행).
- [x] `requesting-code-review`에 따라 별도 읽기 전용 서브에이전트가 현재 파일을 독립 검토: 승인, Critical/Important 없음. Minor 두 건은 제시 영역 비어 있음의 독립 테스트 보강과 과거 결과의 '현재' 표현 정리다. 추가 실관측 불량 후보는 준비를 막고 예측 후보는 막지 않는 테스트를 추가했다(기존 구현에서 통과; 추가 RED로 주장하지 않음). 과거 10개 기록은 당시 기록임을 명시했다.
- [x] 검토 의견 반영 후 최종 `.venv/bin/python -m unittest discover -s tests -t . -v`: **23개 통과, 0 skipped**, 0.022초, 종료 코드 0. 기존 10개와 게임 13개다. `.venv/bin/python -m tests.support`도 같은 순서로 재생 종료, 종료 코드 0. 루트 `git diff --check` 출력 없음.

검토에서 제외한 시간·상태·비전·추적·실장비 기능은 후속 단계로 유지한다. 잘못된 문제 튜플·좌표의 방어적 자료형 검사는 호출자가 올바른 입력을 준비한다는 승인 계약을 따른다. 기존 하네스 이력·사용자 변경·HANDOFF 삭제는 검토 대상에서 제외했고 보존했다. 1단계 구현·검토·검증을 마쳤으며 코드 설명 후 2단계를 자동 시작하지 않는다.

당시 새 테스트는 경계 포함·외부 점, 준비 조건 이탈, 손/공 누락·낮은 점수·미보정·중복 물리적 손, 예측/불량 공 제외, 같은 색 복수 후보, 0.70 경계, 양손 색 교환, 남은 공 이탈/누락, 제시 영역·상자 포함, 양손 위 공 후보의 겹침·한 손 복수 공, 입력 보존을 확인했다. 위치 검사는 이후 사용자 요청으로 손바닥 상자 하나로 단순화했다. 테스트의 좌표는 현장 설정값이 아니다.

`correct`/`wrong`은 한 장의 자세 후보다. 0.4초/4프레임 확정·중복 프레임·문제 생성·카운트다운·10초 제한·점수·결과 화면·PAUSED는 미구현이다. 실제 손/공 검출·저장 영상·한글 화면·Jetson FPS/정확도/복구는 미검증이다. 외부 패키지 설치, commit·push·branch/worktree 변경을 하지 않았고 기존 변경과 HANDOFF 삭제를 유지한다.

## 게임 구현 2단계 — 준비와 문제 시작 (2026-10-22)

당시 승인 범위는 `SETUP → READY → COUNTDOWN → ACTIVE`의 시작 구간, 준비 0.5초, 정상 준비 관측 간격 0.15초, 3초 카운트다운, 문제 추첨과 화면 제출 시각이었다. 정답/오답 0.4초 누적·10초 제한·점수·재준비·장애 처리는 포함하지 않았다. 현재 추첨 기준은 이후 사용자 결정에 따른 GAME_RULES 3절을 따른다.

- [x] `tests/test_game.py`에 준비·문제 시작 테스트를 먼저 추가하고 `.venv/bin/python -m unittest tests.test_game.PreparationTests -v` 실행: 새 API가 없어 10개 `AttributeError`, 종료 코드 1. 미구현 API로 인한 RED이며 assertion 실패라고 기록하지 않는다.
- [x] `create_game_state`, `complete_setup`, `question_candidates`, `update_preparation`, `mark_problem_presented`의 최소 구현 후 준비 단계 10개와 당시 전체 33개 테스트 통과.
- [x] 독립 검토에서 비연속 중복 프레임, 이른/반복 문제 제출, 0.15초 소수 경계가 발견됐다. 회귀 테스트 4개를 먼저 실행해 모두 assertion 실패하는 RED를 확인한 뒤 `processed_frame_ids`, 최초 제출 조건과 현재 이름 `FLOAT_TIME_TOLERANCE`에 해당하는 소수 오차 여유로 각각 GREEN을 확인했다.
- [x] 재검토에서 마지막 정상 준비 프레임과 실제 문제 제출 사이의 0.15초 초과 공백이 발견됐다. 늦은 중복 프레임과 늦은 문제 제출 테스트 2개가 각각 `COUNTDOWN`/`ACTIVE`로 남아 실패하는 RED를 확인했다. `reset_preparation`을 공통으로 사용해 두 테스트와 준비 단계 전체 16개가 GREEN이 됐다.
- [x] 마지막 독립 검토: Critical/Important 없음. 정확히 0.15초인 중복·화면 제출 경로의 개별 테스트가 없다는 Minor는 같은 비교식과 현재 이름 `FLOAT_TIME_TOLERANCE`를 확인하는 정확한 0.15초 경계 테스트가 있어 중복 테스트를 추가하지 않았다.
- [x] 최종 프로젝트 `.venv/bin/python --version`: Python 3.10.12, 종료 코드 0.
- [x] 최종 프로젝트 `.venv/bin/python -m unittest discover -s tests -t . -v`: **39개 통과, 0 skipped**, 0.017초, 종료 코드 0.
- [x] 최종 프로젝트 `.venv/bin/python -m tests.support`: 가짜 관측 → 손 누락 → 읽기 실패 → 모델 오류 → EOF → 재생 종료, 종료 코드 0.
- [x] 문서 기록 후 저장소 루트 `git diff --check`: 출력 없음, 종료 코드 0. 상태 확인에서 변경은 기존 `HANDOFF.md` 삭제와 `[Project01]/` 안의 기존·이번 작업뿐이다.

현재 상태 딕셔너리는 준비·문제 시작에 필요한 값만 담는다. `correct`/`wrong`은 여전히 한 프레임 후보이며 점수나 기회를 바꾸지 않는다. 카메라·MediaPipe·OpenCV 패키지를 설치하지 않았고 저장 영상·실제 화면·Jetson 동작은 검증하지 않았다. 기존 사용자 주석·변경과 루트 `HANDOFF.md` 삭제를 보존했으며 commit·push·branch/worktree 변경을 하지 않았다. 3단계는 자동 시작하지 않는다.

## 게임 구현 3단계 — 정답·오답과 시간 (2026-10-23)

승인 범위는 `ACTIVE` 상태의 정답·오답 연속 판정, 0.4초·최소 4프레임, 10초 제한과 성공 반응 시간이다. 점수·기회·1.5초 결과 표시·재준비·입력 장애 처리는 포함하지 않았다.

- [x] 구현 전 기준 확인: 프로젝트 `.venv/bin/python -m unittest discover -s tests -t . -v`에서 **39개 통과·0 skipped**, 입력 재생 예제 정상 종료.
- [x] `ActiveJudgmentTests` 13개를 먼저 추가하고 실행: `update_active`가 없어 13개 `AttributeError`, 종료 코드 1. 미구현 API의 RED이며 assertion 실패라고 기록하지 않는다.
- [x] 판정 종류·시작/최근 관측 시각·프레임 수와 결과 시각·사유를 상태 딕셔너리에 추가하고, `reset_judgment`, `finish_active`, `update_active`를 최소 구현했다.
- [x] 처음 구현 뒤 13개 중 12개 통과, 비연속 중복 테스트 1개 실패. 원인은 테스트의 마지막 고유 관측 간격이 실제로 0.20초여서 코드가 규칙대로 누적을 초기화한 것이었다. 테스트 시각을 0.15초 이하 간격으로 바로잡았고 제품 코드는 변경하지 않았다.
- [x] 숫자 시각으로 `hold`·판정 변경·0.15초 경계·0.4초/4프레임·문제 제출 전 촬영·비연속 중복·10초 직전/경계/직후·성공 반응 시간을 확인했다.
- [x] 첫 독립 검토에서 새 고유 프레임의 `read_at`이 문제 제출 전이면 판정에서 제외되지만 처리 시각이 제한 시각일 때는 시간 초과를 확인해야 한다는 Important를 받았다. 회귀 테스트가 `ACTIVE != RESULT_TIMEOUT` assertion으로 실패하는 RED를 확인한 뒤, 자세 누적 없이 제한 시간만 확인하도록 수정해 GREEN을 확인했다.
- [x] 같은 프레임 ID의 재전달은 새 정상 입력이 아니므로 제한 시간 확정에도 쓰지 않는다고 규칙과 문서에 명시했다. 이는 제한 시각에 정상 입력이 없으면 장애 여부를 우선 확인한다는 `GAME_RULES`와 맞으며, 장애 감시는 5단계 범위다.
- [x] 재검토 결과 Critical/Important 없음, 원본 규칙과 충돌 없음. Minor로 제안된 “제한 시각의 중복 ID도 `ACTIVE` 유지” 회귀 테스트를 추가했고 기존 구현에서 통과했다. 새 기능의 RED로 주장하지 않는다.
- [x] 최종 프로젝트 `.venv/bin/python --version`: Python 3.10.12, 종료 코드 0.
- [x] 최종 프로젝트 `.venv/bin/python -m unittest discover -s tests -t . -v`: **54개 통과, 0 skipped**, 0.016초, 종료 코드 0.
- [x] 최종 프로젝트 `.venv/bin/python -m tests.support`: 가짜 관측 → 손 누락 → 읽기 실패 → 모델 오류 → EOF → 재생 종료, 종료 코드 0.
- [x] 최종 저장소 루트 `git diff --check`: 출력 없음, 종료 코드 0.

결과 상태는 `RESULT_SUCCESS`, `RESULT_WRONG`, `RESULT_TIMEOUT`까지만 기록한다. 성공 반응 시간은 문제 제출부터 첫 정답 유효 프레임까지이며, 점수·기회는 아직 바꾸지 않는다. 외부 패키지 설치와 카메라·저장 영상·Jetson 검증은 수행하지 않았고, 기존 사용자 변경과 `HANDOFF.md` 삭제를 보존했다. 4단계는 자동 시작하지 않는다.

## 게임 구현 4단계 — 점수와 재준비 (2026-10-23)

승인 범위는 결과 진입 시 점수·기회·완료 시도를 한 번만 반영하고, 결과를 1.5초 유지한 뒤 재준비 또는 요약으로 이동하며, 성공 반응 기록의 평균·최단과 새 판 초기화를 확인하는 것이다. 입력 장애·실제 한글 화면·키 입력 연결은 포함하지 않았다.

- [x] 현재 코드·문서를 다시 대조해 손바닥 상자 하나와 `game.py`의 `random.sample()` 직접 추첨 결정을 보존했다. 문서 충돌은 없었고, 이전 승인 범위 표기만 이번 요청에 따라 4단계로 갱신했다.
- [x] 구현 전 프로젝트 `.venv/bin/python --version`: Python 3.10.12. `.venv/bin/python -m unittest discover -s tests -t . -v`: **56개 통과, 0 skipped**, 0.025초, 종료 코드 0. `.venv/bin/python -m tests.support`는 기존 순서로 재생 종료, 루트 `git diff --check`는 출력 없이 종료 코드 0.
- [x] 기존 실제 결과 흐름과 새 `ResultFlowTests`를 먼저 추가했다. 대상 22개 실행에서 점수·기회 미구현 assertion 실패 5개와 새 API 미구현 `AttributeError` 6개, 종료 코드 1을 확인했다. 현재 동작이 기대와 다른 RED와 미구현 API 오류를 구분해 기록한다.
- [x] `STARTING_CHANCES`, `RESULT_DISPLAY_DURATION`과 상태의 `score`, `chances`, `completed_attempts`, `reaction_times`를 추가했다. `finish_active`는 `ACTIVE`에서만 결과를 반영하며, 성공은 점수와 반응 시간을 추가하고 오답·시간 초과는 기회를 하나 줄인다.
- [x] `reset_round`, `update_result`, `get_summary`, `restart_game`을 일반 함수로 추가했다. 결과 1.5초 직전·경계, `RESET → READY`, 마지막 기회의 `SUMMARY`, 성공 없는 기록, 보정 유지 여부에 따른 새 판 상태를 숫자 시각과 상태 딕셔너리로 확인했다.
- [x] 대상 `ActiveJudgmentTests`와 `ResultFlowTests` **22개 통과**, 이어서 전체 **63개 통과·0 skipped**, 종료 코드 0을 확인했다.
- [x] 읽기 전용 독립 검토: Critical/Important 없음, 승인. 구현·문서 일치와 전체 63개 테스트를 확인했다. 범위 밖의 입력 장애·실제 카메라/모델/추적·화면 지연·키 입력은 판단에서 제외했다.
- [x] 검토 Minor는 재준비 보존 테스트가 0점·빈 반응 목록만 사용한다는 점이었다. 실제 구현 오류는 아니지만 성공 기록이 이미 있는 상태에서 오답 라운드 뒤에도 1점·반응 시간 목록이 보존되는 테스트로 보강했다. 제품 코드는 바꾸지 않았고 새 RED로 주장하지 않는다. 해당 테스트와 `ResultFlowTests` 7개가 통과했다.
- [x] 최종 프로젝트 `.venv/bin/python --version`: Python 3.10.12, 종료 코드 0.
- [x] 최종 프로젝트 `.venv/bin/python -m unittest discover -s tests -t . -v`: **63개 통과, 0 skipped**, 0.028초, 종료 코드 0.
- [x] 최종 프로젝트 `.venv/bin/python -m tests.support`: 가짜 관측 → 손 누락 → 읽기 실패 → 모델 오류 → EOF → 재생 종료, 종료 코드 0.

현재 순수 로직은 결과 상태와 누적 기록을 다루지만 실제 화면에 1.5초 결과를 그리거나 `r` 키를 읽지는 않는다. `update_result`와 `restart_game`을 실제 반복문에 연결하는 일은 화면 단계에서 진행한다. 입력 공백·모델 예외·`PAUSED` 복구는 다음 5단계이며, 설치·저장 영상·실제 카메라·Jetson 검증은 수행하지 않았다. 기존 사용자 변경과 루트 `HANDOFF.md` 삭제를 보존했고 commit·push·branch/worktree 변경을 하지 않았다.

### 사용자 주석 스타일 반영 — 2026-10-23

- 사용자 예시의 함수 역할 설명, 구역 구분선, 조건이 필요한 이유, 낯선 문법 메모 방식을 따라 `game.py` 전체 주석을 정리했다. 설정값·상태 딕셔너리·준비/카운트다운·정답/오답 누적·반응 시간에 설명과 숫자 예시를 추가했다.
- `question is None`은 문제를 전달하지 않은 경우라는 실제 조건으로 설명하고, `next()`가 파이썬 기본 함수라는 점을 명확히 했다. 기존 사용자 주석의 문체를 따르되 실행 코드·설정값·함수와 변수 이름·테스트는 변경하지 않았다.
- 변경 전 프로젝트 `.venv/bin/python -m unittest discover -s tests -t . -v`: **54개 통과, 0 skipped**, 0.015초, 종료 코드 0.
- 변경 전후 `.venv/bin/python -c`에서 `ast.parse`와 `ast.dump`로 비교한 실행 구조의 SHA-256이 동일했다. 주석만 변경한 작업이므로 새 행동 테스트나 RED를 만들었다고 주장하지 않는다.
- 변경 후 프로젝트 `.venv/bin/python -m unittest discover -s tests -t . -v`: **54개 통과, 0 skipped**, 0.016초, 종료 코드 0. 프로젝트 `.venv/bin/python -m tests.support`도 기존 순서대로 재생 종료, 종료 코드 0.
- 저장소 루트 `git diff --check`: 출력 없음, 종료 코드 0. 장비 검증·설치·후속 단계 구현은 수행하지 않았다.

### 손바닥 상자 하나로 관측 단순화 — 2026-10-23

사용자 승인으로 손 위치 정보와 판정을 손바닥 중심·손바닥 상자 기준으로 정리했다. 현재 위치 규칙은 GAME_RULES v0.13의 5절이 원본이다.

- [x] 변경 전 프로젝트 `.venv/bin/python -m unittest discover -s tests -t . -v`: **54개 통과, 0 skipped**, 0.015초, 종료 코드 0.
- [x] 테스트의 `Hand` 호출에서 불필요한 상자 인자를 먼저 제거하고 정답 장면 테스트를 실행했다. 기존 생성자가 여전히 인자를 더 요구해 `TypeError: Hand.__init__() missing 1 required positional argument: 'palm_box'`, 종료 코드 1. API 변경 전의 RED이며 assertion 실패로 기록하지 않는다.
- [x] `Hand`의 불필요한 생성자 인자·속성과 중복 위치 검사를 제거하고, 입력 재생 예제·모든 테스트용 호출을 맞췄다. 한 프레임 판정 테스트 **13개 통과**, 종료 코드 0.
- [x] 위치 경계 테스트에서 제거된 조건만 검사하던 하위 경우를 정리했다. 제시 영역 밖의 손바닥 중심, 손바닥 상자 밖의 공, 손바닥 상자 안이지만 제시 영역 밖인 공, 양손 겹침, 한 손의 복수 공, 입력 보존 등 나머지 검증은 유지한다.
- [x] GAME_RULES v0.13, README·기획·결정·하네스 설계/계획·작업 안내·체크리스트의 현행 요구를 맞췄다. 기존 `portrait_ui_mockup.png` 파일은 보존하고, 현재 기준과 다른 화면 예시의 링크·본문 삽입은 제거했다.
- [x] 변경 후 프로젝트 `.venv/bin/python -m unittest discover -s tests -t . -v`: **54개 통과, 0 skipped**, 0.015초, 종료 코드 0.
- [x] 프로젝트 `.venv/bin/python --version`: Python 3.10.12. `.venv/bin/python -m tests.support`: 정상 관측·손 누락·읽기 실패·모델 오류·EOF 뒤 재생 종료, 종료 코드 0.
- [x] 저장소 루트 `git diff --check`: 출력 없음, 종료 코드 0. 코드·문서 검색으로 제거 대상의 인자·조건·계산 및 표시 요구가 남지 않았음을 확인했다.
- [x] `requesting-code-review`에 따른 읽기 전용 독립 검토: 승인, Critical/Important/Minor 없음. 모든 생성자 호출·위치 경계·양손 겹침·한 손 복수 공 보류·문서 일관성을 확인했다. 검토자도 전체 54개 테스트·입력 재생·공백 검사를 직접 실행해 통과했다.

시간·점수·장애 정책과 기존 사용자 주석은 유지했다. 저장 영상·실제 카메라·Jetson 확인, 설치, 후속 기능 구현은 수행하지 않았다. 기존 사용자 변경과 루트 HANDOFF 삭제를 보존하며 commit·push·branch/worktree 변경은 하지 않았다.

### 손별 공 후보 개수 확인 정리 — 2026-10-23

- 사용자 코드대로 `reason`, `ball_count`, 일반 `for`문으로 0개·1개·여러 개를 구분하고, 여러 개이면 `break`로 확인을 끝낸다. 안내는 사용자가 정한 `손 위의 공이 여러 개입니다.`와 `공이 확인되지 않습니다. 손에 있는 공을 보여주세요.`를 사용한다.
- 기존 반환값을 유지하기 위해 `has_multiple_balls`로 손별 색 저장 여부를 구분한다. 여러 후보가 있는 경우 양손 색을 확정하지 않고, 누락만 있는 경우에는 반대 손에서 확인한 색을 유지한다. 안내 문자열을 게임 제어 조건으로 사용하지 않는다.
- 테스트를 먼저 보강하고 `.venv/bin/python -m unittest tests.test_game.FrameInspectionTests.test_two_ball_candidates_on_one_palm_are_ambiguous tests.test_game.FrameInspectionTests.test_missing_palm_ball_holds_and_keeps_the_other_hand_color -v` 실행: 기존 안내 문구와 새 문구가 달라 2개 테스트의 7개 하위 경우가 assertion 실패, 종료 코드 1(RED).
- 구현 후 `.venv/bin/python -m unittest discover -s tests -t . -v`: **55개 통과, 0 skipped**, 0.017초, 종료 코드 0. 양쪽 손의 누락, 양손 누락, 한 손의 복수 후보 및 반대 손 누락과의 조합에서 보류·안내 우선순위·손별 색 반환을 확인했다.
- 프로젝트 `.venv/bin/python -m tests.support`: 기존 순서로 재생 종료, 종료 코드 0. 저장소 루트 `git diff --check`: 출력 없음, 종료 코드 0. 실제 장비 검증은 추가하지 않았다.

### 전체 후보에서 문제 추첨 — 2026-10-23

사용자 승인으로 매번 6가지 전체 조합에서 문제를 추첨하도록 바꾼 당시 기록이다. 같은 문제가 연속으로 나올 수 있으며, 장애 복구 뒤의 추첨 기준도 동일하다. 규칙의 원본은 GAME_RULES v0.14의 3절이며, 이후 구현 방식은 아래 직접 색 추첨 기록을 따른다.

- [x] 변경 전 `.venv/bin/python -m unittest discover -s tests -t . -v`: **55개 통과, 0 skipped**, 0.016초, 종료 코드 0.
- [x] 같은 난수 흐름으로 준비·카운트다운·문제 표시를 두 번 진행하는 테스트를 먼저 추가했다. `.venv/bin/python -m unittest tests.test_game.PreparationTests.test_seeded_draws_can_repeat_across_preparation_cycles -v`: 두 번째 문제가 `('blue', 'red')`여서 기대한 연속 `('green', 'blue')`와 달라 assertion 실패, 종료 코드 1(RED).
- [x] 문제 이력용 상태값·후보 제외 조건·문제 표시 시 이력 저장을 제거했다. 당시 `question_candidates()`는 인자 없이 서로 다른 두 색의 순서 있는 6개 조합을 반환했다. 준비·문제 표시 시각·판정·점수·장애 정책의 나머지 부분은 유지했다.
- [x] `.venv/bin/python -m unittest tests.test_game.PreparationTests -v`: **17개 통과**, 종료 코드 0. 전체 후보 생성과 두 번의 연속 동일 문제 출제를 확인했다.
- [x] 현행 규칙·README·설계·계획·결정·체크리스트·작업 안내를 같은 추첨 기준으로 맞췄다. 과거 검증 이력은 현재 정책과 구분한다. 장애 복구 정책은 문서만 맞추며 실제 장애 기능을 구현했다고 표시하지 않는다.
- [x] 프로젝트 `.venv/bin/python --version`: Python 3.10.12. `.venv/bin/python -m unittest discover -s tests -t . -v`: **56개 통과, 0 skipped**, 0.015초, 종료 코드 0.
- [x] 프로젝트 `.venv/bin/python -m tests.support`: 정상 관측·손 누락·읽기 실패·모델 오류·EOF 뒤 재생 종료, 종료 코드 0.
- [x] 저장소 루트 `git diff --check`: 출력 없음, 종료 코드 0. 코드·문서 검색에서도 제거한 이력 참조와 제외 요구가 남지 않았음을 확인했다.
- [x] 사용자 요청에 따른 읽기 전용 서브에이전트 독립 리뷰: 승인, Critical/Important/Minor 없음. 검토자가 전체 56개 테스트·입력 재생·공백 검사를 새로 실행해 통과했고, 파일 저장 없이 메모리에서 이전 제외 동작을 재도입하자 연속 출제 테스트가 실패하는 것도 확인했다. 실제 장애 복구·저장 영상·Jetson 검증은 후속 범위로 구분했다.

카메라·저장 영상·Jetson 검증과 설치·후속 기능 구현은 수행하지 않았다. 기존 사용자 변경과 HANDOFF 삭제를 유지한다. 자동 커밋·푸시·브랜치/워크트리 변경은 하지 않는다.

### 서로 다른 두 색을 직접 추첨 — 2026-10-23

- 당시 사용자 승인으로 게임 문제 생성을 `tuple(rng.sample(COLORS, 2))`로 단순화하고, 전체 후보를 만들던 함수를 제거했다. `sample`이 뽑은 순서를 왼손·오른손 순서로 사용하며, 한 문제 안의 색 중복을 막고 연속 동일 문제는 허용한다. 이후 모듈 사용 위치의 변경은 아래 기록을 따른다.
- 함수의 후보 목록을 검사하던 테스트를 실제 준비·카운트다운을 거친 문제 검사로 교체했다. 고정 seed 0~29에서 6가지 순서쌍을 모두 확인한다. 연속 출제 테스트는 특정 seed의 정확한 문제 두 개 대신 고정 난수 흐름의 20회 준비 주기에서 연속 동일 문제가 실제로 발생하는지를 확인하도록 바꿨다.
- 구현 변경 전 `.venv/bin/python -m unittest tests.test_game.PreparationTests.test_random_questions_cover_all_six_ordered_pairs tests.test_game.PreparationTests.test_seeded_draws_can_repeat_across_preparation_cycles tests.test_game.PreparationTests.test_countdown_creates_a_new_question_after_three_seconds -v`: **3개 통과**, 종료 코드 0. 기존 동작을 유지하는 정리이므로 새 RED를 만들었다고 주장하지 않는다.
- 변경 후 `.venv/bin/python -m unittest discover -s tests -t . -v`: **56개 통과, 0 skipped**, 0.026초, 종료 코드 0. `(파랑, 빨강)`과 `(빨강, 파랑)`을 포함한 6가지 순서쌍·연속 동일 출제·카운트다운 시각을 확인했다.
- 프로젝트 `.venv/bin/python -m tests.support`: 기존 순서로 재생 종료, 종료 코드 0. 저장소 루트 `git diff --check`: 출력 없음, 종료 코드 0.
- HARNESS_DESIGN의 현행 API·문제 생성 설명을 실제 코드에 맞췄다. 입력 재생 도우미의 주어진 후보 목록 선택과 실제 게임의 두 색 추첨을 구분했다. 저장 영상·카메라·Jetson 검증과 설치·후속 기능 구현은 수행하지 않았다.
- 읽기 전용 서브에이전트 독립 검토: 승인, Critical/Important/Minor 없음. 검토자가 실제 게임 흐름에서 seed 6의 `('blue', 'red')`, 전체 56개 테스트·입력 재생·공백 검사를 직접 확인했다. 파일 수정은 하지 않았다.

### game.py에서 random 직접 사용 — 2026-10-23

- 사용자 승인으로 `game.py`에 `import random`을 추가하고 문제를 `tuple(random.sample(COLORS, 2))`로 생성하도록 바꿨다. `update_preparation(game_state, frame, regions, now)`에서 난수 객체 인자를 제거해 실제 호출자가 난수 객체를 따로 준비하지 않아도 된다.
- 테스트 호출을 먼저 네 인자로 바꾸고 `.venv/bin/python -m unittest tests.test_game.PreparationTests.test_ready_must_continue_for_half_a_second -v` 실행: 기존 함수가 여전히 난수 인자를 요구해 `TypeError`, 종료 코드 1(RED). API 변경에 따른 오류이며 assertion 실패로 기록하지 않는다.
- 구현 후 `.venv/bin/python -m unittest tests.test_game.PreparationTests -v`: **17개 통과**, 종료 코드 0.
- 테스트는 `random.seed`로 난수 흐름을 재현하고, `addCleanup`에 등록한 `random.setstate`로 테스트 전 난수 상태를 복원한다. 실제 게임 코드에는 고정 seed를 넣지 않았다. 입력 재생 도우미의 기존 난수 객체 사용은 유지한다.
- `.venv/bin/python -m unittest discover -s tests -t . -v`: **56개 통과, 0 skipped**, 0.027초, 종료 코드 0. 역순을 포함한 6가지 문제·연속 동일 문제·기존 준비 및 시간 조건을 확인했다.
- `.venv/bin/python -c`에서 `PreparationTests` 17개를 실행하기 전후의 `random.getstate()`를 직접 비교해 원래 상태 복원을 확인했다. 종료 코드 0.
- 프로젝트 `.venv/bin/python -m tests.support`: 기존 순서로 재생 종료, 종료 코드 0. 저장소 루트 `git diff --check`: 출력 없음, 종료 코드 0.
- HARNESS_DESIGN의 함수 인자·문제 생성·재현 방법과 OPEN_DECISIONS의 현재 난수 사용 설명을 맞췄다. 설치·장비 검증·후속 기능은 진행하지 않았으며 기존 변경과 HANDOFF 삭제를 유지했다.
- 읽기 전용 서브에이전트 독립 검토: 승인, Critical/Important/Minor 없음. 검토자가 네 인자 호출 일치·실제 코드의 seed 미고정·테스트 난수 상태 복원을 확인하고, 전체 56개 테스트·입력 재생·공백 검사를 직접 재실행해 통과했다.

### 2단계 가독성 정리 — 2026-10-22

- 사용자 확인 중 드러난 혼동을 줄이기 위해 `update_preparation`을 명시적인 `READY`와 `COUNTDOWN` 블록으로 재배치했다.
- `state` 매개변수는 `game_state`, 한 프레임 결과는 `frame_result`, 불리언은 `is_ready`, 최근 준비 관측은 `last_ready_observed_at`, 소수 계산 여유는 `FLOAT_TIME_TOLERANCE`로 이름을 분명히 했다.
- 한 줄이던 `inspect_frame(...)["ready"]`를 두 줄로 나눴다. 기능과 설정값은 변경하지 않았다.
- 변경 전 전체 39개 테스트가 통과했고, 변경 후에도 39개가 통과했다. 독립 검토의 500개 무작위 80프레임 비교에서도 이전 구현과 결과가 같았다.
- 검토 Minor로 지적된 `reset_preparation` 내부 시간표는 실행 위치와 맞지 않고 0.3초 간격 예시가 포함돼 있었다. 같은 설명을 0.1초 간격의 짧은 주석으로 `READY` 블록 앞에 옮겼다.

### 사용자 코드 검토 — 색별 후보를 한 번에 모으기 (2026-10-22)

아래는 변경 당시 기록이다. 이후 사용자 요청으로 이 변경을 되돌렸으며 현재 코드는 다음 원상복구 기록을 따른다.

- 사용자 제안대로 후보 분류에서 `frame.balls`를 한 번 순회해 색별 목록에 넣은 뒤, 색별 후보 수가 하나인지 확인한다. 미확인 색을 한글 안내에 포함한다. 준비·정답/오답 조건과 나머지 사용자 주석·코드는 유지한다.
- RED: `.venv/bin/python -m unittest tests.test_game.FrameInspectionTests.test_missing_or_duplicate_ball_names_the_color_to_check -v` → 종료 코드 1, 빨강·초록·파랑의 0개/2개 여섯 경우 모두 일반 문구 `공 확인 필요`여서 assertion 실패.
- GREEN: 프로젝트 `.venv/bin/python -m unittest discover -s tests -t . -v` → **24개 통과, 0 skipped**, 0.014초, 종료 코드 0.
- 프로젝트 `.venv/bin/python -m tests.support` → 정상 관측·손 누락·읽기 실패·모델 오류·EOF 뒤 재생 종료, 종료 코드 0.
- 저장소 루트 `git diff --check` → 출력 없음, 종료 코드 0.
- 실제 장비 성능은 측정하지 않았다. 줄어든 것은 후보 분류 과정의 목록 순회이며, 제시 영역 비어 있음 확인 등 후속 검사는 그대로다.
- 독립 검토자가 변경 부분을 읽기 전용으로 재검토: 승인, 구체적인 문제 없음. 지원 색·실관측·유효성 필터와 후보 유일성이 유지되고 색별 안내와 테스트가 일치함을 확인했다.

### 공 후보 분류 원상복구 (2026-10-22)

- 사용자 요청으로 색마다 전체 후보를 확인하던 코드와 `공 확인 필요` 안내를 복원했다. 이 변경에만 추가했던 COLOR_NAMES·색별 임시 목록·색별 문구 테스트를 제거했다. 사용자 주석과 나머지 판정은 보존했다.
- 프로젝트 `.venv/bin/python -m unittest discover -s tests -t . -v`: 23개 통과, 0 skipped, 0.028초, 종료 코드 0.
- 프로젝트 `.venv/bin/python -m tests.support`: 기존 순서로 재생 종료, 종료 코드 0.
- 저장소 루트 `git diff --check`: 출력 없음, 종료 코드 0. 실제 장비 검증은 추가하지 않았다.

### 사용자 용어 변경 — 손 위의 공 후보 (2026-10-22)

- 사용자 요청대로 `linked`를 `ball_colors_on_hands`, `owners`를 `candidate_hands`로 변경했다. 해당 주석·보류 사유·테스트 이름·README·기획/규칙/설계/계획/결정/작업 지침의 손과 공 관계 표현을 '손 위의 공 후보'로 맞췄다. 카메라 연결·추적 재연결 용어는 유지한다.
- 판정 조건·시간·점수·반환 키 `hand_colors`는 변경하지 않았다. 이름과 설명 변경이므로 기존 행동 테스트를 유지했고 새 기능용 RED를 주장하지 않는다. 게임 규칙의 2D 위치 근사와 실제 접촉 미확정 한계도 유지한다.
- 변경 전 `.venv/bin/python -m unittest discover -s tests -t . -v`: 23개 통과, 0 skipped, 종료 코드 0(0.013초).
- 변경 후 같은 명령: 23개 통과, 0 skipped, 종료 코드 0(0.015초). 두 테스트 이름만 손 위 후보 표현으로 바뀌었으며 기존 assertion은 유지했다.
- 독립 읽기 전용 검토: 승인, 구체적인 문제 없음. 내부 이름 변경이 판정과 반환 키를 유지하며 문서가 물리적 접촉을 확정한다고 주장하지 않음을 확인했다.
- 프로젝트 `.venv/bin/python -m tests.support`: 정상 관측·손 누락·읽기 실패·모델 오류·EOF 뒤 재생 종료, 종료 코드 0.
- 저장소 루트 `git diff --check`: 출력 없음, 종료 코드 0. 기존 사용자 주석·수정과 HANDOFF 삭제를 보존하며 설치·장비 검증·후속 게임 단계는 진행하지 않았다.

## 게임 구현 5단계 — 입력 장애 (2026-10-23)

승인 범위는 카메라 없는 순수 로직에서 짧은 입력 공백·읽기 실패·모델 예외, `PAUSED` 전환과 상태별 복구를 확인하는 것이다. 실제 카메라 읽기 스레드·MediaPipe 예외·오류 화면·Jetson 동작은 포함하지 않는다.

- [x] 구현 전 프로젝트 `.venv/bin/python --version`: Python 3.10.12. 전체 unittest **63개 통과·0 skipped**, 입력 재생 예제 정상 종료, 루트 `git diff --check` 출력 없음·종료 코드 0을 현재 파일에서 다시 확인했다.
- [x] `InputFailureTests` 11개를 먼저 추가하고 실행했다. `update_input_state`가 없어 11개 테스트에서 12개 `AttributeError`(subTest 2개 포함), 종료 코드 1을 확인했다. 미구현 API의 RED이며 assertion 실패라고 기록하지 않는다.
- [x] `INPUT_PAUSE_DURATION=0.5`와 `last_normal_input_at`, `input_gap_started_at`, `input_error_reason`, `paused_from_status`를 상태 딕셔너리에 추가했다. 별도 입력 클래스·시계·예외 계층은 만들지 않았다.
- [x] `reset_input_continuity`, `pause_for_input`, `recover_input`, `update_input_state`를 일반 함수로 추가했다. 읽기 실패 또는 0.15초 초과 공백은 연속 기록을 지우고, 0.5초 이상 공백·모델 예외는 미완료 문제만 무효로 하며 누적 기록을 보존한다.
- [x] 첫 구현 뒤 11개 중 10개 통과, 정확히 0.15초 경계 테스트 1개 실패를 확인했다. systematic-debugging으로 추적한 결과 테스트 프레임의 기본 `read_at`이 문제 제출 전이라 기존 코드가 판정에서 제외한 것이 원인이었다. 테스트 입력의 `read_at`을 제출 시각으로 바로잡았고 제품 코드는 변경하지 않아 11개가 통과했다.
- [x] 결과 표시 중 발생한 모델 오류가 표시 종료 뒤 새 오류 이벤트 없이도 복구 대기로 이어지는 테스트를 강화했다. 기존 상태가 `RESET`이라 assertion 실패하는 RED를 확인한 뒤, `update_result`가 진행 중인 모델 오류 또는 0.5초 이상 공백을 `PAUSED`로 넘기도록 최소 수정해 GREEN을 확인했다.
- [x] 짧은 공백의 제한 시간 유지·복귀 후 시간 초과, 떨어진 짧은 공백 비합산, 준비/카운트다운 취소, `SETUP`·`ACTIVE` 복구 차이, 확정 결과·요약 보존, 손·공 누락 정상 프레임을 숫자 시각과 가짜 관측으로 확인했다.
- [x] 구현과 문서 갱신 전 전체 unittest **74개 통과·0 skipped**, 0.025초, 종료 코드 0을 확인했다.
- [x] 읽기 전용 독립 검토자가 Python 3.10.12의 전체 74개 테스트와 `git diff --check`를 다시 실행했다. Critical 없음, Important 2건과 Minor 2건을 보고했으며 실제 카메라·UI·Jetson은 후속 범위로 제외했다.
- [x] Important 1: 결과 종료 직전 모델 오류 뒤 `'no_input'` 또는 `'read_failure'`가 오면 오류 이유가 덮여 `RESET`으로 가는 재현 테스트가 각각 실패했다. 정상 새 프레임 전에는 `model_error`를 유지하도록 수정해 두 경우가 `PAUSED`가 되는 GREEN을 확인했다.
- [x] Important 2: 같은 프레임 ID를 반복하면 입력 정상 시각만 계속 갱신되어 `ACTIVE`가 끝나지 않는 재현을 확인했다. 정상 입력에 기존 `Frame.frame_id`를 전달하고, 같은 최신 번호나 이미 처리한 번호는 입력 없음으로 다루도록 했다. 중복만 0.5초 이어지면 `PAUSED`, 같은 중복으로는 복구되지 않고 새 번호에서만 `READY`가 되는 테스트가 RED(TypeError: 새 인자 미구현) 뒤 GREEN이 됐다.
- [x] Minor 1: 읽기 실패 테스트의 첫 프레임이 문제 표시 전에 읽힌 값이라 판정 기록이 원래 비어 있었다. `read_at=10.0`으로 맞추고 실패 전 `correct` 1프레임을 확인한 뒤 읽기 실패가 기록을 지우는지 검증하도록 보강했다.
- [x] Minor 2: HARNESS_DESIGN의 현재 범위 문장을 4단계에서 입력 장애 복구를 포함한 5단계로 고쳤다. README와 설계 문서의 실제 연결 예시에 `frame.frame_id` 전달 순서를 명시했다.
- [x] 검토 지적 반영 뒤 `InputFailureTests` **13개 통과**, 전체 unittest **76개 통과·0 skipped**, 0.025초, 종료 코드 0을 확인했다.
- [x] 최종 프로젝트 `.venv/bin/python --version`: Python 3.10.12, 종료 코드 0.
- [x] 최종 프로젝트 `.venv/bin/python -m unittest discover -s tests -t . -v`: **76개 통과, 0 skipped**, 0.027초, 종료 코드 0.
- [x] 최종 프로젝트 `.venv/bin/python -m tests.support`: 정상 관측·손 누락·읽기 실패·모델 오류·EOF 뒤 `재생 종료`, 종료 코드 0.
- [x] 최종 프로젝트 `.venv/bin/python -m py_compile game.py tests/test_game.py`: 출력 없음, 종료 코드 0.
- [x] 최종 저장소 루트 `git diff --check`: 출력 없음, 종료 코드 0. `git status --short`에서 기존 루트 `HANDOFF.md` 삭제와 `[Project01]/` 안의 기존·이번 작업만 확인했다.
- [x] 2026-10-23 `update_input_state`의 `model_error` 분기를 일반 오류 기록보다 앞으로 옮기고, 분기 안에서 오류 이유를 먼저 저장하도록 정리했다. 결과·요약·이미 `PAUSED`인 상태에서도 모델 오류 이유를 잃지 않는 기존 동작은 유지했다.
- [x] 위 순서 정리 후 관련 `InputFailureTests` 3개 통과, 전체 unittest **76개 통과·0 skipped**(0.024초), 입력 재생 예제 정상 종료를 확인했다. 저장소 루트 `git diff --check`도 다시 실행해 출력 없음과 종료 코드 0을 확인했다.

외부 패키지 설치, 실제 카메라·모델·영상·Jetson 시험, commit·push·branch/worktree 변경은 하지 않았다. 기존 사용자 변경과 루트 `HANDOFF.md` 삭제를 보존했다. 이 문장은 당시 5단계 종료 기록이며, 이후 사용자 승인으로 아래 6·7단계를 함께 진행했다.

## 게임 구현 6·7단계 — 실제 손·공 관측 코드 (2026-10-23)

승인 범위는 `mp_hand.py` 흐름을 따른 손 관측과 `pingpong_circle_overlay.py` 흐름을 따른 색 공 관측·미리보기다. 게임 상태와 관측을 연결하는 8단계, 한글 정보 띠, 추적은 포함하지 않는다.

- [x] 구현 전 프로젝트 `.venv`를 확인했다. Python은 3.10.12이며 `cv2`·`numpy`·`mediapipe`·`PIL`은 설치되어 있지 않다. 관련 노트북에도 게임용 확정 버전이 없어 임의 설치나 버전 변경을 하지 않았다. 프로젝트 안에는 손 모델·게임 저장 영상·한글 폰트가 없다.
- [x] `tests/test_vision.py`를 먼저 추가하고 실행해 `ModuleNotFoundError: No module named 'vision'`을 확인했다(RED). 이후 정규화 손바닥 중심·상자, 좌우 매핑, 관측 복사, 공 좌표 변환, 모폴로지 순서와 모델 옵션 전달을 일반 값으로 검증했다.
- [x] `vision.py`에 손바닥 중심·상자 계산, 명시적인 물리 손 매핑, MediaPipe 모델 준비·RGB 변환·손 검출을 구현했다. 상자 여유는 픽셀에서 긴 변의 10%를 계산한 뒤 정규화하며, 손가락 각도나 펼친 개수는 계산하지 않는다.
- [x] `vision.py`에 BGR→LAB 변환, 색별 마스크, 선택 가능한 모폴로지, 외곽선, 면적·중심, 원·중심·외곽선 오버레이를 구현했다. 현재는 2026-10-24 결정에 따라 최소 면적 필터 없이 색마다 가장 큰 외곽선 하나만 고른다.
- [x] `MORPHOLOGY_MODE` 기본값은 `none`으로 두고 `open`·`close`·`open_close`의 판단 기준을 코드 주석과 README에 기록했다. 현장에서 RAW/처리 마스크를 비교한 뒤 촬영 조건·문제·선택·전후 차이·이유·임계값을 README에 남기도록 했다.
- [x] `tests/test_main.py`를 먼저 추가하고 실행해 `ModuleNotFoundError: No module named 'main'`을 확인했다(RED). 이후 최신 프레임만 복사해 전달하는 `CameraReader`를 구현했다. 읽기 스레드는 카메라만 다루고 모델·게임·화면 상태를 변경하지 않는다.
- [x] 독립 검토에서 `hand_mapping`이 빈 채로 유지되는 문제가 Important로 발견됐다. 좌·우 실제 손을 각각 0.5초 보여 준 뒤 Space로 확정하는 간단한 딕셔너리 기반 보정을 추가했다. 누락·낮은 신뢰도·서로 같은 원시 레이블이면 안정 시간을 초기화하거나 보정을 다시 시작한다.
- [x] 보정 테스트 세 개를 먼저 추가해 `AttributeError: module 'main' has no attribute 'create_hand_calibration'`을 확인한 뒤(RED), 구현 후 `tests.test_main` 4개가 통과했다.
- [x] 당시 독립 검토의 Minor 의견을 반영해 같은 색 공 후보를 모두 보존하는 순수 함수 테스트를 추가했고 통과했다. 이 동작과 테스트는 2026-10-24 사용자 결정으로 대체되어, 현재는 같은 색에서 가장 큰 외곽선 하나만 보존한다.
- [x] 실제 실행 파일 `main.py`의 순서는 모델 준비 → 카메라 읽기 → 회전 → RGB 손 검출 → LAB 공 검출 → 새 `Frame` 생성 → 공·손 오버레이 → 화면 출력 → 종료 정리다. `SHOW_MASKS=True`이면 현장에서 색별 RAW/처리 마스크를 비교할 수 있다.
- [x] 독립 읽기 전용 검토 결과 Critical 없음. Important였던 손 매핑과 체크리스트 상태를 수정했고, OpenCV 핵심 흐름의 실제 검증은 설치되지 않은 의존성과 영상·장비가 필요한 현장 검증으로 명확히 남겼다.
- [x] 최종 프로젝트 `.venv/bin/python --version`: Python 3.10.12. `.venv/bin/python -m py_compile contracts.py game.py vision.py main.py tests/test_vision.py tests/test_main.py`: 출력 없음·종료 코드 0.
- [x] 최종 프로젝트 `.venv/bin/python -m unittest discover -s tests -t . -v`: **87개 통과, 0 skipped**, 종료 코드 0. `.venv/bin/python -m tests.support`: 기존 가짜 입력 순서 뒤 `재생 종료`, 종료 코드 0. 저장소 루트 `git diff --check`: 출력 없음·종료 코드 0.

실제 MediaPipe 모델 로딩, OpenCV 색 검출, GStreamer 카메라, 양손 좌우 보정, 저장 영상 재현, LAB 임계값·모폴로지 선택, FPS·정확도·종료 복구는 미검증이다. 이 항목들은 Jetson과 촬영 영상에서 확인하기 전 완료로 표시하지 않는다. 외부 패키지 설치, commit·push·branch/worktree 변경은 하지 않았으며 기존 사용자 변경과 루트 `HANDOFF.md` 삭제를 보존했다. 8단계 게임 연결로 자동 진행하지 않는다.

## 단계 0 — 카메라 없이 코드 시작

- [x] 시각과 공·손의 구조화된 관측 결과를 입력받는 게임 로직을 정의하고, 가짜 관측으로 정답·오답·시간 초과·카메라 장애를 재현한다. 실제 카메라 연결 여부와 구분해 위 게임 구현 1~5단계 기록에 증거를 남겼다.
- [ ] 카메라와 저장 영상이 같은 Frame 정보를 만들도록 일반 함수로 연결한다. 실제 게임 영상이 없다는 사실을 기록하고, 수업 이미지를 인식 정확도 검증 자료로 취급하지 않는다.
- [ ] 문제 화면 제출·프레임 읽기·관측 완료 시각을 구분하고 게임 함수에 초 단위 현재 시각을 전달한다. 직접 지정한 시각과 관측으로 경계 시각을 재현하고, 문제 표시 전 프레임·중복 프레임은 채점에서 제외한다.
- [ ] 저장 영상은 영상 속 시각으로 검출을 재현하고 EOF는 정상 종료로 구분한다. 전체 게임 재현에는 영상과 맞는 고정 문제 순서를 사용한다. 실시간 표시 지연 검증과 구분하며, 게임 규칙 자체는 가짜 관측과 직접 지정한 초 단위 시각으로 먼저 검증한다.
- [x] 사용자 제공 설치·다운로드 명령과 Jetson의 모델 배치 경로 `src/models/MediaPipe/hand_landmarker.task`를 기록한다. Jetson에 다운로드되어 있다는 것은 사용자 보고이며, 현재 저장소에는 모델 파일이 없다.
- [ ] `[Project01]/`에서 상대 모델 경로를 그대로 사용해 Jetson의 MediaPipe 손 모델 로딩·실제 추론 성공 여부를 확인한다. 사용자 결정에 따라 별도 파일 존재 검사와 누락 전용 오류 메시지는 구현하지 않는다.
- [ ] Jetson에서 확인할 Python·OpenCV(GStreamer 지원)·MediaPipe·GUI 의존성 점검 절차를 적는다.
- [x] 원본 640×480 프레임을 시계방향 90° 회전한 480×640 세로 영상과 같은 너비의 상하 정보 띠를 한 장으로 합쳐 `mp_hand.py`와 같은 `cv2.imshow()` 창 하나에 표시하고, 한글은 Pillow·한글 폰트로 그리는 방식을 정한다. 당시 `portrait_ui_mockup.png`를 배치 예시로 사용했으며, 이후 손 관측 단순화에 따라 현재 화면 기준에서는 제외했다.
- [ ] 프로젝트에 한글 폰트를 포함하고 로딩 경로·누락 오류를 구현한다. Jetson에서 Pillow 설치, 글자 표시, 최종 창 크기와 프레임률을 확인한다.
- [ ] 영상·정보 띠를 합친 화면을 실제 게임 루프에서 창 하나에 출력하고, 손·공 좌표가 회전된 영상의 영역 경계와 일치하는지 확인한다.

## 단계 1 — 촬영 환경 및 실행 경로

- [ ] Jetson의 정확한 모델을 확인한다. USB 카메라의 장치 경로와 실제 지원 형식을 기록한다.
- [ ] `2026.10.18/`의 `v4l2src device=/dev/video0` 파이프라인으로 프레임을 읽고 종료·재시작을 확인한다. 실패하면 현장 장치 경로·형식에 맞게 수정한다.
- [ ] 같은 높이의 신발 상자 2개 안쪽 바닥에 각각 500 mL 생수병을 두고, 나무젓가락 2개를 가로로 고정해 렌즈가 아래를 향하는 거치대를 조립한다(사용자 계획, 2026-10-21).
- [ ] 카메라 본체와 젓가락 양 끝을 고정하고, 렌즈 시야·가로대 처짐·상자 기울어짐·케이블 당김·낙하 위험을 확인한다.
- [ ] Jetson을 거치대 오른쪽의 단단하고 평평한 책상 면에 두고 냉각부·전원선 공간과 USB 선 길이를 확인한다.
- [ ] 원본 화면의 왼쪽 종이컵 3개(출발)·중앙(제시)·오른쪽(손 대기)이 한 프레임에 들어오게 한다. 시계방향 회전 후 화면 위·중앙·아래 순서인지 확인하고, 컵과 공이 구르지 않게 한다.
- [ ] 빨강·파랑 도색 공을 준비하고 초록 공을 확보한다. 세 색과 배경·컵의 대비 및 반사를 촬영 화면에서 확인한다.
- [ ] 실제 처리 프레임률과 영상 지연을 측정해 0.15초 간격·0.4초 판정의 실현 가능성을 확인한다. 첫 시연은 라운드마다 10초 고정으로 진행하고 실제 플레이 시간을 기록한 뒤 단축 여부를 판단한다.
- [ ] 손바닥을 살짝 오므려 각 손에 공을 하나씩 올린 시연 장면을 촬영한다. 손가락 모양과 무관하게 제시 공 2개·양손의 손바닥 부근·레이블과 출발 영역의 남은 공 1개가 동시에 보이며 0.4초·4프레임 이상 연속 판정되는지 확인한다. 불가능하면 공 위치·카메라 높이·손 위 공 후보 판정 규칙을 조정한다.

## 단계 2 — 관측 기능

- [ ] 색별 공의 마스크·외곽선·중심을 표시한다.
- [ ] 실물 영상에서 색 마스크의 공 검출 성능과 블러 적용 효과를 확인한다. 마스크가 안정적이면 CLAHE는 구현·적용하지 않고, 생략 이유를 구현 후 README에 기록한다.
- [ ] 이미지 조정·색공간 변환·Image Enhancement·필터링·색상 분할·외곽선·객체 추적·손 인식이 **최종 실행 경로에서 실제 사용됨**을 코드와 시연으로 확인한다. 비활성화된 처리만 문서에 적고 활용했다고 주장하지 않는다.
- [ ] 손목(0)과 손가락 뿌리(5·9·13·17)로 양손의 `palm_box`(10% 여유)를 만들고 물리적 왼손·오른손 레이블을 확인한다. 손바닥을 오므린 자세에서도 손바닥 상자·공 색·공이 올라온 손이 관측되는지 기록한다. 여유값은 현장 보정 대상이며 손가락 펴짐·각도는 채점하지 않는다.
- [ ] 좌우 반전 설정을 바꿔도 화면 표시와 판정이 일치하도록 보정한다.
- [ ] 양손을 교차하거나 회전하고, 손을 가렸다 다시 보여주어 물리적 왼손·오른손 레이블이 유지되는지 확인한다.
- [ ] 손의 왼손·오른손 분류 점수를 실제 영상에서 기록하고, 0.70 임계값에서 레이블 누락·좌우 오류가 발생하는지 확인해 필요하면 조정한다.
- [ ] 빨강·초록·파랑 공마다 OpenCV `cv2.KalmanFilter`를 만들고 실제 검출 시 보정, 가림 시 예측, 0.5초 후 `lost`, 재검출 시 재연결을 확인한다.
- [ ] 실제 검출 공과 예측 공을 구별해 표시하고, 예측만 된 공은 채점·손 위 공 후보 판정·준비 확인에 쓰지 않는다.
- [ ] 공별 검은색 바깥 테두리와 해당 공 색의 가는 안쪽 외곽선을 표시한다. 화면 위에는 문제·시간, 아래에는 점수·기회·상태를 표시한다.

## 단계 3 — 게임 기능

- [ ] 공 3색 중 두 색의 좌우 손 문제를 생성한다.
- [ ] 매 문제의 선택되지 않은 한 색을 `남은 공`으로 기록하고, 채점 프레임마다 그 공이 실제 검출되어 출발 영역 안에 있는지 확인한다. Kalman 예측 위치는 잔류 확인에 사용하지 않는다.
- [ ] `SETUP → READY → COUNTDOWN → ACTIVE → RESULT_SUCCESS/RESULT_WRONG/RESULT_TIMEOUT → RESET → SUMMARY` 흐름과 입력 장애 시 `PAUSED`를 구현한다.
- [ ] 공의 실제 검출 중심이 제시 영역과 해당 손의 `palm_box` 안에 들어오는지로 손 위의 공 후보를 판정하고, 상자 겹침·복수 공은 보류한다. 0.4초·최소 4프레임·프레임 간격 0.15초의 정답/색 오답 판정을 구현한다. 손가락 모양은 판정에 사용하지 않는다. 순수 판정은 위 단계 기록을 따르며 이 항목은 실제 관측 연결까지 포함한다.
- [ ] 손·공 누락과 손 위 공 후보의 모호함을 즉시 오답으로 처리하지 않고, 양손에 실제 관측 공이 하나씩 명확히 보이는 완성 자세에서만 색 오답 연속 시간을 센다.
- [ ] 준비 중에는 공 3개와 **양손이 대기 영역에 0.5초** 보일 때만 카운트다운을 시작하며, 조건이 깨지면 READY로 돌아간다.
- [ ] 정답·오답·시간 초과 결과를 설정값 1.5초 표시하고, 기회가 남으면 문제를 지운 뒤 `다음 라운드를 위해 공을 제자리에 두고 손은 손 대기 영역 안에서 대기하세요.`를 표시한다. 공 3개가 출발 영역에 실제로 보이고 양손이 대기 영역에 있으며 제시 영역이 비어 있는 상태가 0.5초 유지되기 전에는 다음 문제를 내지 않는다.
- [ ] 결과와 관계없이 매 라운드 3초 카운트다운을 적용한다. 공과 손의 준비 조건이 충족된 다음에만 카운트다운을 시작한다.
- [ ] `PAUSED`에서 복구하면 점수·기회·라운드 번호를 유지하고 재준비 뒤 GAME_RULES 3절 기준으로 문제를 다시 추첨한다.
- [ ] 모든 라운드에서 고정 10초 제한, 기회 3개, 성공 +1점, 오답 확정 또는 시간 초과 시 기회 -1, 기회 0일 때 최종 요약을 구현한다.
- [ ] 손·공 누락, 카메라 끊김, 재시작, 종료를 처리한다.

## 단계 4 — 검증 장면

각 장면을 실제 카메라에서 녹화하거나 재현하고 **예상 결과와 실제 결과**를 기록한다.

단, 표에서 ‘선택 사항’으로 표시한 장면은 필수 검증·완료 조건에서 제외한다.

| 장면 | 예상 결과 |
| --- | --- |
| 왼손 초록·오른손 빨강 문제에 맞게 제시 | 0.4초 확인 뒤 +1점, 반응 시간 기록 |
| 두 공을 반대 손에 완성된 자세로 0.4초 제시 | 오답 확정, 점수 변화 없음, 기회 -1 |
| 두 손과 공 색이 맞고 손가락 일부를 굽힌 채 0.4초 제시 | 다른 조건이 충족되면 정답, +1점 |
| 지정 공 2개를 맞게 제시하고 남은 공 1개가 출발 영역에 실제로 보임 | 다른 조건도 충족되면 정답, +1점 |
| 지정 공 2개를 맞게 제시했지만 남은 공이 가려져 보이지 않음 | 정답·오답 보류, 타이머 계속 진행 |
| 지정 공 2개를 맞게 제시하고 남은 공이 출발 영역 밖에 명확히 보임 | 완성 자세와 0.4초·4프레임 확인 후 오답, 기회 -1 |
| 한 손 또는 공 하나만 보임 | 미완료 표시, 즉시 기회 차감 없음 |
| 다른 색 공이 한 손의 작은 `palm_box`에 추가로 들어옴 | 한 손에 공 2개 후보로 모호함 표시, 정답·오답 보류 |
| 두 공을 실제로 한 손바닥 위에 놓음 | 현재 규칙으로 안정적으로 구별할 수 있는지 기록; 구별 가능하면 오답 조건 추가 검토 |
| 두 손이 겹쳐 손 위 공 후보를 구분하기 어려움 | 보류, 점수 없음 |
| 공이 손에 잠깐 가려짐 | 예측 위치 표시 가능, 가린 구간은 채점 안 함 |
| 공이 0.5초 넘게 가려지거나 화면 밖으로 나감 | 위치 표시 중단·`lost`; 다시 실제 검출되면 재연결 또는 새로 초기화 |
| 손으로 공을 감싸 공 색이 보이지 않음 | 공 관측 누락으로 판정 보류, 즉시 기회 차감 없음 |
| 공을 옮기는 도중 틀린 색이 잠깐 손 영역에 들어옴 | 오답 확정 없음 |
| 손 옆 탁자 공의 손 위 후보 오판 확인 (선택 사항) | 사용자가 필수 검증에서 제외한 시나리오이며, 구현·제출의 필수 완료 조건으로 삼지 않음 |
| 준비 중 한 손이 대기 영역 밖에 있음 | 카운트다운 시작 안 함 |
| 오답 프레임 사이에 0.15초 초과 공백 | 오답 연속 기록 초기화, 즉시 기회 차감 없음 |
| 제한 시간 직전에 카메라가 멈춰 0.5초 이상 중단 | 시간 초과 확정 보류 후 시도 무효, 기회 유지 |
| 올바른 색을 짧게 보였다가 숨김 | 연속 관측 조건 미달이면 점수 없음 |
| 10초 경과, 기회가 남음 | 점수 변화 없음, 기회 -1, 다음 라운드 준비 |
| 세 번째 오답 또는 시간 초과 | 기회 0, 한 판 종료, 최종 점수 표시 |
| 정답 성공 | +1점, 기회 유지, 다음 라운드 준비 |
| 정답·오답·시간 초과 후 공이나 손이 제자리로 돌아오지 않음 | 결과 1.5초 표시 후 준비 안내 유지, 다음 문제·카운트다운 시작 안 함 |
| 공 3개와 양손이 제자리로 돌아와 0.5초 유지됨 | 3초 카운트다운 뒤 새 문제 표시 |
| `PAUSED` 중단 문제와 복구 직후 추첨 결과 비교 | 6가지 조합 전체에서 다시 추첨하며 같은 조합도 가능. 점수·기회·라운드 번호는 유지 |
| `ACTIVE`에서 카메라 입력이 연속 0.5초 이상 중단 | 미완료 시도 무효, 점수·기회 유지, 입력 회복 후 재준비 |
| `ACTIVE`에서 카메라 입력이 0.5초 미만 중단 후 회복 | 라운드 무효 없음, 판정 연속 기록 초기화, 10초 타이머는 계속 진행 |
| 준비·카운트다운 중 입력 실패 또는 준비 관측 간격 0.15초 초과 | 준비 기록 초기화, 카운트다운 취소 후 재준비; 0.5초 이상 입력 공백이면 입력 회복까지 대기 |
| 결과 확정 후 카메라 입력 중단 | 확정 점수·기회·시도 기록 보존, 기회가 남으면 재준비 단계에서 복구 대기 |
| 공 3개를 출발 영역 안의 다른 위치에 반환 | 색별 유일한 실제 검출이면 원래 컵 위치와 무관하게 공 준비 조건 충족 |
| `r`, `q` 입력 | 각각 새 판 시작(점수 0·기회 3), 정상 종료 |

## 단계 5 — 제출 및 발표

- [ ] 제공된 [채점 기준](project_grading_criteria.png)과 README 형식에 맞춰 필수 `파일 구조`·`실행 방식`에 실제 파일·의존성·실행 명령을 적고, 기타 참고 사항에 주요 코드의 설계 이유·검증 결과·AI 활용과 본인 기여를 사실대로 기록한다. README 외 추가 제출 요건은 별도 안내에서 확인한다.
- [ ] 구현한 기능과 확장 아이디어를 분리해 기록한다.
- [ ] AI 활용 내용과 본인이 직접 설계·수정·실험한 내용을 사실대로 기록한다.
- [ ] 실제 Jetson에서 여러 라운드를 연속 시연하고 오검출·누락 사례를 정리한다.
- [ ] 발표에서 실제 관측과 Kalman 예측의 차이, 채점 기준, 한계를 설명한다.
