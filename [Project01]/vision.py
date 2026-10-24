"""MediaPipe 손 결과와 색 마스크에서 게임 관측을 만든다."""

import cv2
import mediapipe as mp
import numpy as np
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

from contracts import Ball, Hand

HAND_MODEL_PATH = "../src/models/MediaPipe/hand_landmarker.task"

# 손바닥 상자를 사방으로 조금 넓히는 보정값(나중에 현장 가서 고쳐야 함.)
PALM_MARGIN_RATIO = 0.10

# 아래 LAB 범위는 실물 영상이 없는 상태의 시작값이다.
# 강의실 조명에서 RAW 마스크를 보고 색마다 범위를 다시 맞춘다.
BALL_LAB_RANGES = {
    "red": ((35, 150, 130), (200, 230, 220)),
    "green": ((30, 60, 90), (230, 115, 180)),
    "blue": ((20, 145, 40), (220, 175, 115)),
}
MORPHOLOGY_KERNEL_SIZE = 5

# 현장에서는 RAW 마스크와 처리 마스크를 나란히 확인한 다음 아래 값만 바꾼다.
# none: 원본 마스크 그대로 사용
# open: 공 밖에 작은 점 잡음이 흩어져 있을 때 사용
# close: 공 내부에 작은 구멍이 생길 때 사용
# open_close: 바깥 점 잡음과 내부 구멍이 둘 다 보일 때 사용
# 선택한 뒤 README에 보인 문제와 이 방식을 고른 이유를 적는다.
MORPHOLOGY_MODE = "open_close"

BALL_DRAW_COLORS = {
    "red": (0, 0, 255),
    "green": (0, 200, 0),
    "blue": (255, 0, 0),
}
MAX_PREDICTION_DURATION = 0.5


# 빨강·초록·파랑 공의 위치 추적 정보를 처음 값으로 만드는 함수
def create_ball_tracks():
    return {
        color: {
            "filter": None,  # 특정 공의 칼만 필터
            "center": None,  # 현재 알고 있는 중심 좌표
            "last_observed_at": None,  # 실제로 마지막 검출된 시각
            "last_update_at": None,  # 추적 계산을 마지막으로 한 시각
            "status": "lost",  # observed, predicted 또는 lost
        }
        for color in BALL_DRAW_COLORS
    }


# 현재 공 검출 결과를 보고 칼만 필터를 어떻게 처리할지 결정하는 함수
"""
    "initialize"  : 새 위치에서 추적 시작
    "correct"     : 실제 검출 위치로 기존 추적 보정
    "predict"     : 실제 공이 안 보이므로 잠깐 위치 예측
    "lost"        : 너무 오래 안 보여 추적 종료
"""


def choose_tracking_action(track, candidates, now, width, height, reconnect_distance):
    last_observed_at = track["last_observed_at"]
    expired = (
        last_observed_at is None
        or now - last_observed_at > MAX_PREDICTION_DURATION + 0.000000001
    )
    if len(candidates) != 1:
        return "lost" if expired else "predict"
    if expired:
        return "initialize"
    x, y = candidates[0].center
    old_x, old_y = track["center"]
    distance = (
        ((x - old_x) * width) ** 2 + ((y - old_y) * height) ** 2
    ) ** 0.5  # 픽셀 거리 측정
    # 멀리 다시 나타난 공에 오래된 속도를 이어 붙이지 않고 새 관측에서 시작한다.
    return "initialize" if distance > reconnect_distance else "correct"


# 실제 검출 중심에서 OpenCV 칼만 필터를 초기화하는 함수
def initialize_ball_track(track, center, now):
    kalman = cv2.KalmanFilter(4, 2)
    kalman.measurementMatrix = np.array([[1, 0, 0, 0], [0, 1, 0, 0]], np.float32)
    kalman.transitionMatrix = np.eye(4, dtype=np.float32)
    # 아래 잡음 공분산은 출발값이다. 실제 이동 영상에서 예측 흔들림을 보고 조정한다.
    kalman.processNoiseCov = np.eye(4, dtype=np.float32) * 0.01
    kalman.measurementNoiseCov = np.eye(2, dtype=np.float32) * 0.01
    kalman.errorCovPost = np.eye(4, dtype=np.float32)
    x, y = center
    kalman.statePost = np.array([[x], [y], [0], [0]], np.float32)
    kalman.statePre = kalman.statePost.copy()
    track.update(
        filter=kalman,
        center=center,
        last_observed_at=now,
        last_update_at=now,
        status="observed",
    )


# 실제 관측으로만 correct하고 가림 중에는 표시용 위치만 predict하는 함수
def update_ball_tracks(tracks, balls, now, width, height, reconnect_distance):
    for color, track in tracks.items():
        candidates = [
            ball
            for ball in balls
            if ball.color == color and ball.observed and ball.reliable
        ]
        if track["filter"] is not None:
            dt = now - track["last_update_at"]
            track["filter"].transitionMatrix = np.array(
                [[1, 0, dt, 0], [0, 1, 0, dt], [0, 0, 1, 0], [0, 0, 0, 1]], np.float32
            )
            prediction = track["filter"].predict()
            track["center"] = (float(prediction[0, 0]), float(prediction[1, 0]))
            track["last_update_at"] = now

        action = choose_tracking_action(
            track, candidates, now, width, height, reconnect_distance
        )
        if action == "initialize":
            initialize_ball_track(track, candidates[0].center, now)
        elif action == "correct":
            x, y = candidates[0].center
            corrected = track["filter"].correct(np.array([[x], [y]], np.float32))
            track["center"] = (float(corrected[0, 0]), float(corrected[1, 0]))
            track["last_observed_at"] = now
            track["status"] = "observed"
        elif action == "predict":
            track["status"] = "predicted"
        else:
            track.update(filter=None, center=None, status="lost")


# 예측은 실제 공 테두리와 다르게 회색 십자·빈 원으로 표시한다.
def draw_tracking_overlay(frame, tracks, now):
    result = frame.copy()
    height, width = result.shape[:2]
    for color, track in tracks.items():
        last_at = track["last_observed_at"]
        if (
            track["status"] != "predicted"
            or last_at is None
            or now - last_at > MAX_PREDICTION_DURATION + 0.000000001
        ):
            continue
        x, y = track["center"]
        point = (int(x * width), int(y * height))
        cv2.circle(result, point, 12, (180, 180, 180), 1)
        cv2.drawMarker(result, point, (180, 180, 180), cv2.MARKER_CROSS, 14, 1)
        cv2.putText(
            result,
            f"{color} predicted",
            (point[0] + 15, point[1]),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.45,
            (180, 180, 180),
            1,
        )
    return result


# 손목과 손가락 뿌리 landmark로 손바닥 중심과 상자를 만드는 함수
def get_palm_geometry(landmarks, frame_width, frame_height):
    center_indexes = (0, 5, 17)
    box_indexes = (0, 5, 9, 13, 17)

    palm_center_x = sum(landmarks[i].x for i in center_indexes) / 3
    palm_center_y = sum(landmarks[i].y for i in center_indexes) / 3

    # x와 y의 정규화 길이는 세로 화면에서 서로 다르므로 픽셀로 바꾼 뒤 비교한다.
    palm_pixels = [
        (landmarks[i].x * frame_width, landmarks[i].y * frame_height)
        for i in box_indexes
    ]
    x_values = [point[0] for point in palm_pixels]
    y_values = [point[1] for point in palm_pixels]
    x_min, x_max = min(x_values), max(x_values)
    y_min, y_max = min(y_values), max(y_values)

    long_side = max(x_max - x_min, y_max - y_min)
    margin = long_side * PALM_MARGIN_RATIO
    x_min = max(0, x_min - margin)
    y_min = max(0, y_min - margin)
    x_max = min(frame_width, x_max + margin)
    y_max = min(frame_height, y_max + margin)

    palm_center = (palm_center_x, palm_center_y)
    palm_box = (
        x_min / frame_width,
        y_min / frame_height,
        x_max / frame_width,
        y_max / frame_height,
    )
    return palm_center, palm_box


# MediaPipe 결과에서 매 프레임 새로운 Hand 객체를 만드는 함수
def make_hands(result, hand_mapping, frame_width, frame_height):
    hands = []

    for landmarks, categories in zip(result.hand_landmarks, result.handedness):
        category = categories[0]
        raw_label = category.category_name
        confidence = category.score
        points = [(point.x, point.y) for point in landmarks]
        palm_center, palm_box = get_palm_geometry(landmarks, frame_width, frame_height)

        # 화면 위치로 추측하지 않고 main.py 상단에서 설정한 좌우 매핑을 쓴다.
        physical_hand = hand_mapping.get(raw_label)
        hands.append(
            Hand(
                raw_label,
                physical_hand,
                confidence,
                points,
                palm_center,
                palm_box,
            )
        )

    return hands


# 모델 경로와 최대 손 개수로 MediaPipe 손 검출기를 준비하는 함수
def create_hand_detector(model_path=HAND_MODEL_PATH):
    base_option = python.BaseOptions(model_asset_path=model_path)
    options = vision.HandLandmarkerOptions(base_options=base_option, num_hands=2)
    return vision.HandLandmarker.create_from_options(options)


# BGR 프레임을 RGB로 바꾸고 MediaPipe 결과를 Hand 목록으로 만드는 함수
def detect_hands(frame, hand_detector, hand_mapping):
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    result = hand_detector.detect(mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb))
    frame_height, frame_width = frame.shape[:2]
    return make_hands(result, hand_mapping, frame_width, frame_height)


def get_hand_connections():
    return vision.HandLandmarksConnections.HAND_CONNECTIONS


# 현장에서 선택한 방식대로 색 마스크의 작은 잡음이나 구멍을 정리하는 함수
def apply_morphology(mask, mode, kernel):
    if mode == "none":
        return mask
    if mode == "open":
        return cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    if mode == "close":
        return cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
    if mode == "open_close":
        opened = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        return cv2.morphologyEx(opened, cv2.MORPH_CLOSE, kernel)
    raise ValueError(f"알 수 없는 모폴로지 방식입니다: {mode}")


# 외곽선의 픽셀 중심을 게임에서 쓰는 정규화 좌표의 Ball로 바꾸는 함수
def make_ball(color, center_pixels, area, frame_width, frame_height):
    center_x, center_y = center_pixels
    center = (center_x / frame_width, center_y / frame_height)
    return Ball(color, center, area, observed=True, reliable=True)


# 한 색의 외곽선 중 가장 큰 하나를 공 후보로 만드는 함수
def make_ball_candidates(
    color,
    measurements,
    frame_width,
    frame_height,
):
    if not measurements:
        return [], []

    largest = max(measurements, key=lambda measurement: measurement[2])
    contour, center_pixels, area = largest
    ball = make_ball(
        color,
        center_pixels,
        area,
        frame_width,
        frame_height,
    )
    return [ball], [contour]


# LAB 색 마스크와 외곽선으로 색마다 가장 큰 공 후보를 찾는 함수
def detect_balls(
    frame,
    color_ranges=BALL_LAB_RANGES,
    morphology_mode=MORPHOLOGY_MODE,
):
    frame_height, frame_width = frame.shape[:2]

    # pingpong_circle_overlay.py와 같이 먼저 BGR 프레임을 LAB로 변환한다.
    frame_lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
    kernel = cv2.getStructuringElement(
        cv2.MORPH_ELLIPSE,
        (MORPHOLOGY_KERNEL_SIZE, MORPHOLOGY_KERNEL_SIZE),
    )

    balls = []
    raw_masks = {}
    processed_masks = {}
    contours_by_color = {}

    for color, (lower_values, upper_values) in color_ranges.items():
        lower = np.array(lower_values, dtype=np.uint8)
        upper = np.array(upper_values, dtype=np.uint8)

        # 색별 RAW 마스크를 따로 남겨 현장에서 모폴로지 전후를 비교할 수 있게 한다.
        raw_mask = cv2.inRange(frame_lab, lower, upper)
        processed_mask = apply_morphology(raw_mask, morphology_mode, kernel)

        contours, _ = cv2.findContours(
            processed_mask,
            cv2.RETR_EXTERNAL,
            cv2.CHAIN_APPROX_SIMPLE,
        )

        measurements = []
        for contour in contours:
            area = cv2.contourArea(contour)
            (center_x, center_y), _ = cv2.minEnclosingCircle(contour)
            measurements.append((contour, (center_x, center_y), area))

        # 실습 코드처럼 해당 색에서 가장 큰 외곽선 하나만 선택한다.
        color_balls, valid_contours = make_ball_candidates(
            color,
            measurements,
            frame_width,
            frame_height,
        )
        balls.extend(color_balls)

        raw_masks[color] = raw_mask
        processed_masks[color] = processed_mask
        contours_by_color[color] = valid_contours

    return balls, raw_masks, processed_masks, contours_by_color


# 공 영역을 반투명으로 칠하고 외곽선·최소 외접원·중심을 표시하는 함수
def draw_ball_overlay(frame, contours_by_color):
    result = frame.copy()
    overlay = result.copy()

    for color, contours in contours_by_color.items():
        draw_color = BALL_DRAW_COLORS[color]
        cv2.drawContours(
            overlay,
            contours,
            -1,
            draw_color,
            thickness=cv2.FILLED,
        )

    # 실습 코드처럼 원본을 가리지 않도록 공 영역만 옅게 겹친다.
    result = cv2.addWeighted(overlay, 0.15, result, 0.85, 0)

    for color, contours in contours_by_color.items():
        draw_color = BALL_DRAW_COLORS[color]
        for contour in contours:
            # 밝은 배경에서도 보이도록 검은 바깥선 뒤에 색 안쪽 선을 그린다.
            cv2.drawContours(result, [contour], -1, (0, 0, 0), 4)
            cv2.drawContours(result, [contour], -1, draw_color, 2)

            (center_x, center_y), radius = cv2.minEnclosingCircle(contour)
            center = (int(center_x), int(center_y))
            radius = int(radius)
            cv2.circle(result, center, radius, (0, 0, 0), 4)
            cv2.circle(result, center, radius, draw_color, 2)
            cv2.circle(result, center, 5, draw_color, -1)

    return result


# 손 landmark 연결선·점·손바닥 상자와 레이블을 표시하는 함수
def draw_hand_overlay(frame, hands, connections):
    result = frame.copy()
    frame_height, frame_width = result.shape[:2]
    finger_tips = (4, 8, 12, 16, 20)

    for hand in hands:
        points = [
            (int(x * frame_width), int(y * frame_height)) for x, y in hand.landmarks
        ]
        for connection in connections:
            cv2.line(
                result,
                points[connection.start],
                points[connection.end],
                (0, 255, 0),
                2,
            )
        for index, point in enumerate(points):
            color = (0, 0, 255) if index in finger_tips else (255, 0, 0)
            radius = 6 if index in finger_tips else 4
            cv2.circle(result, point, radius, color, -1)

        x_min, y_min, x_max, y_max = hand.palm_box
        box_start = (int(x_min * frame_width), int(y_min * frame_height))
        box_end = (int(x_max * frame_width), int(y_max * frame_height))
        # 손과 공을 가리지 않도록 손바닥 상자는 가는 청록 점선으로 표시한다.
        x1, y1 = box_start
        x2, y2 = box_end
        for x in range(x1, x2, 12):
            cv2.line(result, (x, y1), (min(x + 6, x2), y1), (255, 255, 0), 1)
            cv2.line(result, (x, y2), (min(x + 6, x2), y2), (255, 255, 0), 1)
        for y in range(y1, y2, 12):
            cv2.line(result, (x1, y), (x1, min(y + 6, y2)), (255, 255, 0), 1)
            cv2.line(result, (x2, y), (x2, min(y + 6, y2)), (255, 255, 0), 1)

        label = hand.physical_hand or f"raw:{hand.raw_label}"
        cv2.putText(
            result,
            f"{label} {hand.confidence:.2f}",
            (box_start[0], max(20, box_start[1] - 8)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (0, 255, 255),
            2,
        )

    return result
