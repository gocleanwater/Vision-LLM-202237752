"""카메라 없이 관측 판정과 게임의 시간 흐름을 확인한다."""

import random
import math

# 게임에서 사용할 색깔과 시간 설정 (시간은 전부 초 단위!)
COLORS = ("red", "green", "blue")
MIN_HAND_CONFIDENCE = 0.70  # 왼손/오른손 분류 점수가 이 값 이상이어야 사용
READY_DURATION = 0.5  # 준비 자세를 유지해야 하는 시간
MAX_READY_GAP = 0.35  # Jetson 실측 처리 간격을 포함하는 준비·판정 프레임 최대 간격
COUNTDOWN_DURATION = 3.0  # 문제를 보여주기 전 카운트다운 시간
FLOAT_TIME_TOLERANCE = (
    0.000000001  # 소수 계산 오차 때문에 정확히 0.4초인 것을 부족하다고 판단하지 않도록!
)
JUDGMENT_DURATION = 0.4  # 정답 또는 오답 자세를 유지해야 하는 시간
MIN_JUDGMENT_FRAMES = 4  # 시간만 채우면 안 되고, 확인한 프레임도 최소 4개여야 함
ACTIVE_TIME_LIMIT = 10.0  # 한 문제의 제한 시간
STARTING_CHANCES = 3  # 한 판을 시작할 때 주는 기회 수
RESULT_DISPLAY_DURATION = 1.5  # 정답/오답/시간 초과 결과를 보여주는 시간
INPUT_PAUSE_DURATION = 0.5  # 정상 입력이 이 시간 이상 끊기면 PAUSED로 이동


# 점이 박스 안에 있는 지를 나타내는 함수 (안에 있으면 true, 없으면 false)
def point_in_box(point, box):
    x, y = point  # 점의 위치를 언팩킹
    box_x_min, box_y_min, box_x_max, box_y_max = box  # box의 범위를 보기 위해 언팩킹
    return (
        box_x_min <= x <= box_x_max and box_y_min <= y <= box_y_max
    )  # 해당 점이 박스 안에 있냐?


# 프레임을 보고 준비 상태와 손별 공 색을 확인하는 함수
def inspect_frame(frame, regions, question=None):
    # 연속되는 프레임 중 전달받은 한 프레임만 보고 판단한다.
    # correct: 정답 자세일 때
    # wrong: 오답 자세일 때
    # hold: 보류
    result = {
        "ready": False,
        "judgment": "hold",
        "reason": "",
        "hand_colors": {"left": None, "right": None},
        "remaining_ball": None,  # 문제 전에는 None, 문제 중에는 남은 공의 위치 안내
    }

    balls = {}
    for color in COLORS:  # 색깔을 하나하나씩 뽑기
        # 해당 색깔 중 실제로 검출됐고 믿고 사용할 수 있는 공만 모으기 (예측 위치는 제외!)
        candidates = [
            ball
            for ball in frame.balls
            if ball.color == color and ball.observed and ball.reliable
        ]
        if len(candidates) == 1:
            balls[color] = candidates[0]

    # 손이 가려져 채점을 못 해도 남은 공의 위치는 따로 안내한다.
    if question is not None:
        remaining_color = next(color for color in COLORS if color not in question)
        remaining_ball = balls.get(remaining_color)
        if remaining_ball is None:
            result["remaining_ball"] = "남은 공 확인 필요"
        elif point_in_box(remaining_ball.center, regions["start"]):
            result["remaining_ball"] = "남은 공 출발 영역 확인"
        else:
            result["remaining_ball"] = "남은 공 위치 오류"

    if len(balls) != len(COLORS):
        result["reason"] = "공 준비 필요" if question is None else "공 확인 필요"
        return result

    hands = {}
    for side in ("left", "right"):
        # 화면의 왼쪽/오른쪽 위치가 아니라, 보정된 실제 왼손/오른손으로 찾기
        candidates = [hand for hand in frame.hands if hand.physical_hand == side]
        if not candidates:
            result["reason"] = "다른 손을 보여주세요"
            return result
        # 손이 없거나 같은 손이 여러 개로 잡히거나, 분류 점수가 낮으면 아직 판단하지 않음
        if len(candidates) != 1 or candidates[0].confidence < MIN_HAND_CONFIDENCE:
            result["reason"] = "손 구분 확인 중"
            return result
        hands[side] = candidates[0]

    # ============ 라운드 시작 전 Ready 상태 확인 ============ #

    # 라운드 시작 전 색깔 공들의 준비 상태 확인
    # all()은 안에 있는 조건이 전부 True일 때만 True! values()는 딕셔너리의 값들을 가져옴
    all_balls_at_start = all(
        point_in_box(ball.center, regions["start"]) for ball in balls.values()
    )
    # 라운드 시작 전 양손의 준비 상태 확인
    both_hands_waiting = all(
        point_in_box(hand.palm_center, regions["waiting"]) for hand in hands.values()
    )
    # 라운드 시작 전 제시 영역에 공과 손이 없는지 확인
    # any()는 하나라도 True이면 True이므로, not any()로 하나도 없는지 확인
    presentation_empty = not any(
        ball.observed and point_in_box(ball.center, regions["presentation"])
        for ball in frame.balls
    ) and not any(
        point_in_box(hand.palm_center, regions["presentation"]) for hand in frame.hands
    )
    result["ready"] = all_balls_at_start and both_hands_waiting and presentation_empty
    # 문제를 전달하지 않았으면 준비 상태만 확인하고 여기서 끝냄 (아래 정답/오답 판단은 하지 않기)
    if question is None:
        result["reason"] = "준비 완료" if result["ready"] else "공과 손 준비 필요"
        return result

    # ============ 라운드 시작 후 정답/오답 판단 ============ #

    # 양손의 손바닥 중심이 모두 제시 영역 안에 있어야 정답/오답 판단을 시작
    if not all(
        point_in_box(hand.palm_center, regions["presentation"])
        for hand in hands.values()
    ):
        result["reason"] = "양손을 제시 영역에 보여주세요"
        return result

    # 왼손과 오른손 위에 올라온 것으로 보이는 공 색깔을 각각 모으기
    ball_colors_on_hands = {"left": [], "right": []}

    # 공이 제시 영역 안에 있는지 확인하고, 어느 손 위에 있는지 확인
    for color, ball in balls.items():  # 색과 해당 공을 함께 꺼내기
        if not point_in_box(ball.center, regions["presentation"]):
            continue  # 제시 영역 밖의 공은 건너뛰고 다음 공 확인
        # 공 중심이 어느 손의 손바닥 상자 안에 있는지 찾기
        candidate_hands = [
            side
            for side, hand in hands.items()
            if point_in_box(ball.center, hand.palm_box)
        ]
        if len(candidate_hands) > 1:
            # 공 하나가 양손 상자에 모두 들어가면 어느 손의 공인지 알 수 없으므로 보류
            result["reason"] = "두 손을 떨어뜨려 주세요"
            return result
        for side in candidate_hands:
            # 손바닥 상자 안에 들어온 공이므로 해당 손의 공 후보에 추가
            ball_colors_on_hands[side].append(color)

    reason = ""
    has_multiple_balls = False  # 여러 개로 보이면 기존처럼 손별 색은 아직 저장하지 않기

    for colors in ball_colors_on_hands.values():
        ball_count = len(colors)  # 해당 손 위에 올라온 공 후보 개수

        if ball_count > 1:
            reason = "손 위의 공이 여러 개입니다."
            has_multiple_balls = True
            break  # 여러 개 보이는 상황을 우선 안내하고 확인 종료
        elif ball_count == 0:
            reason = "공이 확인되지 않습니다. 손에 있는 공을 보여주세요."
            # 다른 손에 공이 여러 개일 수도 있으므로 계속 확인

    # 여러 개로 보이는 손이 없으면 확인한 색 저장 (한 손의 공이 안 보여도 반대 손의 색은 유지!)
    if not has_multiple_balls:
        for side, colors in ball_colors_on_hands.items():
            if len(colors) == 1:
                result["hand_colors"][side] = colors[0]

    if reason:
        result["reason"] = reason
        return result  # 안내할 문제가 있으면 판정 보류

    remaining_at_start = point_in_box(balls[remaining_color].center, regions["start"])
    colors_match = (
        ball_colors_on_hands["left"][0],
        ball_colors_on_hands["right"][0],
    ) == question  # 문제도 (왼손 색, 오른손 색) 순서이므로 순서까지 같아야 함
    # 여기까지 왔으면 양손의 공이 하나씩 보이는 완성 자세! 이제 남은 공 위치와 손별 색 확인
    if not remaining_at_start:
        result["judgment"] = "wrong"
        result["reason"] = "남은 공 위치 오류"
    elif not colors_match:
        result["judgment"] = "wrong"
        result["reason"] = "손별 공 색 오류"
    else:
        result["judgment"] = "correct"
        result["reason"] = "정답 자세"
    return result


# =========== 게임 상태를 관리하는 함수들 ============ #


# 준비부터 정답/오답 결과까지 기억할 값들을 딕셔너리로 만드는 함수
def create_game_state():
    return {
        "status": "SETUP",  # 처음에는 설정된 영역과 정상 프레임을 기다리는 상태
        "ready_started_at": None,  # 준비 자세가 시작된 첫 시각
        "last_ready_observed_at": None,  # 준비 자세를 마지막으로 확인한 시각
        "processed_frame_ids": {},  # 이번 라운드에서 판정한 번호: 목록 전체를 검색하지 않도록 딕셔너리 사용
        "countdown_started_at": None,  # 3초 카운트다운이 시작된 시각
        "question": None,  # 현재 문제 (왼손 색, 오른손 색)
        "problem_presented_at": None,  # 문제가 포함된 화면을 실제로 출력한 시각
        "current_judgment": None,  # 지금 이어서 확인 중인 자세: correct 또는 wrong
        "judgment_started_at": None,  # 해당 자세를 처음 확인한 시각
        "last_judgment_observed_at": None,  # 해당 자세를 마지막으로 확인한 시각
        "judgment_frame_count": 0,  # 해당 자세를 연속으로 확인한 프레임 수
        "reaction_time": None,  # 문제 표시부터 첫 정답 자세까지 걸린 시간 (성공했을 때만 기록)
        "result_started_at": None,  # 정답/오답/시간 초과가 확정된 시각
        "result_reason": None,  # 어떤 이유로 해당 결과가 나왔는지
        "score": 0,  # 성공할 때마다 1점씩 증가
        "chances": STARTING_CHANCES,  # 오답이나 시간 초과 때 1개씩 감소
        "completed_attempts": 0,  # 결과가 확정된 시도 수
        "reaction_times": [],  # 성공한 시도의 반응 시간만 모은 목록
        "last_normal_input_at": None,  # 영상과 모델 처리가 마지막으로 정상 완료된 시각
        "input_frame_ids": {},  # 이번 판의 정상 입력 번호. 라운드가 끝나도 중복 확인에 사용!
        "input_gap_started_at": None,  # 현재 이어지는 입력 공백이 시작된 시각
        "input_error_reason": None,  # 현재 입력 문제: read_failure, no_input, model_error
        "paused_from_status": None,  # PAUSED 직전에 어떤 게임 상태였는지 기억
        "retrying_round": False,  # 장애로 무효가 된 현재 문제를 다시 준비하는지
    }


# 설정된 영역과 첫 정상 프레임을 받았을 때 준비 상태로 바꾸는 함수
def complete_setup(game_state):
    game_state["status"] = "READY"


# 준비 조건이 깨지면 준비 시간과 카운트다운을 지우고 READY로 돌아가는 함수
def reset_preparation(game_state):
    game_state["status"] = "READY"
    game_state["ready_started_at"] = None  # 준비가 시작된 첫 시각
    game_state["last_ready_observed_at"] = None  # 준비를 마지막으로 확인한 시각
    game_state["countdown_started_at"] = None  # 카운트다운이 시작된 시각
    game_state["question"] = None  # 이미 문제를 골랐어도 아직 시작 전이므로 취소


# 프레임을 받을 때마다 준비 자세가 이어지는지, 카운트다운이 끝났는지 확인하는 함수
def update_preparation(game_state, frame, regions, now, frame_result=None):
    # now는 현재 프레임의 관측 처리가 끝난 시각
    current_status = game_state["status"]
    if current_status not in ("READY", "COUNTDOWN"):
        return

    # 마지막 준비 확인 이후 얼마나 지났는지 계산 (0.35초보다 길면 계속 준비했다고 볼 수 없으니까)
    last_ready_observed_at = game_state["last_ready_observed_at"]
    ready_gap_too_long = False
    if last_ready_observed_at is not None:
        time_since_last_ready = now - last_ready_observed_at
        ready_gap_too_long = (
            time_since_last_ready > MAX_READY_GAP + FLOAT_TIME_TOLERANCE
        )

    # 같은 프레임을 다시 받았으면 준비 확인에 또 쓰지 않기
    # 다만 마지막 준비 확인 이후 너무 오래 지났으면 준비 기록은 지워야 함!
    if frame.frame_id in game_state["processed_frame_ids"]:
        if ready_gap_too_long:
            reset_preparation(game_state)
        return

    game_state["processed_frame_ids"][frame.frame_id] = True
    if frame_result is None:
        frame_result = inspect_frame(frame, regions)
    is_ready = frame_result["ready"]  # 한 프레임 결과 중 준비 여부만 꺼내기

    # ============ READY: 준비 자세가 0.5초 이어지는지 확인 ============ #
    # 10.0 → 10.1 → 10.2초 순서로 확인하면 시작은 10.0초 그대로!
    # 마지막 확인 시각만 10.1, 10.2초로 바뀌어야 전체 준비 시간을 계산할 수 있음
    if current_status == "READY":
        if not is_ready:
            # 공이나 손이 준비 위치를 벗어나면 이전에 기다린 시간은 지우기
            game_state["ready_started_at"] = None
            game_state["last_ready_observed_at"] = None
            return

        if game_state["ready_started_at"] is None or ready_gap_too_long:
            # 처음 준비했거나 중간 간격이 너무 길면 지금부터 다시 0.5초 세기
            game_state["ready_started_at"] = now
        game_state["last_ready_observed_at"] = now

        ready_duration = (
            now - game_state["ready_started_at"]
        )  # 현재 시각 - 시작 시각 = 준비한 시간
        if ready_duration + FLOAT_TIME_TOLERANCE >= READY_DURATION:
            game_state["status"] = "COUNTDOWN"
            game_state["countdown_started_at"] = now
        return

    # ============ COUNTDOWN: 준비 자세를 유지하면서 3초 기다리기 ============ #
    if current_status == "COUNTDOWN":
        if not is_ready or ready_gap_too_long:
            reset_preparation(game_state)
            if is_ready:
                # 간격 때문에 취소됐어도 지금 자세는 준비 상태라면, 현재 프레임부터 다시 세기
                game_state["ready_started_at"] = now
                game_state["last_ready_observed_at"] = now
            return

        game_state["last_ready_observed_at"] = now
        countdown_duration = now - game_state["countdown_started_at"]
        countdown_finished = (
            countdown_duration + FLOAT_TIME_TOLERANCE >= COUNTDOWN_DURATION
        )
        if countdown_finished and game_state["question"] is None:
            # sample()은 세 색 중 서로 다른 두 색을 순서도 무작위로 뽑아 리스트로 반환!
            # tuple()로 (왼손 색, 오른손 색)으로 저장하므로 (파랑, 빨강)도 나올 수 있음
            # 이미 골랐으면 매 프레임 다시 뽑지 않기
            game_state["question"] = tuple(random.sample(COLORS, 2))


# 문제 화면을 실제로 출력했을 때 문제 시작 시각을 기록하는 함수
def mark_problem_presented(game_state, presented_at):
    if game_state["status"] != "COUNTDOWN" or game_state["question"] is None:
        # 카운트다운 중이고 문제도 골라진 경우에만 시작 (이미 시작한 문제 시각은 덮어쓰지 않기)
        return
    last_ready_observed_at = game_state["last_ready_observed_at"]
    # 문제를 골랐어도 화면 출력이 늦어졌으면 그 사이 준비가 유지됐는지 알 수 없으므로 다시 준비
    if (
        last_ready_observed_at is None
        or presented_at - last_ready_observed_at > MAX_READY_GAP + FLOAT_TIME_TOLERANCE
    ):
        reset_preparation(game_state)
        return
    game_state["status"] = "ACTIVE"
    game_state["problem_presented_at"] = (
        presented_at  # 문제를 고른 시각이 아니라 화면에 낸 시각부터 10초!
    )


# 이어서 확인하던 정답/오답 자세의 시간과 프레임 수를 지우는 함수
def reset_judgment(game_state):
    game_state["current_judgment"] = None
    game_state["judgment_started_at"] = None
    game_state["last_judgment_observed_at"] = None
    game_state["judgment_frame_count"] = 0


# 문제를 끝내고 결과 상태, 확정 시각, 이유를 저장하는 함수
def finish_active(game_state, result_status, now, reason):
    # ACTIVE가 아니면 이미 결과를 반영한 것이므로 점수와 기회를 다시 바꾸지 않기
    if game_state["status"] != "ACTIVE":
        return

    game_state["status"] = result_status
    game_state["result_started_at"] = now
    game_state["result_reason"] = reason
    game_state["completed_attempts"] += 1

    if result_status == "RESULT_SUCCESS":
        game_state["score"] += 1
        game_state["reaction_times"].append(game_state["reaction_time"])
    else:
        game_state["chances"] -= 1


# 한 라운드의 임시 값을 지우고 다음 라운드 준비 상태로 돌아가는 함수
def reset_round(game_state):
    reset_preparation(game_state)
    game_state["processed_frame_ids"] = {}
    game_state["problem_presented_at"] = None
    reset_judgment(game_state)
    game_state["reaction_time"] = None
    game_state["result_started_at"] = None
    game_state["result_reason"] = None
    game_state["retrying_round"] = False


# 정상 입력이 끊겼을 때 준비 또는 정답/오답의 연속 기록을 지우는 함수
def reset_input_continuity(game_state):
    if game_state["status"] in (
        "READY",
        "COUNTDOWN",
    ):  # 라운드 시작 전일 때는 준비 상태를 초기화
        reset_preparation(game_state)
    elif (
        game_state["status"] == "ACTIVE"
    ):  # 라운드 진행 중일 때는 정답/오답 판단 기록을 초기화
        reset_judgment(game_state)


# 입력 장애 상태로 들어가되 점수·기회·완료 기록은 바꾸지 않는 함수
def pause_for_input(game_state, reason):
    previous_status = game_state["status"]
    result_statuses = ("RESULT_SUCCESS", "RESULT_WRONG", "RESULT_TIMEOUT")

    # 확정 결과와 요약 화면은 입력 장애가 생겨도 그대로 유지
    if previous_status in result_statuses or previous_status == "SUMMARY":
        return
    if previous_status == "PAUSED":
        return

    if previous_status in ("READY", "COUNTDOWN"):
        reset_preparation(game_state)
    elif previous_status in ("ACTIVE", "RESET"):
        # 미완료 ACTIVE 문제 또는 끝난 라운드의 임시 값만 지우기
        reset_round(game_state)

    game_state["status"] = "PAUSED"
    if previous_status == "ACTIVE":
        game_state["retrying_round"] = True
    game_state["paused_from_status"] = previous_status
    game_state["input_error_reason"] = reason


# 정상 입력이 돌아오면 장애 전 상태에 맞는 준비 위치로 돌아가는 함수
def recover_input(game_state):
    if game_state["status"] != "PAUSED":
        return

    if game_state["paused_from_status"] == "SETUP":
        game_state["status"] = "SETUP"
    else:
        game_state["status"] = "READY"
    game_state["paused_from_status"] = None


# 카메라·모델 입력 상태를 보고 짧은 공백과 PAUSED 전환을 처리하는 함수
def update_input_state(game_state, input_status, now, frame_id=None):
    last_normal_at = game_state["last_normal_input_at"]
    gap_started_at = game_state["input_gap_started_at"]

    # 이미 본 프레임을 또 읽을 때: 이는 입력이 없다고 봐야 한다.
    if (
        input_status == "frame"
        and frame_id is not None
        and (
            frame_id in game_state["input_frame_ids"]
            or frame_id in game_state["processed_frame_ids"]
        )
    ):
        input_status = "no_input"

    # ========== 정상 입력이 들어왔을 때("frame"): 공백 시간과 PAUSED 전환 확인 ============ #
    if input_status == "frame":
        # 별도 실패 신호가 없어도 정상 프레임 사이가 길면 그 공백을 확인
        if gap_started_at is None:
            gap_started_at = last_normal_at

        if game_state["status"] == "PAUSED":
            recover_input(game_state)
        elif gap_started_at is not None:
            gap_duration = now - gap_started_at
            if gap_duration > MAX_READY_GAP + FLOAT_TIME_TOLERANCE:
                reset_input_continuity(game_state)
            if gap_duration + FLOAT_TIME_TOLERANCE >= INPUT_PAUSE_DURATION:
                pause_for_input(game_state, "no_input")
                recover_input(game_state)

        # 정상 처리된 프레임부터는 새 공백을 다시 세므로 떨어진 공백을 합하지 않음
        game_state["last_normal_input_at"] = now
        if frame_id is not None:
            game_state["input_frame_ids"][frame_id] = True
        game_state["input_gap_started_at"] = None
        game_state["input_error_reason"] = None
        return

    # =========== 정상 입력이 끊겼을 때("no_input", "read_failure", "model_error"): 공백 시간과 PAUSED 전환 확인 ============ #
    # 공백 시작 시각 기록 (공백 시작 기록이 없을 때)
    if gap_started_at is None:
        gap_started_at = last_normal_at if last_normal_at is not None else now
        game_state["input_gap_started_at"] = gap_started_at
    # 모델 오류는 다른 입력 문제보다 우선하며 공백 시간을 기다리지 않고 즉시 처리
    if input_status == "model_error":
        game_state["input_error_reason"] = "model_error"
        reset_input_continuity(game_state)
        pause_for_input(game_state, "model_error")
        return

    # 모델 오류가 이미 발생했다면, 이후의 no_input이나 read_failure로 원인을 바꾸지 않음
    # input_status는 이번 입력, input_error_reason은 정상 입력이 돌아올 때까지 기억할 오류 원인!
    # 짧은 공백이나 결과 표시 중에도 기록하므로 PAUSED에서만 쓰는 값은 아니다.
    if game_state["input_error_reason"] != "model_error":
        game_state["input_error_reason"] = input_status

    gap_duration = now - gap_started_at
    if (
        input_status == "read_failure"
        or gap_duration > MAX_READY_GAP + FLOAT_TIME_TOLERANCE
    ):
        reset_input_continuity(game_state)

    if gap_duration + FLOAT_TIME_TOLERANCE >= INPUT_PAUSE_DURATION:
        pause_for_input(game_state, input_status)


# 결과를 1.5초 보여준 뒤 RESET 또는 SUMMARY로 이동하는 함수
def update_result(game_state, now):
    result_statuses = ("RESULT_SUCCESS", "RESULT_WRONG", "RESULT_TIMEOUT")

    if game_state["status"] in result_statuses:
        result_duration = now - game_state["result_started_at"]
        if result_duration + FLOAT_TIME_TOLERANCE < RESULT_DISPLAY_DURATION:
            return

        if game_state["chances"] == 0:
            game_state["status"] = "SUMMARY"
        else:
            game_state["status"] = "RESET"
            gap_started_at = game_state["input_gap_started_at"]
            input_gap_is_long = (
                gap_started_at is not None
                and now - gap_started_at + FLOAT_TIME_TOLERANCE >= INPUT_PAUSE_DURATION
            )
            # 결과 표시 중 생긴 입력 문제가 아직 끝나지 않았으면 준비 전에 복구를 기다림
            if game_state["input_error_reason"] == "model_error" or input_gap_is_long:
                pause_for_input(game_state, game_state["input_error_reason"])
        return

    # RESET은 한 라운드 값을 정리하는 짧은 상태이며, 다음 호출에서 READY로 이동
    if game_state["status"] == "RESET":
        reset_round(game_state)


# 요약 화면에 필요한 점수, 시도 수, 성공 반응 시간 기록을 계산하는 함수
def get_summary(game_state):
    reaction_times = game_state["reaction_times"]
    average_reaction_time = None
    fastest_reaction_time = None

    if reaction_times:
        average_reaction_time = sum(reaction_times) / len(reaction_times)
        fastest_reaction_time = min(reaction_times)

    return {
        "score": game_state["score"],
        "completed_attempts": game_state["completed_attempts"],
        "average_reaction_time": average_reaction_time,
        "fastest_reaction_time": fastest_reaction_time,
    }


# 현재 상태와 관측 결과를 위·아래 정보 띠에 표시할 문장으로 바꾸는 함수
def get_screen_lines(game_state, now, frame_result=None):
    status = game_state["status"]
    color_names = {"red": "빨강", "green": "초록", "blue": "파랑"}
    top = ["컬러 볼 게임"]
    chances = game_state["chances"]
    icons = "●" * chances + "○" * (STARTING_CHANCES - chances)
    bottom = [
        f"점수 {game_state['score']} | 기회 {chances}/{STARTING_CHANCES} {icons}"
        f" | 라운드 {game_state['completed_attempts'] + 1}"
    ]
    status_names = {
        "SETUP": "설정 중",
        "READY": "준비 중",
        "COUNTDOWN": "시작 대기",
        "ACTIVE": "채점 중",
        "RESULT_SUCCESS": "정답",
        "RESULT_WRONG": "오답",
        "RESULT_TIMEOUT": "시간 초과",
        "RESET": "재준비",
        "PAUSED": "입력 복구 대기",
    }
    if status in status_names:
        bottom.append(f"상태: {status_names[status]}")
    last_normal_at = game_state["last_normal_input_at"]
    fresh_feedback = (
        last_normal_at is not None
        and now - last_normal_at <= MAX_READY_GAP + FLOAT_TIME_TOLERANCE
    )  # 마지막 관측 결과가 화면에 안내할 만큼 최근의 것인지 확인하는 Boolean 값
    question = game_state["question"]
    if question is not None and status in ("COUNTDOWN", "ACTIVE"):
        top = [
            f"내 왼손: {color_names[question[0]]} | 내 오른손: {color_names[question[1]]}"
        ]

    if status == "SETUP":
        bottom.append("게임 영역을 불러오는 중입니다.")
    elif status == "READY":
        if game_state["retrying_round"]:
            prefix = "문제를 다시 시작하려면"
        elif game_state["completed_attempts"]:
            prefix = "다음 라운드를 위해"
        else:
            prefix = "시작하려면"
        bottom.append(
            f"{prefix} 공을 출발 영역에 두고 손은 손 대기 영역 안에서 대기하세요."
        )
        if frame_result is not None and fresh_feedback:
            bottom.append(frame_result["reason"])
    elif status == "COUNTDOWN":
        if question is not None:
            top.append(f"남은 시간 {ACTIVE_TIME_LIMIT:.1f}초")
        else:
            elapsed = now - game_state["countdown_started_at"]
            remaining = max(1, math.ceil(COUNTDOWN_DURATION - elapsed))
            top.append(f"시작까지 {remaining}")
    elif status == "ACTIVE":
        elapsed = now - game_state["problem_presented_at"]
        remaining = max(0.0, ACTIVE_TIME_LIMIT - elapsed)
        top.append(f"남은 시간 {remaining:.1f}초")
        if frame_result is not None and fresh_feedback:
            bottom.append(frame_result["reason"])
            if (
                frame_result["remaining_ball"] is not None
                and frame_result["remaining_ball"] != frame_result["reason"]
            ):
                bottom.append(frame_result["remaining_ball"])
            colors = frame_result["hand_colors"]
            bottom.append(
                f"왼손 {color_names.get(colors['left'], '미확인')} | 오른손 {color_names.get(colors['right'], '미확인')}"
            )
        else:
            bottom.append("관측 갱신 대기")
    elif status == "RESULT_SUCCESS":
        top = ["정답!", f"게임 내 반응 시간 {game_state['reaction_time']:.2f}초"]
    elif status in ("RESULT_WRONG", "RESULT_TIMEOUT"):
        top = ["오답" if status == "RESULT_WRONG" else "시간 초과"]
        bottom.append(game_state["result_reason"] or "")
    elif status == "PAUSED":
        top = ["입력 장애 — 복구 대기"]
        reason = game_state["input_error_reason"]
        bottom.append(
            "모델 처리 오류 — 다음 정상 관측을 기다립니다."
            if reason == "model_error"
            else "카메라 입력을 확인하세요."
        )
    elif status == "SUMMARY":
        summary = get_summary(game_state)
        top = [f"최종 점수 {summary['score']} | 시도 {summary['completed_attempts']}"]
        average = summary["average_reaction_time"]
        if average is None:
            top.append("성공 반응 시간: 기록 없음")
        else:
            top.append(
                f"평균 {average:.2f}초 | 최단 {summary['fastest_reaction_time']:.2f}초"
            )
        bottom = ["한 판이 끝났습니다."]
    bottom.append("r: 새 판 | q: 종료")
    return top, bottom


# 입력 상태와 관측을 받아 기존 게임 함수들을 순서대로 호출하는 함수
def update_game(game_state, input_status, now, frame=None, regions=None):
    # 입력 감시는 먼저! 장애로 무효가 된 문제를 아래에서 채점하지 않도록 한다.
    frame_id = frame.frame_id if frame is not None else None
    is_new_frame = (
        input_status == "frame"
        and frame is not None
        and frame_id not in game_state["input_frame_ids"]
        and frame_id not in game_state["processed_frame_ids"]
    )
    update_input_state(game_state, input_status, now, frame_id)
    frame_result = None

    if is_new_frame and regions is not None:
        if game_state["status"] == "SETUP":
            complete_setup(game_state)
        # 결과 뒤 RESET에서는 이전 문제가 남아 있어도 준비 자세로 안내한다.
        question = game_state["question"] if game_state["status"] == "ACTIVE" else None
        frame_result = inspect_frame(frame, regions, question)
        update_preparation(game_state, frame, regions, now, frame_result)
        update_active(game_state, frame, regions, now, frame_result)

    # 새 영상이 없어도 확정 결과의 표시 시간은 계속 흐른다.
    update_result(game_state, now)
    return frame_result


# r 키로 새 판을 시작할 때 점수와 라운드 기록을 처음 값으로 되돌리는 함수
def restart_game(game_state):
    game_state.clear()
    game_state.update(create_game_state())


# 문제 진행 중 프레임을 보고 정답/오답 유지 시간과 제한 시간을 확인하는 함수
def update_active(game_state, frame, regions, now, frame_result=None):
    # ============ ACTIVE: 지금 들어온 프레임을 사용할 수 있는지 확인 ============ #
    if game_state["status"] != "ACTIVE":
        return
    if frame.frame_id in game_state["processed_frame_ids"]:
        # 같은 프레임을 또 받은 것은 새 입력이 아님! 프레임 수와 제한 시간 확인에 다시 쓰지 않기
        return

    game_state["processed_frame_ids"][frame.frame_id] = True
    deadline = (
        game_state["problem_presented_at"] + ACTIVE_TIME_LIMIT
    )  # 예: 10초에 문제 표시 → 20초가 제한 시각
    # read_at은 카메라에서 읽은 시각, now는 손과 공의 관측 처리가 끝난 시각
    if frame.read_at < game_state["problem_presented_at"]:
        # 문제 표시 전에 읽은 장면은 정답/오답 판단에 쓰면 안 됨! 다만 제한 시간이 지났는지는 확인 -> 오답이라고 판단하지 않도록
        if now + FLOAT_TIME_TOLERANCE >= deadline:
            finish_active(game_state, "RESULT_TIMEOUT", now, "시간 초과")
        return

    if frame_result is None:
        frame_result = inspect_frame(frame, regions, game_state["question"])
    judgment = frame_result[
        "judgment"
    ]  # 현재 한 프레임의 correct / wrong / hold 결과 꺼내기

    # ============ 같은 정답/오답 자세가 계속 이어지는지 확인 ============ #
    if judgment == "hold":
        # 손이나 공이 안 보이는 등 판단을 못 하면, 이전 자세가 계속 유지됐다고 볼 수 없으므로 지우기
        reset_judgment(game_state)
    else:  # 정답이나 오답이라면...(즉, 정답인지 오답인지 판단할 수 있는 자세라면)
        last_observed_at = game_state["last_judgment_observed_at"]
        # 마지막 유효 자세와 0.35초 넘게 떨어져 있으면 그 사이 자세를 모르므로 새로 세야 함
        gap_too_long = (
            last_observed_at is not None
            and now - last_observed_at > MAX_READY_GAP + FLOAT_TIME_TOLERANCE
        )
        changed_judgment = (
            judgment != game_state["current_judgment"]
        )  # 정답 ↔ 오답으로 바뀌었는지 확인

        if changed_judgment or gap_too_long:
            # 첫 자세이거나 판정이 바뀌거나 간격이 길면, 현재 프레임부터 1개로 다시 시작
            game_state["current_judgment"] = judgment
            game_state["judgment_started_at"] = now
            game_state["judgment_frame_count"] = 1
        else:
            # 같은 자세가 이어지면 시작 시각은 두고 프레임 수만 하나 늘리기
            game_state["judgment_frame_count"] += 1
        game_state["last_judgment_observed_at"] = now

    # ============ 0.4초와 최소 4프레임을 모두 채웠는지 확인 ============ #
    confirmed = False
    if game_state["judgment_started_at"] is not None:
        judgment_duration = now - game_state["judgment_started_at"]
        enough_time = judgment_duration + FLOAT_TIME_TOLERANCE >= JUDGMENT_DURATION
        enough_frames = game_state["judgment_frame_count"] >= MIN_JUDGMENT_FRAMES
        confirmed = (
            enough_time and enough_frames
        )  # 둘 다 만족해야 확정! 4프레임이어도 0.3초면 아직 부족

    # ============ 제한 시각 안에 자세가 확정됐으면 정답/오답 결과 저장 ============ #
    # 정확히 제한 시각에 확정된 자세까지 인정하므로 시간 초과 처리보다 먼저 확인
    within_deadline = now <= deadline + FLOAT_TIME_TOLERANCE
    if confirmed and within_deadline:
        if game_state["current_judgment"] == "correct":
            # 반응 시간은 첫 정답 자세까지! 자세가 맞는지 확인하느라 기다린 0.4초는 더하지 않음
            # 예: 문제 표시 10.0초, 첫 정답 자세 10.2초, 확정 10.6초 → 반응 시간은 0.2초
            game_state["reaction_time"] = (
                game_state["judgment_started_at"] - game_state["problem_presented_at"]
            )
            finish_active(game_state, "RESULT_SUCCESS", now, "정답")
        else:
            finish_active(game_state, "RESULT_WRONG", now, frame_result["reason"])
        return

    # 아직 확정되지 않았거나 확정된 시각이 제한 시각보다 늦으면 시간 초과
    if now + FLOAT_TIME_TOLERANCE >= deadline:
        finish_active(game_state, "RESULT_TIMEOUT", now, "시간 초과")
