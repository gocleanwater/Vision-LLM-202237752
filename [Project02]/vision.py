"""int8_yolo.py의 GStreamer·YOLO 추론을 요청 한 번의 사진 분석에 사용한다."""
import logging
import math

# data.yaml의 이름으로 매핑한다. 클래스 번호를 하드코딩하지 않는다.
INGREDIENT_NAMES = dict(zip(
    ['banana', 'bell pepper', 'bulgur', 'cabbage', 'carrot', 'cheese', 'chicken',
     'chickpeas', 'cucumber', 'egg', 'eggplant', 'farfalle pasta', 'fusilli pasta',
     'garlic', 'green pepper', 'ground meat', 'ketchup', 'lemon', 'margarine',
     'mayonnaise', 'milk', 'mushroom', 'olive', 'olive oil', 'onion', 'parsley',
     'potato', 'red lentils', 'rice', 'sausage', 'spaghetti', 'tomato',
     'tomato paste', 'turkish dumplings', 'yogurt', 'zucchini'],
    ['바나나', '파프리카', '불구르', '양배추', '당근', '치즈', '닭고기',
     '병아리콩', '오이', '계란', '가지', '파르팔레 파스타', '푸실리 파스타',
     '마늘', '풋고추', '다진 고기', '케첩', '레몬', '마가린', '마요네즈',
     '우유', '버섯', '올리브', '올리브유', '양파', '파슬리', '감자',
     '붉은 렌틸콩', '쌀', '소시지', '스파게티', '토마토', '토마토 페이스트',
     '터키식 만두', '요거트', '주키니']))


# 상자·점수를 검사하고 바로 사용할 재료와 VLM 확인 후보를 나눈다.
# confidence는 모델의 점수이지 정답 확률을 보장하는 값은 아니다.
def split_detections(detections, width, height, detect_conf, accept_conf):
    certain, candidates = [], []
    for detection in detections:
        ingredient = detection['ingredient_id']
        score = detection['confidence']
        coords = detection['bbox_xyxy']
        if ingredient not in INGREDIENT_NAMES or not math.isfinite(score) or not 0 <= score <= 1:
            raise ValueError('지원하지 않는 YOLO 클래스 또는 점수')
        if len(coords) != 4 or not all(math.isfinite(v) for v in coords):
            raise ValueError('잘못된 상자 좌표')
        x1, y1, x2, y2 = coords
        if not (0 <= x1 < x2 <= width and 0 <= y1 < y2 <= height):
            raise ValueError('영상 범위를 벗어난 상자')
        # 높은 점수 → 바로 채택 / 중간 점수 → VLM 확인 / 탐지 하한 미만 → 제외.
        if score >= accept_conf:
            certain.append(ingredient)
        elif score >= detect_conf:
            candidates.append(detection)
    return list(dict.fromkeys(certain)), candidates


# 실제로 전달한 후보 번호마다 한 번씩만 답했는지 검사한다.
# null(None)은 확인 불가이며, 원래 YOLO 분류를 다른 지원 재료로 정정할 수도 있다.
def validate_checks(payload, candidates):
    # 집합 비교로 없는 번호 추가·중복·누락을 막는다.
    expected = {d['detection_id'] for d in candidates}
    if not isinstance(payload, dict) or set(payload) != {'checks'} or not isinstance(payload['checks'], list):
        raise ValueError('VLM 형식 오류')
    seen, ingredients = set(), []
    for check in payload['checks']:
        if not isinstance(check, dict) or set(check) != {'detection_id', 'ingredient_id'}:
            raise ValueError('VLM 항목 오류')
        ident, ingredient = check['detection_id'], check['ingredient_id']
        if not isinstance(ident, str) or ident not in expected or ident in seen:
            raise ValueError('없는 후보 또는 중복 후보')
        if ingredient is not None and (not isinstance(ingredient, str) or ingredient not in INGREDIENT_NAMES):
            raise ValueError('지원하지 않는 재료')
        seen.add(ident)
        if ingredient:
            ingredients.append(ingredient)
    if seen != expected:
        raise ValueError('후보 확인 누락')
    return ingredients


# 확실한 재료는 보존하고 애매한 후보가 있을 때만 check를 한 번 호출한다.
# YOLO가 아예 탐지하지 못한 객체를 새로 찾는 단계는 아니다.
def resolve_ingredients(certain, candidates, check):
    if not candidates:
        return certain
    try:
        confirmed = validate_checks(check(candidates), candidates)
    except Exception:
        logging.exception('VLM 확인 실패: 애매한 후보만 제외합니다.')
        confirmed = []
    return list(dict.fromkeys(certain + confirmed))


# 매 질문마다 YOLO를 다시 로딩하지 않도록 모델과 설정을 묶어 두는 클래스다.
class Vision:
    def __init__(self, engine_path, runtime, check_candidates, detect_conf=0.15, accept_conf=0.65):
        if not 0 <= detect_conf < accept_conf <= 1:
            raise ValueError('0 <= detect_conf < accept_conf <= 1이어야 합니다.')
        if not engine_path.is_file() or engine_path.name.endswith('_raw.engine'):
            raise FileNotFoundError('최종 식재료 엔진을 배치하세요: ' + str(engine_path))
        self.engine_path, self.runtime = engine_path, runtime
        self.check_candidates = check_candidates
        self.detect_conf, self.accept_conf = detect_conf, accept_conf
        # 실제 관측이 필요할 때 한 번 로딩한 뒤 같은 모델 객체를 재사용한다.
        self.model = None

    # 현재 사진 한 장을 분석해 ["egg", "potato"] 같은 중복 없는 재료 종류 목록을 반환한다.
    def observe(self):
        import cv2
        from ultralytics import YOLO
        image_path = self.runtime / 'camera.jpg'
        collage_path = self.runtime / 'vlm_candidates.jpg'
        # 새 촬영이 실패했을 때 이전 사진을 이번 결과로 쓰지 않도록 먼저 지운다.
        image_path.unlink(missing_ok=True)
        collage_path.unlink(missing_ok=True)
        # int8_yolo.py의 GStreamer 입력. YUY2 영상을 OpenCV용 BGR로 바꾼다.
        # queue/appsink는 오래된 프레임이 쌓이지 않도록 설정한다.
        pipeline = (
            'v4l2src device=/dev/video0 ! '
            'video/x-raw,format=YUY2,width=640,height=480,framerate=30/1 ! '
            'videoconvert ! video/x-raw,format=BGR ! '
            'queue leaky=downstream max-size-buffers=1 '
            'max-size-bytes=0 max-size-time=0 ! '
            'appsink drop=true max-buffers=1 sync=false'
        )
        cap = cv2.VideoCapture(pipeline, cv2.CAP_GSTREAMER)
        try:
            if not cap.isOpened():
                raise RuntimeError('카메라를 열지 못했습니다.')
            # 연결 직후 검은 프레임이 나올 수 있어 약 3초 동안 밝기와 색상이 안정되게 한다.
            for _ in range(90):
                ret, frame = cap.read()
                if not ret or frame is None:
                    raise RuntimeError('촬영 실패')
        finally:
            # 촬영 성공·실패 모두 카메라를 닫는다. 사진 분석 중에는 카메라를 붙잡지 않는다.
            cap.release()
        if not cv2.imwrite(str(image_path), frame):
            raise RuntimeError('사진 저장 실패')
        if self.model is None:
            self.model = YOLO(str(self.engine_path), task='detect')
        # 탐지 하한으로 후보를 먼저 받고, 바로 사용할 상한 기준은 뒤에서 따로 적용한다.
        results = self.model.predict(source=frame, conf=self.detect_conf, iou=0.5, verbose=False, classes=None)
        result = results[0]
        # 다른 모델을 잘못 사용하지 않았는지 학습한 36종의 클래스 이름과 대조한다.
        if set(result.names.values()) != set(INGREDIENT_NAMES):
            raise ValueError('엔진 클래스가 학습한 36종과 다릅니다.')
        height, width = frame.shape[:2]
        detections = []
        for index, box in enumerate(result.boxes):
            # xyxy는 왼쪽 위(x1,y1)와 오른쪽 아래(x2,y2)의 원본 영상 픽셀 좌표다.
            coords = box.xyxy[0].tolist()
            # 부동소수점 오차 또는 가장자리 좌표를 영상 안으로 자른다.
            coords = [max(0., min(float(v), float(width if i % 2 == 0 else height))) for i, v in enumerate(coords)]
            detections.append({'detection_id': 'd' + str(index + 1),
                               'ingredient_id': result.names[int(box.cls.item())],
                               'confidence': float(box.conf.item()), 'bbox_xyxy': coords})
        certain, candidates = split_detections(detections, width, height, self.detect_conf, self.accept_conf)
        # 이 내부 함수는 이번 frame을 기억한다. 확인 후보가 있을 때만 호출된다.
        def check(items):
            collage = make_collage(frame, items)
            if not cv2.imwrite(str(collage_path), collage):
                raise RuntimeError('후보 사진 저장 실패')
            return self.check_candidates(collage_path, items)
        return resolve_ingredients(certain, candidates, check)


# 여러 bbox를 잘라 번호와 함께 격자 이미지 한 장으로 만든다. 번호는 원래 상자와 응답을 연결한다.
def make_collage(frame, candidates):
    import cv2
    import numpy as np
    # 후보마다 호출하지 않고 모든 crop을 번호와 함께 한 장에 담는다.
    columns = min(4, len(candidates))
    rows = math.ceil(len(candidates) / columns)
    canvas = np.full((rows * 192, columns * 192, 3), 255, dtype=np.uint8)
    height, width = frame.shape[:2]
    for index, candidate in enumerate(candidates):
        x1, y1, x2, y2 = candidate['bbox_xyxy']
        # 주변에 약간의 여백을 주되 실제 영상 경계를 벗어나지 않게 자른다.
        margin = int(max(x2 - x1, y2 - y1) * 0.08) + 1
        crop = frame[max(0, int(y1) - margin):min(height, math.ceil(y2) + margin),
                     max(0, int(x1) - margin):min(width, math.ceil(x2) + margin)]
        # 가로세로 비율을 유지해 한 칸에 넣는다. 위쪽 공간은 번호 표시용이다.
        scale = min(180 / crop.shape[1], 156 / crop.shape[0])
        crop = cv2.resize(crop, (max(1, int(crop.shape[1] * scale)), max(1, int(crop.shape[0] * scale))))
        x, y = (index % columns) * 192, (index // columns) * 192
        canvas[y + 30:y + 30 + crop.shape[0], x:x + crop.shape[1]] = crop
        cv2.putText(canvas, candidate['detection_id'], (x + 4, y + 22), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 1)
    return canvas
