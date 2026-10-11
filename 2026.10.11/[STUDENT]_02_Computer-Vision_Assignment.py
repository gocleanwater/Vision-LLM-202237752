"""2026.10.11 과제"""

import cv2
import numpy as np
import matplotlib.pyplot as plt
import skimage.data

# ==========================================================

# TODO: astronaut 이미지를 흑백으로 변환하여 렌더링
astronaut = skimage.data.astronaut()

# 정규화
# (OpenCV는 float는 범위를 [0,1]로 잡아둬서 이렇게 정규화를 진행해야 한다.) (int면 범위가 [0,255]이다.)
astronaut = astronaut.astype(np.float32) / 255.

# astronaut 사진은 skikit image 라이브러리에서 가져왔으므로 RGB 색공간이다. (오직 OpenCV만 BGR이다.)
astronaut_gray = cv2.cvtColor(astronaut, cv2.COLOR_RGB2GRAY)

plt.imshow(astronaut_gray, cmap="gray")
plt.axis("off");

# ==========================================================

# TODO: astronaut 이미지를 HSV 색공간으로 변환
# TODO: HSV 각 채널을 분리한 뒤 subplot에 시각화

image_hsv = cv2.cvtColor(astronaut, cv2.COLOR_RGB2HSV)
h, s, v = cv2.split(image_hsv)

plt.figure(figsize=(15,8))

plt.subplot(1,3,1), plt.imshow(h, cmap="gray"), plt.title('H Channel (Hue)')
# Hue는 색깔 정보인데, 독립적으로 split해서 보면... 정보가 거의 없다(색깔을 어떻게 한 차원으로.. 보여주는 것은 말이 안되기 때문에!)

plt.subplot(1,3,2), plt.imshow(s, cmap="gray"), plt.title('S Channel (Saturation)')
plt.subplot(1,3,3), plt.imshow(v, cmap="gray"), plt.title('V Channel (Value)')

for ax in plt.gcf().axes:
    ax.axis("off")

# ==========================================================

image = skimage.data.astronaut()
image = image.astype(np.float32) / 255.

# TODO: 이미지를 HSV 색공간으로 변환
image_hsv = cv2.cvtColor(image, cv2.COLOR_RGB2HSV)

# TODO: HSV 이미지의 각 채널 분리
h, s, v = cv2.split(image_hsv)

# TODO: H 각도를 증가시켜 색상 변경 (360도 초과하지 않도록 유의)
h = (h + 90) % 360

# TODO: 각 채널을 cv2.merge([h, s, v])로 결합
image_merged = cv2.merge([h, s, v])

# TODO: 색공간을 다시 변환하여 이미지 출력
image_merged = cv2.cvtColor(image_merged, cv2.COLOR_HSV2RGB)
plt.imshow(image_merged)
plt.axis("off");

# ==========================================================

image = skimage.data.astronaut()
image = image.astype(np.float32) / 255.

# TODO: 이미지를 HSV 색공간으로 변환
image_hsv = cv2.cvtColor(image, cv2.COLOR_RGB2HSV)

# TODO: HSV 이미지의 각 채널 분리
h, s, v = cv2.split(image_hsv)

# TODO: S 값에 배율을 적용하여 채도 감쇠
s = s * 0.5

# TODO: np.clip(s, 0, 1)을 사용하여 최소/최대값 설정
s = np.clip(s, 0, 1)

# TODO: 각 채널을 cv2.merge([h, s, v])로 결합
image_merged = cv2.merge([h, s, v])

# TODO: 색공간을 다시 변환하여 이미지 출력
image_merged = cv2.cvtColor(image_merged, cv2.COLOR_HSV2RGB)
plt.imshow(image_merged)
plt.axis("off");

# ==========================================================

image = skimage.data.astronaut()
image = image.astype(np.float32) / 255.

# TODO: 이미지를 HSV 색공간으로 변환
image_hsv = cv2.cvtColor(image, cv2.COLOR_RGB2HSV)

# TODO: HSV 이미지의 각 채널 분리
h, s, v = cv2.split(image_hsv)

# TODO: V 값에 배율을 적용하여 명도 증폭
v = v * 2

# TODO: np.clip(v, 0, 1)을 사용하여 최소/최대값 설정
v = np.clip(v, 0, 1)

# TODO: 각 채널을 cv2.merge([h, s, v])로 결합
image_merged = cv2.merge([h, s, v])

# TODO: 색공간을 다시 변환하여 이미지 출력
image_merged = cv2.cvtColor(image_merged, cv2.COLOR_HSV2RGB)
plt.imshow(image_merged)
plt.axis("off");

# ==========================================================

image = skimage.data.astronaut()
image = image.astype(np.float32) / 255.

# TODO: 기존 sharpening kernel 포함하여 총 3가지 kernel을 적용한 결과를 원본 이미지와 함께 비교하는 subplot 생성
sharp_kernel_0 = np.array([[0, -1, 0],
                         [-1, 5, -1],
                         [0, -1, 0]], dtype=np.float32)

sharp_kernel_1 = np.array([[-1, -1, -1],
                         [-1, 9, -1],
                         [-1, -1, -1]], dtype=np.float32)

sharp_kernel_2 = np.array([[-2, -2, -2],
                         [-2, 17, -2],
                         [-2, -2, -2]], dtype=np.float32)

# sharp_kernel_2 = sharp_kernel_2 / 9

sharpened_0 = cv2.filter2D(image, cv2.CV_32F, sharp_kernel_0)
sharpened_1 = cv2.filter2D(image, cv2.CV_32F, sharp_kernel_1)
sharpened_2 = cv2.filter2D(image, cv2.CV_32F, sharp_kernel_2)

sharpened_0 = np.clip(sharpened_0, 0, 1)
sharpened_1 = np.clip(sharpened_1, 0, 1)
sharpened_2 = np.clip(sharpened_2, 0, 1)

plt.figure(figsize=(18,8))

plt.subplot(1,4,1), plt.imshow(image), plt.title('original')
plt.subplot(1,4,2), plt.imshow(sharpened_0), plt.title('sharp_kernel_0')
plt.subplot(1,4,3), plt.imshow(sharpened_1), plt.title('sharp_kernel_1')
plt.subplot(1,4,4), plt.imshow(sharpened_2), plt.title('sharp_kernel_2')

for ax in plt.gcf().axes:
    ax.axis("off")

# ==========================================================

image = skimage.data.astronaut()
image = image.astype(np.float32) / 255.

# TODO: 각 borderType을 적용한 결과 이미지와 제목이 적혀있는 subplot 생성

kernel_size = (101, 101)

border_types = [
    (cv2.BORDER_CONSTANT, "CONSTANT"),
    (cv2.BORDER_REFLECT, "REFLECT"),
    (cv2.BORDER_REFLECT_101, "REFLECT_101"),
    (cv2.BORDER_REPLICATE, "REPLICATE"),
]

plt.figure(figsize=(18,8))

# TODO: enumerate과 for loop을 사용하여 효율적으로 subplot 생성

border_types = enumerate(border_types, start=1)

for idx, (code, name) in border_types:
    plt.subplot(1, 4, idx), plt.imshow(cv2.blur(image, kernel_size, borderType=code)), plt.title(name)

for ax in plt.gcf().axes:
    ax.axis("off")

# ==========================================================

img_path = 'src/images/sky.png'
sky_img = cv2.imread(img_path)

plt.figure(figsize=(5,10))

sky_img = cv2.cvtColor(sky_img, cv2.COLOR_BGR2RGB)

# TODO: 원본 이미지 확인
plt.imshow(sky_img)
plt.axis("off");

# TODO: 이미지를 grayscale로 변환
sky_img_gray = cv2.cvtColor(sky_img, cv2.COLOR_RGB2GRAY)

# TODO: 이미지를 float32로 변환
sky_img_gray = sky_img_gray.astype(np.float32) / 255.

# TODO: Gaussian Filter 적용 (Kernel 사이즈는 55x55)
sky_blur = cv2.GaussianBlur(sky_img_gray, (55, 55), 0)

# TODO: cv2.subtract를 사용하여 원본에서 저주파 성분 차감 (High-pass Filter)
sky_hf = cv2.subtract(sky_img_gray, sky_blur)

# TODO: 고주파 이미지 확인 (cmap 설정)
plt.figure(figsize=(5,10))
plt.imshow(sky_hf, cmap="gray")
plt.axis("off");

# TODO: cv2.add를 사용하여 원본과 고주파 이미지를 합산
unsharp_mask_applied = cv2.add(sky_img_gray, sky_hf)

# 더했으므로 1.0을 넘을 수도 있으므로 clip을 해준다!
unsharp_mask_applied = np.clip(unsharp_mask_applied, 0, 1)

# TODO: subplot 3개 (원본 흑백 이미지, 고주파 이미지, unsharp mask 적용된 이미지) 생성
plt.figure(figsize=(16,8))
plt.subplot(1, 3, 1), plt.imshow(sky_img_gray, cmap="gray"), plt.title("Original")
plt.subplot(1, 3, 2), plt.imshow(sky_hf, cmap="gray"), plt.title("High Frequency")
plt.subplot(1, 3, 3), plt.imshow(unsharp_mask_applied, cmap="gray"), plt.title("Unsharp Mask Applied")

for ax in plt.gcf().axes:
    ax.axis("off")
