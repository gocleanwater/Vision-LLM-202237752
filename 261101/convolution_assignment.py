"""2차원 Convolution 연산을 NumPy와 CuPy로 각각 계산한다."""

import time

import cv2
import cupy as cp
import matplotlib.pyplot as plt
import numpy as np


IMAGE_PATH = "../src/images/seagull.jpg"
TARGET_WIDTH = 1280
TARGET_HEIGHT = 720


def relu(x):
    return np.maximum(0, x)


def convolution2d(image, kernel, bias=0.0, stride=1, padding=0):
    """NumPy를 이용한 2차원 convolution."""

    image_height, image_width = image.shape
    kernel_height, kernel_width = kernel.shape

    padded_image = np.pad(
        image,
        ((padding, padding), (padding, padding)),
        mode="constant",
        constant_values=0,
    )

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


# TODO: CuPy를 사용하여 2차원 convolution 함수 정의

def convolution2d_cp(image, kernel, bias=0.0, stride=1, padding=0):
    """
    CuPy를 이용한 2차원 convolution.

    커널의 위치는 Python 반복문으로 순차 처리하고,
    각 위치에 해당하는 출력 배열 전체 연산은 GPU에서 처리한다.
    """

    image_height, image_width = image.shape
    kernel_height, kernel_width = kernel.shape

    padded_image = cp.pad(
        image,
        ((padding, padding), (padding, padding)),
        mode="constant",
        constant_values=0,
    )

    output_height = (padded_image.shape[0] - kernel_height) // stride + 1
    output_width = (padded_image.shape[1] - kernel_width) // stride + 1
    output = cp.zeros((output_height, output_width), dtype=cp.float32)

    for kernel_y in range(kernel_height):
        for kernel_x in range(kernel_width):
            input_region = padded_image[
                kernel_y : kernel_y + output_height * stride : stride,
                kernel_x : kernel_x + output_width * stride : stride,
            ]
            output += input_region * kernel[kernel_y, kernel_x]

    output += bias

    return output


def main():
    img_gray = cv2.imread(IMAGE_PATH, cv2.IMREAD_GRAYSCALE)
    img_gray = cv2.resize(
        img_gray,
        (TARGET_WIDTH, TARGET_HEIGHT),
        interpolation=cv2.INTER_AREA,
    )
    input_np = img_gray.astype(np.float32) / 255.0

    dx_edge_filter = np.array(
        [
            [-1, 0, 1],
            [-1, 0, 1],
            [-1, 0, 1],
        ],
        dtype=np.float32,
    )
    dy_edge_filter = np.array(
        [
            [-1, -1, -1],
            [0, 0, 0],
            [1, 1, 1],
        ],
        dtype=np.float32,
    )
    dx_bias = -0.2
    dy_bias = -0.2

    # TODO: 기존에 정의한 convolution2d 함수를 사용하여 convolution을 CPU로 처리
    # TODO: 변수 재사용 가능

    cpu_start = time.perf_counter()

    output_dx_np = convolution2d(
        image=input_np,
        kernel=dx_edge_filter,
        bias=dx_bias,
        stride=1,
        padding=1,
    )
    output_dy_np = convolution2d(
        image=input_np,
        kernel=dy_edge_filter,
        bias=dy_bias,
        stride=1,
        padding=1,
    )

    cpu_time = time.perf_counter() - cpu_start

    relu_dx_np = relu(output_dx_np)
    relu_dy_np = relu(output_dy_np)

    # TODO: convolution을 GPU로 처리 (변환-워밍업-처리 파이프라인 구현)
    # TODO: 변수 재사용 가능

    input_cp = cp.asarray(input_np)
    dx_edge_filter_cp = cp.asarray(dx_edge_filter)
    dy_edge_filter_cp = cp.asarray(dy_edge_filter)

    warmup_image = cp.zeros((64, 64), dtype=cp.float32)
    _ = convolution2d_cp(
        image=warmup_image,
        kernel=dx_edge_filter_cp,
        bias=dx_bias,
        stride=1,
        padding=1,
    )
    cp.cuda.Stream.null.synchronize()

    cp.cuda.Stream.null.synchronize()
    gpu_start = time.perf_counter()

    output_dx_cp = convolution2d_cp(
        image=input_cp,
        kernel=dx_edge_filter_cp,
        bias=dx_bias,
        stride=1,
        padding=1,
    )
    output_dy_cp = convolution2d_cp(
        image=input_cp,
        kernel=dy_edge_filter_cp,
        bias=dy_bias,
        stride=1,
        padding=1,
    )

    cp.cuda.Stream.null.synchronize()
    gpu_time = time.perf_counter() - gpu_start

    output_dx_cp_np = cp.asnumpy(output_dx_cp)
    output_dy_cp_np = cp.asnumpy(output_dy_cp)
    relu_dx_cp_np = relu(output_dx_cp_np)
    relu_dy_cp_np = relu(output_dy_cp_np)

    # TODO: CPU/GPU 결과 비교 및 출력

    print("========== NumPy CPU ==========")
    print(f"Convolution time: {cpu_time:.4f} seconds")
    print()

    print("========== CuPy GPU ==========")
    print(f"Convolution time: {gpu_time:.4f} seconds")
    print()

    print("========== Comparison ==========")
    print(f"Speedup: {cpu_time / gpu_time:.2f}x")
    print("Vertical result same:", np.allclose(output_dx_np, output_dx_cp_np))
    print("Horizontal result same:", np.allclose(output_dy_np, output_dy_cp_np))

    plt.figure(figsize=(18, 8))

    plt.subplot(2, 3, 1), plt.imshow(input_np, cmap="gray"), plt.title("Input Image")
    plt.subplot(2, 3, 2), plt.imshow(relu_dx_np, cmap="gray"), plt.title("Vertical Convolution (CPU)")
    plt.subplot(2, 3, 3), plt.imshow(relu_dx_cp_np, cmap="gray"), plt.title("Vertical Convolution (GPU)")
    plt.subplot(2, 3, 4), plt.imshow(input_np, cmap="gray"), plt.title("Input Image")
    plt.subplot(2, 3, 5), plt.imshow(relu_dy_np, cmap="gray"), plt.title("Horizontal Convolution (CPU)")
    plt.subplot(2, 3, 6), plt.imshow(relu_dy_cp_np, cmap="gray"), plt.title("Horizontal Convolution (GPU)")

    for ax in plt.gcf().axes:
        ax.axis("off")

    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    main()
