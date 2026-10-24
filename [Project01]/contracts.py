"""공·손·한 프레임의 정보를 담는 간단한 클래스."""


class Ball:
    def __init__(self, color, center, area, observed=True, reliable=True):
        self.color = color          # 'red', 'green', 'blue'
        self.center = center        # (x, y)
        self.area = area            # 원본 영상의 공 면적(px²)
        self.observed = observed    # 실제 검출이면 True, 예측이면 False
        self.reliable = reliable    # 유효한 공 후보인지 표시


class Hand:
    def __init__(self, raw_label, physical_hand, confidence, landmarks,
                 palm_center, palm_box):
        self.raw_label = raw_label          # 모델의 'Left' / 'Right'
        self.physical_hand = physical_hand  # 보정한 'left' / 'right', 미보정은 None
        self.confidence = confidence
        self.landmarks = landmarks          # (x, y) 좌표 목록
        self.palm_center = palm_center
        self.palm_box = palm_box            # 손바닥 상자 (x_min, y_min, x_max, y_max)


class Frame:
    def __init__(self, frame_id, read_at, processed_at, balls, hands):
        self.frame_id = frame_id
        self.read_at = read_at              # 프레임 읽기 완료 시각(초)
        self.processed_at = processed_at    # 인식 처리 완료 시각(초)
        self.balls = balls                  # Ball 객체 목록
        self.hands = hands                  # Hand 객체 목록
