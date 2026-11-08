"""2026.10.17 컴퓨터 비전 과제: 농구공 영역 및 외곽선 검출."""

from pathlib import Path

import cv2
import matplotlib.pyplot as plt
import numpy as np


# 노트북에서 사용한 저장소의 원본 이미지를 읽습니다.
image_path = Path(__file__).resolve().parent.parent / "src" / "images" / "basketball_crop.jpg"
basketball = cv2.imread(str(image_path))
if basketball is None:
    raise FileNotFoundError(f"이미지를 읽을 수 없습니다: {image_path}")

# LAB 색공간에서 밝기 채널에 CLAHE를 적용하고 농구공 색상 범위를 마스킹합니다.
lower_basketball_lab = np.array([70, 130, 70])
upper_basketball_lab = np.array([180, 230, 185])

basketball_lab = cv2.cvtColor(basketball, cv2.COLOR_BGR2LAB)
l, a, b = cv2.split(basketball_lab)
clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
l_clahe_enhanced = clahe.apply(l)
basketball_enhanced_lab = cv2.merge((l_clahe_enhanced, a, b))
mask_enhanced = cv2.inRange(
    basketball_enhanced_lab, lower_basketball_lab, upper_basketball_lab
)

# Morphological operation으로 최종 binary mask를 생성합니다.
kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
ball_mask_opened2 = cv2.morphologyEx(
    mask_enhanced, cv2.MORPH_OPEN, kernel, iterations=2
)
ball_mask_closed3 = cv2.morphologyEx(
    ball_mask_opened2, cv2.MORPH_CLOSE, kernel, iterations=3
)
final_ball_mask = ball_mask_closed3

# Binary mask에서 가장 큰 외곽선을 검출합니다.
final_img = basketball.copy()
contours, _ = cv2.findContours(
    final_ball_mask,
    cv2.RETR_EXTERNAL,
    cv2.CHAIN_APPROX_SIMPLE,
)

if len(contours) > 0:
    largest_contour = max(contours, key=cv2.contourArea)

    final_mask = np.zeros_like(final_ball_mask)
    cv2.drawContours(
        final_mask,
        [largest_contour],
        -1,
        255,
        thickness=cv2.FILLED,
    )

    # 가장 큰 영역을 반투명 초록색으로 표시하고 외곽선을 그립니다.
    mask_color = np.zeros_like(final_img)
    mask_color[:, :, 1] = final_mask
    alpha = 0.35
    final_img = cv2.addWeighted(final_img, 1.0, mask_color, alpha, 0)
    cv2.drawContours(final_img, [largest_contour], -1, (0, 255, 0), 2)

# OpenCV의 BGR 이미지를 RGB로 바꿔 Matplotlib에 올바른 색상으로 표시합니다.
plt.imshow(cv2.cvtColor(final_img, cv2.COLOR_BGR2RGB))
plt.axis("off")
plt.show()
