import cv2
import numpy as np
from numpy.linalg import inv

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

def KalmanFilter(mu_prev, sigma_prev, z):
    mu_bar = A_t.dot(mu_prev)
    sigma_bar = A_t.dot(sigma_prev).dot(A_t.transpose()) + R_t
    if z is None:
        return mu_bar, sigma_bar
    else:
        K_t = sigma_bar.dot(C_t.transpose()).dot(inv(C_t.dot(sigma_bar).dot(C_t.transpose()) + Q_t))
        mu = mu_bar + K_t.dot(z - C_t.dot(mu_bar))
        sigma = (np.identity(2) - K_t.dot(C_t)).dot(sigma_bar)
        return mu, sigma


# Kalman filter 변수 정의
A_t = np.array([[1, 1], [0, 1]])
G = np.array([[0.5], [1]])
R_t = G.dot(G.transpose())
C_t = np.array([[1, 0]])
Q_t = np.array([[1]])
mu_t = np.array([[0, 0], [0, 0]])
sigma_t = np.array([[0, 0], [0, 0]])

# 객체 최초 검출 여부 확인용 boolean
found = False
radius = 0

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

    # TODO: Kalman Filter를 활용하여 객체 추적

    # TODO: 탐지된 객체의 중심과 반지름을 구해 프레임 위에 overlay
    # TODO: 예측된 객체의 중심과 반지름을 구해 프레임 위에 다른 색으로 overlay

    contour_lst, _ = cv2.findContours(
        pingpong_mask_opened,
        cv2.RETR_EXTERNAL,
        cv2.CHAIN_APPROX_SIMPLE
    )

    if len(contour_lst) > 0:
        # 가장 큰 contour 선택
        contour = max(contour_lst, key=cv2.contourArea)

        # 최소 외접원 반지름
        (_, _), radius_float = cv2.minEnclosingCircle(contour)
        radius = int(radius_float)

        # 무게중심
        M = cv2.moments(contour)
        if M["m00"] != 0:
            center = (
                int(M["m10"] / M["m00"]),
                int(M["m01"] / M["m00"])
            )
        else:
            center = center_circle

        # 검출된 객체에 파란 원 overlay
        cv2.circle(result, center, int(radius), (255, 0, 0), 2)
        cv2.circle(result, center, 5, (255, 0, 0), -1)

        # 객체 최초 검출
        if not found:
            found = True

    # 최초 검출 이후 Kalman Filter 적용
    # 측정값 사용 (visible) -> Prediction & Update
    if found and (len(contour_lst) > 0):
        mu_t, sigma_t = KalmanFilter(mu_t, sigma_t, np.array([list(center)]))
        x_bel, y_bel = mu_t[0][0], mu_t[0][1]

    # 측정값 미사용 (occluded) -> Prediction
    elif found and (len(contour_lst) <= 0):
        mu_t, sigma_t = KalmanFilter(mu_t, sigma_t, None)
        x_bel, y_bel = mu_t[0][0], mu_t[0][1]

    # 예측한 객체 위치에 노란 원 overlay
    if found:
        cv2.circle(result, (int(x_bel), int(y_bel)), int(radius), (0, 255, 255), 2)
        cv2.circle(result, (int(x_bel), int(y_bel)), 5, (0, 255, 255), -1)

    cv2.imshow("Camera", result)

cap.release()
cv2.destroyAllWindows()
