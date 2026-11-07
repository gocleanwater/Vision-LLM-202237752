import cv2
import numpy as np

pipeline = (
    "v4l2src device=/dev/video0 ! "
    "video/x-raw,format=YUY2,width=640,height=480,framerate=30/1 ! "
    "videoconvert ! video/x-raw,format=BGR ! "
    "queue leaky=downstream max-size-buffers=1 "
    "max-size-bytes=0 max-size-time=0 ! "
    "appsink drop=true max-buffers=1 sync=false"
)
cap = cv2.VideoCapture(pipeline, cv2.CAP_GSTREAMER)

# TODO: 배운 기술(이미지 전처리, 특징 추출)을 활용하여 실시간으로 객체를 검출

# 초록 LAB lower/upper range
green_lower = np.array([30, 60, 90], dtype=np.uint8)
green_upper = np.array([230, 115, 180], dtype=np.uint8)
kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))

while True:
    ret, frame = cap.read()

    if not ret:
        break
    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

    # TODO: 각 프레임 이미지를 전처리
    pingpong_lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)

    # TODO: Color Segmentation으로 Binary Mask 생성
    pingpong_mask_lab = cv2.inRange(pingpong_lab, green_lower, green_upper)

    # TODO: Morphological Operation을 적용하여 객체 영역 추출
    pingpong_mask_opened = cv2.morphologyEx(pingpong_mask_lab, cv2.MORPH_OPEN, kernel)
    # pingpong_mask_closed = cv2.morphologyEx(pingpong_mask_opened, cv2.MORPH_CLOSE, kernel)

    # cv2.imshow("Camera", frame)
    # cv2.imshow("0. RAW mask", pingpong_mask_lab)
    # cv2.imshow("1. OPEN mask", pingpong_mask_opened)
    # cv2.imshow("2. CLOSE mask", pingpong_mask_closed)

    # 해보니 굳이 CLOSE까지 할 필요는 없어서 OPEN까지만 진행

    # TODO: 객체의 중심과 반지름을 구해 프레임 위에 overlay

    contours, _ = cv2.findContours(
        pingpong_mask_opened,
        cv2.RETR_EXTERNAL,
        cv2.CHAIN_APPROX_SIMPLE
    )

    result = frame.copy()

    if len(contours) > 0:
        # 가장 큰 contour
        largest_contour = max(contours, key=cv2.contourArea)

        # 가장 큰 contour만 채운 binary mask 생성
        largest_mask = np.zeros_like(pingpong_mask_opened)
        cv2.drawContours(
            largest_mask,
            [largest_contour],
            -1,
            255,
            thickness=cv2.FILLED
        )

        # 공 영역을 반투명 빨간색으로 표시
        overlay = result.copy()
        overlay[largest_mask > 0] = (0, 0, 255)  # OpenCV는 BGR, 빨간색
        result = cv2.addWeighted(overlay, 0.15, result, 0.85, 0)

        # 빨간색 외곽선
        cv2.drawContours(result, [largest_contour], -1, (0, 0, 255), 2)

        # 최소 외접원 중심 및 반지름
        (x, y), radius = cv2.minEnclosingCircle(largest_contour)
        center_circle = (int(x), int(y))
        radius = int(radius)

        # 파란색 원
        cv2.circle(result, center_circle, radius, (0,0,255), 3)
        cv2.circle(result, center_circle, 5, (0,0,255), -1)

    cv2.imshow("Camera", result)

cap.release()
cv2.destroyAllWindows()
