"""CNN 기초: 갈매기 이미지에 smoothing/sharpening 필터를 적용한다."""

import cv2
import matplotlib.pyplot as plt
import numpy as np


IMAGE_PATH = "../src/images/seagull.jpg"


def relu(x):
    """입력 배열에서 음수를 0으로 바꾼다."""

    return np.maximum(0, x)


def convolution2d(image, kernel, bias=0.0, stride=1, padding=0):
    """2차원 이미지에 하나의 CNN 필터와 편향을 적용한다."""

    image_height, image_width = image.shape
    kernel_height, kernel_width = kernel.shape

    padded_image = np.pad(
        image,
        ((padding, padding), (padding, padding)),
        mode="constant",
        constant_values=0,
    )

    # floor((H + 2P - K) / S) + 1과 같은 계산이다.
    output_height = (padded_image.shape[0] - kernel_height) // stride + 1
    output_width = (padded_image.shape[1] - kernel_width) // stride + 1
    output = np.zeros((output_height, output_width), dtype=np.float32)

    for output_y in range(output_height):
        for output_x in range(output_width):
            start_y = output_y * stride
            start_x = output_x * stride
            image_region = padded_image[
                start_y : start_y + kernel_height,
                start_x : start_x + kernel_width,
            ]
            weighted_sum = np.sum(image_region * kernel)
            output[output_y, output_x] = weighted_sum + bias

    return output


def main():
    img_bgr = cv2.imread(IMAGE_PATH)
    img_gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    input_image = img_gray.astype(np.float32) / 255.0

    # TODO: Smoothing/Sharpening 필터 정의
    smoothing_filter = np.array(
        [
            [1, 2, 1],
            [2, 4, 2],
            [1, 2, 1],
        ],
        dtype=np.float32,
    )
    sharpening_filter = np.array(
        [
            [-1, -1, -1],
            [-1, 9, -1],
            [-1, -1, -1],
        ],
        dtype=np.float32,
    )

    # TODO: Smoothing/Sharpening 필터 정규화 (필터 정의에서 이미 정규화 하였다면 스킵)
    smoothing_filter = smoothing_filter / np.sum(smoothing_filter)
    sharpening_filter = sharpening_filter / np.sum(sharpening_filter)

    # TODO: Smoothing/Sharpening 편향 정의
    smoothing_bias = 0.0
    sharpening_bias = 0.0

    # TODO: convolution2d 함수를 사용하여 가중치와 편향 적용
    smoothing_output = convolution2d(
        image=input_image,
        kernel=smoothing_filter,
        bias=smoothing_bias,
        stride=1,
        padding=1,
    )
    sharpening_output = convolution2d(
        image=input_image,
        kernel=sharpening_filter,
        bias=sharpening_bias,
        stride=1,
        padding=1,
    )

    # TODO: 활성화 함수 적용 (필요할 시)
    smoothing_feature_map = relu(smoothing_output) # Smoothing은 ReLU 효과가 크지 않다. (음수가 되지 않으므로)
    sharpening_feature_map = relu(sharpening_output) # Sharpening은 ReLU 효과가 크다. (음수가 되므로)

    # 결과 시각화
    plt.figure(figsize=(18, 8))

    plt.subplot(2, 3, 1)
    plt.imshow(input_image, cmap="gray")
    plt.title("Input Image")

    plt.subplot(2, 3, 2)
    plt.imshow(smoothing_output, cmap="gray", vmin=0, vmax=1)
    plt.title("Smoothing: Convolution")

    plt.subplot(2, 3, 3)
    plt.imshow(smoothing_feature_map, cmap="gray", vmin=0, vmax=1)
    plt.title("Smoothing: Convolution + ReLU")

    plt.subplot(2, 3, 4)
    plt.imshow(input_image, cmap="gray")
    plt.title("Input Image")

    plt.subplot(2, 3, 5)
    plt.imshow(sharpening_output, cmap="gray", vmin=0, vmax=1)
    plt.title("Sharpening: Convolution")

    plt.subplot(2, 3, 6)
    plt.imshow(sharpening_feature_map, cmap="gray", vmin=0, vmax=1)
    plt.title("Sharpening: Convolution + ReLU")

    for axis in plt.gcf().axes:
        axis.axis("off")

    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    main()
