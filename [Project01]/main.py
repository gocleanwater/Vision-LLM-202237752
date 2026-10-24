"""카메라에서 손·공 관측과 오버레이를 확인하는 실행 파일."""

import threading
import time
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

import game
from contracts import Frame
from vision import (
    create_ball_tracks,
    create_hand_detector,
    detect_balls,
    detect_hands,
    draw_ball_overlay,
    draw_hand_overlay,
    get_hand_connections,
    update_ball_tracks,
    draw_tracking_overlay,
    MAX_PREDICTION_DURATION,
)


CAMERA_PIPELINE = (
    "nvarguscamerasrc sensor-id=0 ! "
    "video/x-raw(memory:NVMM), width=1280, height=720, framerate=30/1 ! "
    "nvvidconv ! "
    "video/x-raw, format=BGRx ! "
    "videoconvert ! "
    "video/x-raw, format=BGR ! "
    "queue leaky=downstream max-size-buffers=1 ! "
    "appsink drop=true max-buffers=1 sync=false"
)

# 현장에서 모폴로지를 정할 때만 True로 바꾸어 색별 전후 마스크를 확인한다.
# 게임 시연 화면은 창 하나를 써야 하므로 선택이 끝나면 다시 False로 둔다.
SHOW_MASKS = False
# 우선 MediaPipe 레이블을 그대로 사용한다. 실제 좌우가 맞는지는 현장에서 확인!
# 반대로 나오면 아래 값만 {"Left": "right", "Right": "left"}로 바꾼다.
# 촬영 방향이나 반전 설정을 바꾼 경우에도 실제 양손을 다시 확인한다.
HAND_MAPPING = {"Left": "left", "Right": "right"}

# 현장에서 회전된 영상의 정규화 좌표로 채운다. 미설정이면 SETUP에 머문다.
# {"start": (x1, y1, x2, y2), "presentation": (...), "waiting": (...)}
REGIONS = {
    "start": (0.02, 0.00, 0.98, 0.30),
    "presentation": (0.02, 0.31, 0.98, 0.62),
    "waiting": (0.02, 0.63, 0.98, 1.00),
}
FONT_PATH = Path(__file__).resolve().parent / "assets/fonts/NotoSansKR-wght.ttf"
FONT_SIZE = 22
# None이면 Jetson CSI 카메라. 저장 영상 경로를 넣으면 원본 FPS 간격으로 재생한다.
VIDEO_PATH = None
# 저장 영상과 문제를 대조할 때만 채운다. 완료 시도 순서로 사용하고 목록을 반복한다.
# 장애로 무효가 된 시도는 완료 횟수가 늘지 않으므로 같은 고정 문제를 다시 사용한다.
FIXED_QUESTIONS = []
# 실제 검출을 먼저 확인한 뒤 켠다. 거리 단위는 회전된 영상의 픽셀이다.
TRACKING_ENABLED = False
TRACK_RECONNECT_DISTANCE = None


def rotate_camera_frame(frame):
    return cv2.rotate(frame, cv2.ROTATE_90_COUNTERCLOCKWISE)


# 글자 수가 아니라 실제 픽셀 너비를 보고 정보 띠의 줄을 나누는 함수
def make_text_band(lines, width, font):
    measure = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    wrapped = []
    for line in lines:
        current = ""
        for character in line:
            candidate = current + character
            if current and measure.textbbox((0, 0), candidate, font=font)[2] > width - 32:
                wrapped.append(current)
                current = character
            else:
                current = candidate
        wrapped.append(current)

    line_height = font.getbbox("한글Ag")[3] + 8
    band = Image.new("RGB", (width, 24 + line_height * len(wrapped)), (25, 25, 25))
    draw = ImageDraw.Draw(band)
    for index, line in enumerate(wrapped):
        draw.text((16, 10 + index * line_height), line, font=font, fill=(255, 255, 255))
    return np.array(band)


# 관측 좌표는 카메라 영상 안에서만 사용하고 정보 띠는 마지막에 붙이는 함수
def draw_screen(frame, game_state, now, font, frame_result=None, regions=None, message=None):
    height, width = frame.shape[:2]
    camera_image = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
    draw = ImageDraw.Draw(camera_image)
    if regions is not None:
        names = {"start": "공 출발", "presentation": "제시", "waiting": "손 대기"}
        for name, box in regions.items():
            x1, y1, x2, y2 = box
            start = (int(x1 * (width - 1)), int(y1 * (height - 1)))
            end = (int(x2 * (width - 1)), int(y2 * (height - 1)))
            draw.rectangle((start, end), outline=(255, 230, 80), width=2)
            draw.text((start[0] + 5, start[1] + 3), names[name], font=font, fill=(255, 230, 80))

    top, bottom = game.get_screen_lines(game_state, now, frame_result)
    if message:
        bottom.append(message)
    top_band = make_text_band(top, width, font)
    bottom_band = make_text_band(bottom, width, font)
    # Pillow는 RGB, OpenCV는 BGR이므로 합친 뒤 화면 출력 형식으로 되돌린다.
    screen_rgb = np.vstack((top_band, np.array(camera_image), bottom_band))
    return cv2.cvtColor(screen_rgb, cv2.COLOR_RGB2BGR)


# 카메라는 최신 프레임만 보관하고 게임·모델·화면 처리는 하지 않는 클래스
class CameraReader:
    def __init__(self, capture, is_video=False, frame_interval=0.0):
        self.capture = capture
        self.is_video = is_video
        self.frame_interval = frame_interval
        self.end_of_stream = False
        self.lock = threading.Lock()
        self.running = False
        self.thread = None
        self.latest_frame = None
        self.latest_read_at = None
        self.latest_frame_id = 0
        self.read_failure_pending = False

    def start(self):
        self.running = True
        self.thread = threading.Thread(target=self.read_frames, daemon=True)
        self.thread.start()

    def read_frames(self):
        try:
            while self.running:
                ret, frame = self.capture.read()
                read_at = time.monotonic()

                if not ret:
                    if self.is_video:
                        with self.lock:
                            self.end_of_stream = True
                        break
                    with self.lock:
                        self.read_failure_pending = True
                    # 카메라가 끊긴 동안 빈 반복으로 CPU를 계속 쓰지 않도록 잠깐 기다린다.
                    time.sleep(0.01)
                    continue

                self.store_frame(frame, read_at)
                if self.frame_interval > 0:
                    time.sleep(self.frame_interval)
        finally:
            # 읽기와 해제를 같은 스레드에서 순서대로 한다. read 중에는 해제하지 않기!
            self.capture.release()

    def store_frame(self, frame, read_at):
        with self.lock:
            self.latest_frame_id += 1
            self.latest_read_at = read_at
            self.latest_frame = frame.copy()

    def get_latest(self, last_frame_id):
        with self.lock:
            if (
                self.latest_frame is None
                or self.latest_frame_id == last_frame_id
            ):
                return None

            # 메인 반복문이 그림을 그려도 스레드가 보관한 프레임은 바뀌지 않게 복사한다.
            return (
                self.latest_frame_id,
                self.latest_read_at,
                self.latest_frame.copy(),
            )

    def has_ended(self):
        with self.lock:
            return self.end_of_stream

    def take_read_failure(self):
        with self.lock:
            # 다음 정상 프레임이 먼저 와도 한 번의 읽기 실패를 놓치지 않기!
            failed = self.read_failure_pending
            self.read_failure_pending = False
            return failed

    def stop(self):
        self.running = False
        if self.thread is not None:
            # read가 늦어져도 메인은 1초만 기다린다.
            # 이후 카메라 해제는 read가 끝난 뒤 읽기 스레드가 직접 한다.
            self.thread.join(timeout=1.0)


def main():
    if TRACKING_ENABLED and TRACK_RECONNECT_DISTANCE is None:
        raise ValueError("추적을 켜기 전에 현장 재연결 거리 TRACK_RECONNECT_DISTANCE를 설정하세요.")
    if not FONT_PATH.is_file():
        raise FileNotFoundError(f"한글 폰트 파일을 찾을 수 없습니다: {FONT_PATH}")
    font = ImageFont.truetype(str(FONT_PATH), FONT_SIZE)
    # 포함한 가변 폰트의 기본값은 얇은 두께이므로 읽기 쉬운 Regular(400)를 쓴다.
    font.set_variation_by_axes([400])
    # =============== 모델 준비 =============== #
    hand_detector = create_hand_detector()
    hand_connections = get_hand_connections()

    # =============== 카메라 준비 =============== #
    if VIDEO_PATH is None:
        cap = cv2.VideoCapture(CAMERA_PIPELINE, cv2.CAP_GSTREAMER)
    else:
        cap = cv2.VideoCapture(str(VIDEO_PATH))
    if not cap.isOpened():
        cap.release()
        hand_detector.close()
        raise RuntimeError("입력을 열 수 없습니다: 카메라·GStreamer 또는 VIDEO_PATH를 확인하세요.")

    frame_interval = 0.0
    if VIDEO_PATH is not None:
        fps = cap.get(cv2.CAP_PROP_FPS)
        if not np.isfinite(fps) or fps <= 0:
            cap.release()
            hand_detector.close()
            raise RuntimeError("저장 영상의 FPS를 읽을 수 없습니다.")
        frame_interval = 1.0 / fps
    camera = CameraReader(cap, VIDEO_PATH is not None, frame_interval)
    camera.start()
    last_frame_id = 0
    game_state = game.create_game_state()
    display_frame = None
    last_error = None
    frame_result = None
    tracks = create_ball_tracks()

    try:
        while True:
            now = time.monotonic()
            had_read_failure = camera.take_read_failure()
            if had_read_failure:
                game.update_game(game_state, "read_failure", now, regions=REGIONS)
                frame_result = None
            latest = camera.get_latest(last_frame_id)
            if latest is None and camera.has_ended():
                print("저장 영상 재생 종료:", game.get_summary(game_state))
                break

            if latest is not None:
                frame_id, read_at, frame = latest
                last_frame_id = frame_id

                # =============== 프레임 방향 통일 =============== #
                # 공·손 검출과 영역 좌표는 모두 회전된 세로 영상을 기준으로 한다.
                frame = rotate_camera_frame(frame)

                # =============== RGB 변환과 손 검출 =============== #
                # detect_hands 안에서 BGR을 RGB로 바꾼 뒤 MediaPipe를 실행한다.
                try:
                    hands = detect_hands(frame, hand_detector, HAND_MAPPING)

                    # =============== LAB 마스크와 공 검출 =============== #
                    balls, raw_masks, processed_masks, contours_by_color = detect_balls(frame)
                except Exception as error:
                    # 실제 모델·검출 오류는 입력 장애로 전달하고 다음 영상에서 재시도한다.
                    if str(error) != last_error:
                        print(f"관측 처리 오류: {error}")
                    last_error = str(error)
                    frame_result = None
                    game.update_game(game_state, "model_error", time.monotonic(), regions=REGIONS)
                    display_frame = frame.copy()
                else:
                    last_error = None

                    processed_at = time.monotonic()
                    # 검출 중에도 카메라가 한 번 실패했을 수 있으므로 채점 전에 확인한다.
                    if camera.take_read_failure():
                        game.update_game(game_state, "read_failure", processed_at, regions=REGIONS)
                    observation = Frame(frame_id, read_at, processed_at, balls, hands)
                    frame_result = game.update_game(
                        game_state, "frame", processed_at, observation,
                        REGIONS,
                    )
                    if TRACKING_ENABLED:
                        height, width = frame.shape[:2]
                        # 추적 상태만 갱신한다. observation.balls는 실제 관측 그대로 유지!
                        update_ball_tracks(tracks, balls, processed_at, width, height,
                                           TRACK_RECONNECT_DISTANCE)

                    # =============== 손·공 정보 표시 =============== #
                    display_frame = draw_ball_overlay(frame, contours_by_color)
                    display_frame = draw_hand_overlay(display_frame, hands, hand_connections)

                    # 모폴로지를 정할 때만 RAW와 처리 결과를 직접 비교한다.
                    if SHOW_MASKS:
                        for color in raw_masks:
                            cv2.imshow(f"{color} 0. RAW mask", raw_masks[color])
                            cv2.imshow(f"{color} 1. processed mask", processed_masks[color])
            elif not had_read_failure:
                game.update_game(game_state, "no_input", now, regions=REGIONS)

            # =============== 화면 출력 =============== #
            if (FIXED_QUESTIONS and game_state["status"] == "COUNTDOWN"
                    and game_state["question"] is not None):
                index = game_state["completed_attempts"] % len(FIXED_QUESTIONS)
                game_state["question"] = FIXED_QUESTIONS[index]
            if display_frame is None:
                # 첫 카메라 입력 전에도 창을 만들고 q/r 키를 받을 수 있게 한다.
                display_frame = np.zeros((640, 480, 3), dtype=np.uint8)
            screen_frame = display_frame
            screen_now = time.monotonic()
            tracking_message = None
            if TRACKING_ENABLED:
                screen_frame = draw_tracking_overlay(display_frame, tracks, screen_now)
                states = []
                for color, track in tracks.items():
                    last_at = track["last_observed_at"]
                    status = track["status"]
                    if last_at is None or screen_now - last_at > MAX_PREDICTION_DURATION:
                        status = "lost"
                    states.append(f"{color}: {status}")
                tracking_message = "추적 | " + " | ".join(states)
            message = f"관측 처리 오류: {last_error}" if last_error else tracking_message
            result = draw_screen(
                screen_frame, game_state, screen_now, font,
                frame_result, REGIONS,
                message,
            )
            question = game_state["question"]
            presented_at = time.monotonic()
            cv2.imshow("Jetson Color Ball Game", result)
            if game_state["status"] == "COUNTDOWN" and question is not None:
                game.mark_problem_presented(game_state, presented_at)

            key = cv2.waitKey(1) & 0xFF
            if key == ord("r"):
                game.restart_game(game_state)
            if key == ord("q"):
                break

    finally:
        # =============== 종료 정리 =============== #
        camera.stop()
        hand_detector.close()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
