# Vision-LLM 필기고사 이론 정리

> 핵심 범위: `02_Computer-Vision.ipynb`, `03_DL-and-GPU.ipynb`, `04_DL-Object-Detection.ipynb`의 **마크다운 이론**
> 보조 범위: `00_Initial-Setup.ipynb`, `01_Linux-and-Python.ipynb`의 개념 부분  
> 설치 명령, 함수 사용법, 코드 작성법, 실습 순서는 제외하고 **정의·원리·과정·비교·공식**만 정리했다.

---

# 1. Computer Vision의 전체 구조

Computer Vision은 이미지나 영상에서 의미 있는 정보를 얻는 기술이다. 전체 흐름은 크게 다음과 같이 나눌 수 있다.

1. **이미지 전처리**
   - 이미지의 크기, 방향, 픽셀값을 조정한다.
   - 색공간을 목적에 맞게 변환한다.
   - 노이즈를 제거하거나 대비를 향상한다.
2. **특징 추출**
   - 색상, Edge, Contour, Corner와 같이 객체를 구분할 수 있는 정보를 찾는다.
3. **객체 검출**
   - 현재 이미지에서 원하는 객체의 위치와 크기를 찾는다.
4. **객체 추적**
   - 여러 프레임에 걸쳐 객체의 움직임을 연결하고 다음 상태를 예측한다.

핵심 관계:

$$
전처리 \rightarrow 특징\ 추출 \rightarrow 객체\ 검출 \rightarrow 객체\ 추적
$$

전처리가 부정확하면 이후의 특징 추출과 객체 검출도 불안정해진다. 즉, 각 단계는 독립적이지 않고 앞 단계의 결과에 영향을 받는다.

---

# 2. 디지털 이미지의 기본 이론

## 2.1 이미지는 픽셀 배열이다

디지털 이미지는 픽셀을 일정한 격자로 배치한 배열이다.

- 컬러 이미지의 일반적인 구조: **높이 × 너비 × 채널**, 즉 `(H, W, C)`
- 배열 표현: `[row, column, channel]`
- RGB 이미지의 채널 수: 3개
- 각 픽셀은 해당 위치의 색상 또는 밝기 정보를 저장한다.

이미지 좌표의 원점은 일반적인 수학 좌표와 다르게 **왼쪽 위**에 있다.

- row가 증가하면 아래쪽으로 이동한다.
- column이 증가하면 오른쪽으로 이동한다.

## 2.2 픽셀값과 자료형

일반적인 8비트 이미지는 각 채널의 값을 `0~255` 범위의 정수로 표현한다.

- `0`: 가장 어두운 값
- `255`: 가장 밝은 값
- 대표 자료형: `uint8`

딥러닝이나 수치 연산에서는 픽셀을 `0.0~1.0` 범위의 실수로 바꾸기도 한다. 이때 자료형만 실수로 바꾸는 것이 아니라 값을 255로 나누는 **스케일링**이 필요하다.

## 2.3 Indexing과 Slicing의 의미

- **Indexing**: 배열에서 하나의 픽셀이나 특정 채널을 선택한다.
- **Slicing**: 배열의 연속된 범위를 선택한다.
- 이미지에서 Slicing은 특정 영역만 잘라내는 Crop과 같은 의미를 가진다.

---

# 3. 색공간(Color Space)

## 3.1 색공간의 정의

색공간은 색을 수치로 표현하는 기준이다.

- 같은 색도 색공간에 따라 서로 다른 채널과 값으로 표현된다.
- 처리 목적에 따라 적절한 색공간이 달라진다.
- 색공간을 변환하면 색상 분할, 밝기 보정, 특징 추출을 더 쉽게 수행할 수 있다.

## 3.2 RGB와 BGR

RGB와 BGR은 모두 빨강·초록·파랑 채널을 사용하지만 채널 순서가 다르다.

- RGB: Red → Green → Blue
- BGR: Blue → Green → Red

OpenCV는 일반적으로 BGR 순서를 사용하고 Matplotlib은 RGB 순서를 사용한다. BGR 이미지를 RGB라고 해석하면 빨강과 파랑이 바뀐 것처럼 보인다.

핵심은 색 자체가 달라진 것이 아니라 **채널의 해석 순서가 달라진 것**이다.

## 3.3 Grayscale

Grayscale은 색상 정보를 제거하고 밝기만 표현한다.

RGB 세 채널을 단순히 평균하는 것이 아니라 인간의 시각이 각 색의 밝기를 다르게 느끼는 특성을 반영한다.

$$
Gray = 0.299R + 0.587G + 0.114B
$$

초록색의 가중치가 가장 큰 이유는 인간의 눈이 초록 계열의 밝기 변화에 상대적으로 민감하기 때문이다.

Grayscale의 장점:

- 색상 정보가 불필요한 문제에서 데이터량을 줄일 수 있다.
- Edge나 형태처럼 밝기 변화가 중요한 특징에 집중할 수 있다.

## 3.4 HSV

HSV는 색을 색상, 채도, 명도로 분리한다.

- **H(Hue)**: 어떤 색인가
- **S(Saturation)**: 색이 얼마나 선명한가
- **V(Value)**: 색이 얼마나 밝은가

HSV의 장점은 색상과 밝기가 어느 정도 분리된다는 것이다. 따라서 RGB보다 특정 색상 범위를 직관적으로 지정하기 쉽다.

OpenCV의 8비트 표현 범위:

- H: `0~179`
- S: `0~255`
- V: `0~255`

Hue는 원형으로 순환한다. 일반적인 각도에서 0°와 360°가 같은 방향인 것처럼 Hue의 시작과 끝은 서로 연결된다. 빨강이 Hue 범위 양쪽에 걸쳐 있는 이유도 이 때문이다.

HSV의 한계:

- V는 해당 색의 밝기 성분이지만 인간이 체감하는 지각 밝기와 완전히 같지는 않다.
- 조명 변화가 매우 크면 같은 물체의 HSV 값도 달라질 수 있다.

## 3.5 LAB

LAB는 인간의 색 지각을 반영한 비선형 색공간이다.

- **L\***: 지각 밝기
- **a\***: 초록 ↔ 빨강
- **b\***: 파랑 ↔ 노랑

개념적인 범위:

- L\*: `0~100`
- a\*: 약 `-128~127`
- b\*: 약 `-128~127`

LAB에서는 밝기와 색상 축이 분리되어 있으므로 밝기만 조절하면서 색 정보의 변형을 줄일 수 있다. 이 때문에 조명 오염이 있는 이미지의 대비 향상이나 색상 분할에 유용하다.

## 3.6 색공간 비교

| 색공간 | 채널 의미 | 장점 | 주요 한계 |
|---|---|---|---|
| RGB/BGR | 빨강·초록·파랑 | 이미지 표현에 기본적 | 색과 밝기가 섞여 있어 범위 지정이 어려울 수 있음 |
| Grayscale | 밝기 | 데이터가 단순하고 형태 분석에 유리 | 색상 정보가 사라짐 |
| HSV | 색상·채도·명도 | 특정 색을 직관적으로 분리하기 쉬움 | V가 지각 밝기와 같지 않고 조명 변화에 영향받음 |
| LAB | 지각 밝기·녹/적·청/황 | 밝기와 색상 분리, 조명 보정에 유리 | 채널 의미가 상대적으로 직관적이지 않음 |

---

# 4. 필터링과 Convolution

## 4.1 필터링의 정의

필터링은 이미지에서 불필요한 성분을 제거하거나 원하는 특징을 강조하는 처리다.

- 노이즈 제거
- Blur
- Edge 강조
- 특징 추출

필터링은 작은 행렬인 **Kernel(Filter)**을 이미지 위에서 이동시키며 수행한다.

## 4.2 Convolution의 원리

Kernel이 이미지의 한 영역과 겹쳤을 때 다음 과정을 수행한다.

1. 이미지 영역과 Kernel의 대응하는 값을 곱한다.
2. 모든 곱을 더한다.
3. 합을 출력 이미지의 한 픽셀로 저장한다.
4. Kernel을 이동해 같은 연산을 반복한다.

따라서 Kernel 값이 어떤 형태인지에 따라 Blur, Sharpening, Edge Detection 등 서로 다른 효과가 나타난다.

## 4.3 Smoothing과 Sharpening

- **Smoothing**: 작은 변화와 노이즈를 줄여 이미지를 부드럽게 만든다.
- **Sharpening**: 급격한 밝기 변화와 세부 특징을 강조해 이미지를 선명하게 만든다.

두 연산은 주파수 관점에서 서로 반대되는 성격을 가진다.

- Smoothing: 고주파 억제
- Sharpening: 고주파 강조

## 4.4 Box Filter

Box Filter는 Kernel 안의 모든 픽셀에 같은 가중치를 적용해 평균을 구한다.

특징:

- 계산이 단순하고 빠르다.
- 모든 주변 픽셀을 동일하게 취급한다.
- Kernel이 커지면 Blur가 각지거나 모자이크처럼 보일 수 있다.

## 4.5 Gaussian Filter

Gaussian Filter는 중심 픽셀에 큰 가중치를 주고 중심에서 멀어질수록 가중치를 부드럽게 줄인다.

특징:

- Box Filter보다 자연스러운 Blur를 만든다.
- 노이즈 제거와 Edge Detection 전처리에 널리 사용된다.
- Box Filter보다 계산이 복잡하다.

## 4.6 Sharpening Filter

Sharpening Filter는 주변 픽셀과의 차이를 강조한다. 밝기가 급격히 변하는 부분, 즉 Edge와 세부 질감이 강해진다.

Sharpening을 지나치게 적용하면 노이즈도 함께 강조될 수 있다. 이는 노이즈 역시 고주파 성분이기 때문이다.

## 4.7 Border 처리

Kernel이 이미지 가장자리에 도달하면 이미지 밖의 값이 필요하다. 이때 가상의 픽셀을 어떤 방식으로 채울지 결정하는 것이 Border 처리다.

대표적인 방식:

- 일정한 상수값으로 채우기
- 가장자리 값을 반복하기
- 이미지를 반사한 것처럼 확장하기

Border 방식의 차이는 주로 이미지 가장자리의 필터링 결과에 나타난다.

## 4.8 Box Filter와 Gaussian Filter 비교

| 구분 | Box Filter | Gaussian Filter |
|---|---|---|
| 가중치 | 모두 동일 | 중심이 크고 멀어질수록 감소 |
| 계산량 | 상대적으로 작음 | 상대적으로 큼 |
| Blur | 각지거나 인공적일 수 있음 | 자연스럽고 부드러움 |
| 주요 장점 | 빠른 평균화 | 안정적인 Smoothing |

---

# 5. 이미지 주파수와 Edge Detection

## 5.1 이미지 주파수

이미지 주파수는 공간에 따라 픽셀값이 얼마나 빠르게 변하는지를 의미한다.

### 저주파(Low Frequency)

- 픽셀값이 천천히 변하는 성분
- 하늘, 벽, 피부, 부드러운 음영
- 이미지의 전체적인 형태와 넓은 영역

### 고주파(High Frequency)

- 픽셀값이 빠르게 변하는 성분
- Edge, 무늬, 질감, 거친 표면
- 노이즈도 고주파에 포함될 수 있다.

## 5.2 LPF와 HPF

### Low-pass Filter

- 저주파를 통과시키고 고주파를 억제한다.
- Edge와 노이즈가 약해져 이미지가 흐려진다.
- Box Filter와 Gaussian Filter가 대표적이다.

### High-pass Filter

- 고주파를 통과시키고 저주파를 억제한다.
- Edge와 세부 특징이 강조된다.
- 노이즈도 함께 강조될 수 있다.

## 5.3 Residual Extraction

원본 이미지에서 저주파 이미지를 빼면 고주파 성분이 남는다.

$$
High\ Frequency = Original - Low\ Frequency
$$

여기서 저주파 이미지는 보통 Gaussian Filter로 만든다. 남은 Residual에는 Edge, 질감, 노이즈와 같은 빠른 변화가 포함된다.

## 5.4 Unsharp Masking

Residual Extraction으로 얻은 고주파 성분을 원본에 더해 Edge를 강조하는 방법이다.

$$
Sharpened = Original + High\ Frequency
$$

이름에는 `Unsharp`가 들어가지만 실제 목적은 이미지를 더 선명하게 만드는 것이다.

## 5.5 Sobel Filter

Sobel Filter는 이미지 밝기의 변화율, 즉 Gradient를 이용해 Edge를 검출한다.

- x방향 미분 `dx`: 좌우 방향의 밝기 변화를 측정하여 **세로 Edge**를 검출한다.
- y방향 미분 `dy`: 상하 방향의 밝기 변화를 측정하여 **가로 Edge**를 검출한다.

전체 Edge 강도:

$$
Magnitude = \sqrt{dx^2 + dy^2}
$$

Sobel의 장점:

- 계산이 빠르다.
- Edge의 강도와 방향을 얻을 수 있다.

Sobel의 단점:

- 노이즈에 민감하다.
- Edge가 두껍게 나타날 수 있다.

## 5.6 Canny Edge Detection

Canny는 노이즈를 줄이면서 얇고 정확한 Edge를 찾는 다단계 알고리즘이다.

### 처리 과정

1. **Gaussian Smoothing**
   - 노이즈를 제거한다.
   - 노이즈를 그대로 미분하면 가짜 Edge가 많이 생길 수 있다.
2. **Sobel Filter**
   - Gradient의 크기와 방향을 계산한다.
   - 아직 Edge 후보가 두껍게 존재한다.
3. **Non-Maximum Suppression(NMS)**
   - Gradient 방향을 기준으로 주변과 비교한다.
   - 국소 최댓값만 남겨 Edge를 한 픽셀에 가깝게 얇게 만든다.
4. **Hysteresis Thresholding**
   - 높은 임계값보다 큰 픽셀은 강한 Edge로 유지한다.
   - 낮은 임계값보다 작은 픽셀은 제거한다.
   - 중간 범위의 픽셀은 강한 Edge와 연결된 경우에만 유지한다.

### Sobel과 Canny 비교

| 구분 | Sobel | Canny |
|---|---|---|
| 구성 | Gradient 계산 | Smoothing → Gradient → NMS → 이중 임계값 |
| Edge 두께 | 비교적 두꺼움 | 얇음 |
| 노이즈 영향 | 큼 | 상대적으로 작음 |
| 계산 복잡도 | 낮음 | 높음 |

---

# 6. Color Segmentation과 Binary Mask

## 6.1 Color Segmentation

Color Segmentation은 특정 색상 범위에 속하는 픽셀만 분리하는 기법이다.

결과는 보통 Binary Mask로 표현한다.

- 원하는 영역: 흰색 또는 1
- 나머지 영역: 검정 또는 0

## 6.2 Thresholding

Thresholding은 값이 설정한 범위 안에 있는지에 따라 픽셀을 두 종류로 나누는 과정이다.

$$
Mask(x,y)=
\begin{cases}
1, & Lower \le I(x,y) \le Upper\\
0, & otherwise
\end{cases}
$$

색상 분할의 품질은 다음 요소에 영향을 받는다.

- 색공간 선택
- 하한과 상한 범위
- 조명 변화
- 카메라 노이즈
- 객체와 배경의 색상 유사도

## 6.3 빨강을 두 범위로 검출하는 이유

Hue는 원형 값이다. 빨강은 Hue의 시작 부분과 끝부분에 걸쳐 있으므로 하나의 연속된 숫자 범위로 표현하기 어렵다. 따라서 두 개의 범위를 각각 검출하고 합친다.

## 6.4 Binary Mask의 노이즈

Thresholding 결과에는 작은 흰색 점, 객체 내부의 검정 구멍, 끊어진 경계가 생길 수 있다. Blur를 사용하면 작은 변화가 줄어들지만 너무 강하면 객체 경계와 세부 정보까지 사라진다.

따라서 Binary Mask에는 Smoothing뿐 아니라 Morphological Operation을 함께 사용하는 경우가 많다.

---

# 7. Morphological Operation

Morphological Operation은 Binary Mask의 형태를 Kernel로 변형하는 연산이다. 흰색 영역을 객체로 본다.

## 7.1 Erosion(침식)

Kernel 범위의 픽셀이 모두 흰색일 때만 중심 픽셀을 흰색으로 유지한다.

- 논리적인 AND와 비슷하다.
- 흰색 영역이 줄어든다.
- 작은 흰색 노이즈가 제거된다.
- 객체의 가는 부분도 함께 사라질 수 있다.

## 7.2 Dilation(팽창)

Kernel 범위에 흰색 픽셀이 하나라도 있으면 중심 픽셀을 흰색으로 만든다.

- 논리적인 OR와 비슷하다.
- 흰색 영역이 커진다.
- 객체 내부의 작은 검정 구멍이 줄어든다.
- 가까운 흰색 영역이 연결될 수 있다.

## 7.3 Opening(열기)

$$
Opening = Erosion \rightarrow Dilation
$$

먼저 작은 흰색 노이즈를 침식으로 제거하고, 이후 팽창으로 주요 객체의 크기를 대체로 복원한다.

주요 목적: **객체 바깥의 작은 흰색 노이즈 제거**

## 7.4 Closing(닫기)

$$
Closing = Dilation \rightarrow Erosion
$$

먼저 흰색 영역을 팽창해 내부 구멍과 끊어진 부분을 연결하고, 이후 침식으로 주요 객체의 크기를 대체로 복원한다.

주요 목적: **객체 내부의 검정 구멍과 끊어진 영역 연결**

## 7.5 네 연산 비교

| 연산 | 원리 | 흰색 영역 | 대표 목적 |
|---|---|---|---|
| Erosion | 모두 흰색일 때 유지 | 축소 | 작은 흰색 노이즈 제거 |
| Dilation | 하나라도 흰색이면 확장 | 확대 | 검정 구멍과 끊김 감소 |
| Opening | 침식 → 팽창 | 대체로 복원 | 외부 흰색 노이즈 제거 |
| Closing | 팽창 → 침식 | 대체로 복원 | 내부 구멍과 끊김 연결 |

---

# 8. Image Enhancement와 CLAHE

## 8.1 Image Enhancement

Image Enhancement는 이미지의 대비와 시각적 정보를 개선해 특징 추출을 쉽게 만드는 과정이다.

Color Segmentation은 조명 변화에 민감하다. 같은 물체라도 밝은 부분과 어두운 부분의 색상값이 달라지기 때문이다. 대비를 개선하면 객체와 배경의 차이가 커져 분할이 쉬워질 수 있다.

## 8.2 Histogram Equalization(HE)

히스토그램은 밝기값별 픽셀 수의 분포다. Histogram Equalization은 밝기 분포가 더 넓게 퍼지도록 재배치해 전체 대비를 높인다.

한계:

- 이미지 전체에 같은 변환을 적용한다.
- 일부 영역이 지나치게 밝거나 어두워질 수 있다.
- 지역적인 밝기 차이를 충분히 반영하지 못한다.

## 8.3 Adaptive Histogram Equalization(AHE)

AHE는 이미지를 작은 영역으로 나누고 각 영역의 히스토그램을 따로 평활화한다.

장점:

- 지역적인 대비를 강화할 수 있다.

한계:

- 단색 영역의 작은 노이즈까지 강하게 증폭할 수 있다.

## 8.4 CLAHE

CLAHE는 **Contrast Limited Adaptive Histogram Equalization**의 약자다.

- 이미지를 작은 영역으로 나누어 국소 대비를 향상한다.
- 히스토그램의 높이에 제한을 둔다.
- 제한을 초과한 빈도는 잘라내고 재분배한다.
- 단색 영역의 노이즈가 지나치게 강조되는 것을 막는다.

발전 관계:

$$
HE \rightarrow AHE \rightarrow CLAHE
$$

- HE: 전체 이미지의 대비 향상
- AHE: 지역별 대비 향상
- CLAHE: 지역별 대비 향상 + 과도한 증폭 제한

LAB의 L\* 채널에 CLAHE를 적용하면 지각 밝기의 대비를 개선하면서 색상 채널의 직접적인 변형을 줄일 수 있다.

---

# 9. Edge, Contour, Interest Point

## 9.1 Edge

Edge는 밝기나 색이 급격하게 변하는 경계 픽셀이다. 객체의 경계 후보를 나타내지만, 반드시 하나의 닫힌 객체 영역을 의미하지는 않는다.

## 9.2 Contour

Contour는 Binary Mask에서 연결된 객체 영역을 따라 형성된 외곽선이다.

Contour의 품질은 Mask의 연결 상태에 영향을 받는다.

- 객체가 끊어져 있으면 Contour도 여러 개로 나뉠 수 있다.
- 노이즈가 많으면 작은 Contour가 많이 생성된다.
- Opening과 Closing으로 Mask를 정리하면 주요 객체의 Contour를 안정적으로 얻을 수 있다.

## 9.3 대표 Contour 선택

여러 Contour 중에서 주요 객체를 선택할 때 면적 또는 둘레를 기준으로 사용할 수 있다.

- 노이즈는 일반적으로 작은 면적을 가진다.
- 주요 객체는 상대적으로 큰 연결 영역을 가진다.
- 따라서 가장 큰 Contour를 선택하면 주요 객체를 찾기 쉬워진다.

단, 가장 큰 영역이 항상 원하는 객체라는 보장은 없으므로 이는 장면에 대한 가정을 포함한다.

## 9.4 Minimum Enclosing Circle

Contour의 모든 점을 포함하는 가장 작은 원이다.

- 객체를 원으로 근사한다.
- 중심과 반지름을 얻을 수 있다.
- 실제 객체가 완전한 원이 아니어도 모든 Contour 점을 포함한다.

## 9.5 Centroid

Centroid는 객체 픽셀 분포의 기하학적 중심이다. 영상 모멘트를 이용해 계산한다.

$$
C_x = \frac{M_{10}}{M_{00}}, \qquad
C_y = \frac{M_{01}}{M_{00}}
$$

- $M_{00}$: 객체의 면적에 해당
- $M_{10}$: x방향 1차 모멘트
- $M_{01}$: y방향 1차 모멘트

Centroid는 중심을 제공하지만 반지름은 제공하지 않는다. 따라서 원형 객체에서는 Centroid와 Minimum Enclosing Circle의 반지름을 함께 사용할 수 있다.

## 9.6 Interest Point

Interest Point는 주변과 구별되는 정보량이 높은 지점이다.

좋은 특징점의 조건:

- 주변과 명확히 구분된다.
- 다른 이미지에서도 다시 찾기 쉽다.
- 크기, 회전, 조명 변화에 비교적 안정적이다.

대표적인 특징점 추출 방법:

- Harris Corner
- SIFT
- ORB

특징점은 이미지 비교, Feature Matching, 객체 추적에 사용된다.

## 9.7 세 개념 비교

| 개념 | 의미 | 주요 목적 |
|---|---|---|
| Edge | 밝기·색의 급격한 변화 | 경계 후보 검출 |
| Contour | 연결된 Binary 영역의 외곽선 | 객체 영역과 형태 분석 |
| Interest Point | 주변과 구별되는 주요 지점 | 이미지 매칭과 추적 |

---

# 10. Harris Corner Detection

## 10.1 Corner의 의미

이미지의 작은 영역을 여러 방향으로 이동했을 때 밝기 변화가 어떻게 나타나는지로 영역을 구분할 수 있다.

- **평탄한 영역**: 어느 방향으로 이동해도 변화가 작다.
- **Edge**: Edge와 수직인 한 방향으로 이동할 때만 변화가 크다.
- **Corner**: 여러 방향으로 이동할 때 변화가 크다.

따라서 Corner는 두 방향에서 모두 Gradient가 큰 지점으로 볼 수 있다.

## 10.2 Harris Corner의 과정

1. Sobel Filter로 x, y 방향 Gradient를 계산한다.
2. $I_x^2$, $I_y^2$, $I_xI_y$를 구한다.
3. Gaussian Filter로 주변 영역의 정보를 모은다.
4. 구조 행렬 $M$을 만든다.
5. Harris Response를 계산한다.
6. Thresholding으로 약한 반응을 제거한다.
7. NMS로 국소 최댓값만 남긴다.

Harris Response:

$$
R = \det(M)-k\,\mathrm{trace}(M)^2
$$

직관적인 해석:

- $R$이 큰 양수: Corner일 가능성이 큼
- $R$이 큰 음수: Edge일 가능성이 큼
- $R$이 0에 가까움: 평탄한 영역일 가능성이 큼

---

# 11. 객체 검출과 추적

## 11.1 Detection과 Tracking

- **Detection**: 현재 프레임에서 객체의 위치를 찾는다.
- **Tracking**: 이전 상태와 현재 측정을 연결해 시간에 따른 움직임을 추정한다.

Detection은 각 프레임을 독립적으로 볼 수 있지만 Tracking은 시간 정보가 필요하다.

| 개념 | 핵심 질문 | 사용하는 정보 |
|---|---|---|
| Detection | 지금 객체가 어디 있는가? | 현재 프레임 |
| Tracking | 객체가 어떻게 움직이고 있는가? | 이전 상태 + 현재 측정 |

## 11.2 Kalman Filter

Kalman Filter는 노이즈가 포함된 측정값으로부터 실제 상태를 추정하는 알고리즘이다.

상태에는 직접 측정하는 값뿐 아니라 속도처럼 내부적으로 추정하는 값도 포함할 수 있다.

예시:

- 상태 벡터: $[x, y, v_x, v_y]$
- 측정 벡터: $[x, y]$

카메라가 위치만 측정해도 이전 위치 변화로 속도를 추정할 수 있다.

### Prediction

- 이전 상태와 상태 전이 모델로 다음 상태를 예측한다.
- 예측의 불확실성도 함께 증가시킨다.

### Update 또는 Correction

- 새로운 측정값과 예측값을 비교한다.
- 예측과 측정의 불확실성을 고려해 두 정보를 결합한다.
- 측정값이 신뢰할 만하면 측정 쪽으로, 노이즈가 크면 예측 쪽으로 더 가깝게 보정한다.

### 주요 행렬의 의미

- **Transition Matrix**: 상태가 시간에 따라 어떻게 변하는지 표현
- **Measurement Matrix**: 상태 중 센서가 관측하는 항목을 표현
- **Process Noise Covariance**: 이동 모델의 불확실성
- **Measurement Noise Covariance**: 측정값의 불확실성
- **Error Covariance**: 현재 상태 추정의 불확실성

### Kalman Filter의 장점

- 측정 노이즈를 줄인다.
- 객체가 잠시 가려져도 예측을 이어 갈 수 있다.
- 불안정한 검출 결과를 부드럽게 만든다.
- 위치와 속도 등을 함께 추정할 수 있다.

## 11.3 MediaPipe와 Landmark

MediaPipe는 손, 얼굴, 자세 등의 의미 있는 지점을 Landmark로 검출한다.

- Landmark: 관절이나 손가락 끝처럼 의미 있는 좌표
- Connection: Landmark 사이의 해부학적 연결 관계
- Skeleton: Landmark와 Connection을 함께 표현한 구조

Landmark 검출 결과에 사람이 만든 규칙을 적용할 수 있다. 예를 들어 세 관절점이 이루는 각도로 손가락의 펴짐 여부를 판단하는 것은 **Rule-based System**이다.

두 벡터 사이의 각도:

$$
\cos\theta = \frac{\vec{a}\cdot\vec{b}}{\|\vec{a}\|\|\vec{b}\|}
$$

각도가 180°에 가까울수록 관절이 비교적 곧게 펴진 상태다.

---

# 12. 딥러닝과 인공신경망

## 12.1 딥러닝

딥러닝은 여러 층의 인공신경망을 이용해 데이터에서 복잡한 패턴을 학습하는 기술이다.

규칙 기반 방식에서는 사람이 판단 규칙을 직접 만든다. 딥러닝에서는 데이터와 정답을 이용해 모델이 분류에 필요한 가중치와 특징을 학습한다.

## 12.2 인공신경망의 구조

- **입력층(Input Layer)**: 외부 데이터를 받는다.
- **은닉층(Hidden Layer)**: 입력을 변환하며 특징을 학습한다.
- **출력층(Output Layer)**: 최종 예측을 만든다.
- **퍼셉트론(Perceptron)**: 인공신경망을 구성하는 기본 연산 단위다.

---

# 13. 퍼셉트론과 논리 게이트

## 13.1 퍼셉트론

퍼셉트론은 여러 입력에 각각의 가중치를 곱하고 편향을 더한 뒤 활성화 함수를 적용한다.

$$
z = w_1x_1+w_2x_2+\cdots+w_nx_n+b
$$

$$
y=f(z)
$$

- **입력 $x$**: 모델에 주어진 데이터
- **가중치 $w$**: 각 입력이 출력에 미치는 중요도
- **편향 $b$**: 활성화 기준을 이동시키는 값
- **가중합 $z$**: 입력과 가중치의 곱을 더하고 편향을 더한 값
- **활성화 함수 $f$**: 가중합을 최종 출력으로 변환

## 13.2 가중치와 편향의 역할

가중치는 결정 경계의 방향을 조절하고, 편향은 결정 경계의 위치를 이동시킨다.

편향이 없으면 결정 경계가 원점을 지나야 하지만 편향이 있으면 원점과 무관한 위치에 결정 경계를 만들 수 있다.

## 13.3 단층 퍼셉트론(SLP)

단층 퍼셉트론은 입력층과 출력층으로 이루어진다.

- 하나의 선형 결정 경계를 만든다.
- 선형 분리 가능한 문제를 해결한다.
- AND, OR, NAND, NOR는 선형 분리가 가능하다.

## 13.4 XOR 문제

XOR은 두 입력이 서로 다를 때만 1이다. XOR의 두 클래스는 하나의 직선으로 나눌 수 없다.

따라서 단일 퍼셉트론으로는 XOR을 해결할 수 없다.

중요한 결론:

- 데이터가 부족해서가 아니다.
- Epoch가 부족해서가 아니다.
- 모델 구조가 XOR의 비선형 관계를 표현할 수 없기 때문이다.

모델이 문제를 표현할 수 없다면 학습 횟수를 늘려도 해결되지 않는다.

## 13.5 다층 퍼셉트론(MLP)

다층 퍼셉트론은 입력층과 출력층 사이에 하나 이상의 은닉층을 가진다.

- 여러 선형 변환과 비선형 활성화 함수를 조합한다.
- 비선형 결정 경계를 만들 수 있다.
- XOR 같은 비선형 분리 문제를 해결할 수 있다.

XOR은 다음 논리 조합으로도 표현할 수 있다.

$$
XOR(x_1,x_2)=AND(NAND(x_1,x_2),OR(x_1,x_2))
$$

이는 여러 퍼셉트론을 층으로 조합하면 단일 퍼셉트론보다 복잡한 문제를 표현할 수 있음을 보여 준다.

---

# 14. 활성화 함수

활성화 함수는 뉴런의 가중합을 출력 신호로 변환한다. 활성화 함수가 비선형성을 제공해야 여러 층을 쌓았을 때 복잡한 비선형 관계를 표현할 수 있다.

## 14.1 Step Function

$$
f(x)=
\begin{cases}
1, & x\ge0\\
0, & x<0
\end{cases}
$$

특징:

- 출력이 0 또는 1이다.
- 임계값을 기준으로 명확하게 분류한다.
- 대부분의 구간에서 기울기가 0이고 임계점에서 미분하기 어려워 경사하강 기반 학습에 적합하지 않다.

## 14.2 Sigmoid

$$
\sigma(x)=\frac{1}{1+e^{-x}}
$$

특징:

- 출력 범위가 `0~1`이다.
- 이진 분류의 확률처럼 해석하기 쉽다.
- 입력의 절댓값이 커지면 기울기가 매우 작아질 수 있다.
- 깊은 신경망에서는 Gradient Vanishing의 원인이 될 수 있다.

## 14.3 ReLU

$$
ReLU(x)=\max(0,x)
$$

특징:

- 음수는 0으로 만든다.
- 양수는 그대로 통과시킨다.
- 계산이 단순하다.
- 양수 영역에서 Gradient가 유지되어 CNN에서 널리 사용된다.

Convolution 결과에서 양수와 음수는 서로 반대 방향의 패턴을 나타낼 수 있다. ReLU는 그중 양수 반응만 남기므로 Filter와 같은 방향의 특징을 강조한다.

## 14.4 활성화 함수 비교

| 함수 | 출력 | 장점 | 한계 |
|---|---|---|---|
| Step | 0 또는 1 | 단순한 임계 판단 | 미분 기반 학습에 부적합 |
| Sigmoid | 0~1 | 확률 해석에 유리 | 큰 절댓값에서 Gradient가 작아짐 |
| ReLU | 음수 0, 양수 유지 | 계산이 단순하고 CNN 학습에 유리 | 음수 영역의 Gradient가 0 |

---

# 15. 인공신경망의 학습 원리

## 15.1 학습의 의미

신경망 학습은 예측과 정답의 차이를 줄이도록 가중치와 편향을 반복해서 수정하는 과정이다.

$$
입력 \rightarrow 예측 \rightarrow 오차\ 계산 \rightarrow 파라미터\ 수정
$$

## 15.2 Epoch

Epoch는 전체 학습 데이터를 한 번 모두 사용해 학습한 주기다.

- Epoch가 너무 적으면 충분히 학습하지 못해 Underfitting이 발생할 수 있다.
- Epoch가 너무 많으면 학습 데이터를 지나치게 외워 Overfitting이 발생할 수 있다.

### Underfitting

- 모델이 데이터의 규칙을 충분히 학습하지 못한 상태
- 학습 데이터와 새로운 데이터 모두에서 성능이 낮을 수 있다.

### Overfitting

- 모델이 학습 데이터에 지나치게 맞춰진 상태
- 학습 데이터에서는 성능이 좋지만 새로운 데이터에서는 성능이 낮다.

## 15.3 Loss Function

Loss Function은 예측값과 정답이 얼마나 다른지를 수치로 나타낸다.

- Loss가 작을수록 예측이 정답에 가깝다.
- 학습의 목표는 Loss를 최소화하는 것이다.
- Loss는 모델의 파라미터를 어느 방향으로 수정할지 결정하는 기준이 된다.

## 15.4 Gradient

Gradient는 파라미터를 조금 변화시켰을 때 Loss가 어느 방향으로 얼마나 변하는지를 나타낸다.

연쇄법칙:

$$
\frac{dL}{dw}
=
\frac{dL}{dy}
\frac{dy}{dz}
\frac{dz}{dw}
$$

Gradient가 양수라면 가중치를 증가시킬 때 Loss가 증가하는 방향이고, Gradient가 음수라면 가중치를 증가시킬 때 Loss가 감소하는 방향이다.

## 15.5 Forward Propagation

입력을 첫 번째 층부터 출력층까지 전달해 예측값을 계산하는 과정이다.

## 15.6 Backpropagation

출력에서 입력 방향으로 연쇄법칙을 적용해 각 파라미터가 Loss에 미친 영향을 계산하는 과정이다.

Backpropagation 자체는 Gradient를 계산하는 과정이며, 실제 가중치 수정은 Optimizer가 수행한다.

## 15.7 Gradient Descent

Loss를 줄이기 위해 Gradient의 반대 방향으로 가중치를 이동한다.

$$
w_{new}=w_{old}-\eta\frac{dL}{dw}
$$

$\eta$는 Learning Rate다.

## 15.8 Learning Rate

Learning Rate는 한 번의 갱신에서 가중치를 얼마나 크게 바꿀지를 결정한다.

- 너무 작음: 안정적일 수 있지만 학습이 매우 느리다.
- 너무 큼: 최적점을 지나치거나 Loss가 진동해 학습이 불안정할 수 있다.

## 15.9 전체 학습 순서

1. 입력과 정답을 준비한다.
2. Forward Propagation으로 예측한다.
3. Loss를 계산한다.
4. 이전 Gradient를 초기화한다.
5. Backpropagation으로 Gradient를 계산한다.
6. Optimizer가 Weight와 Bias를 갱신한다.

---

# 16. 분류 문제와 손실 함수

## 16.1 이진 분류

두 클래스 중 하나를 선택하는 문제다.

- 출력에 Sigmoid를 사용할 수 있다.
- 손실 함수로 Binary Cross-Entropy를 사용할 수 있다.

## 16.2 다중 클래스 분류

여러 클래스 중 하나를 선택하는 문제다.

- MNIST는 숫자 0~9 중 하나를 고르는 10개 클래스 문제다.
- 손실 함수로 Cross Entropy를 사용한다.

PyTorch의 Cross Entropy는 모델의 원시 출력인 **Logit**을 직접 입력받는다. 내부적으로 필요한 확률 변환과 손실 계산을 함께 처리하므로 앞에서 Softmax를 별도로 적용하지 않는다.

---

# 17. Convolutional Neural Network(CNN)

## 17.1 CNN의 정의

CNN은 이미지처럼 공간적 구조를 가진 데이터를 처리하도록 설계된 신경망이다.

일반적인 Fully Connected Network는 이미지를 1차원으로 펼치면 픽셀 사이의 위치 관계를 직접 보존하기 어렵다. CNN은 이미지의 2차원 또는 3차원 구조를 유지한 채 주변 픽셀의 지역 패턴을 학습한다.

## 17.2 CNN의 핵심 특징

- **Local Connectivity**: 가까운 픽셀 영역을 중심으로 특징을 추출한다.
- **Weight Sharing**: 같은 Kernel을 이미지의 모든 위치에 적용한다.
- **Spatial Structure**: 픽셀의 공간적 관계를 유지한다.

Weight Sharing을 사용하므로 모든 위치에 별도 가중치를 두는 것보다 파라미터 수를 줄일 수 있고, 같은 특징을 이미지의 여러 위치에서 찾을 수 있다.

## 17.3 CNN의 가중치와 편향

- 가중치: Kernel 각 칸의 값
- 편향: Feature 반응의 기준을 이동시키는 값

학습 전 Kernel은 무작위 값이다. 학습이 진행되면 분류에 유용한 Edge, 방향, 질감, 형태에 반응하도록 Kernel 값이 수정된다.

## 17.4 Feature Map

Feature Map은 하나의 Kernel을 입력 전체에 Convolution한 결과다.

- Kernel 하나당 Feature Map 하나가 생성된다.
- 각 값은 해당 위치에 Kernel이 찾는 패턴이 얼마나 강하게 존재하는지를 의미한다.

Feature Map 값의 의미:

- 큰 양수: Kernel과 같은 방향의 특징이 강함
- 0에 가까움: 해당 특징이 거의 없음
- 큰 음수: Kernel의 음의 반응이 강함. 방향성 Edge Kernel이라면 반대 방향의 밝기 변화를 뜻할 수 있음

## 17.5 출력 크기

입력 크기 $H\times W$, Padding $P$, Kernel 크기 $K$, Stride $S$일 때:

$$
H_{out}=\left\lfloor\frac{H+2P-K}{S}\right\rfloor+1
$$

$$
W_{out}=\left\lfloor\frac{W+2P-K}{S}\right\rfloor+1
$$

- Padding이 커지면 출력 크기를 유지하는 데 도움이 된다.
- Kernel이 커지면 출력 크기가 작아진다.
- Stride가 커지면 이동 간격이 넓어져 출력 크기가 작아진다.

## 17.6 Pooling

Pooling은 Feature Map의 공간 크기를 줄이면서 중요한 반응을 요약한다.

Max Pooling은 작은 영역에서 가장 큰 값을 선택한다.

효과:

- 연산량과 메모리 사용 감소
- 뒤쪽 Layer에 전달할 데이터 크기 감소
- 작은 위치 변화에 대한 민감도 완화
- 강한 특징 유지

## 17.7 Flatten과 Fully Connected Layer

- **Flatten**: 다차원 Feature Map을 1차원 벡터로 바꾼다.
- **Fully Connected Layer**: 추출된 특징을 종합해 최종 클래스를 판단한다.

## 17.8 층에 따른 특징 변화

- 앞쪽 Layer: 선, Edge, 밝기와 색상 변화
- 중간 Layer: 질감, 획, 객체의 부분 형태
- 깊은 Layer: 부분 특징의 조합, 객체의 전체 구조

깊은 층은 앞 층에서 추출한 단순 특징을 조합해 더 복잡한 특징을 만든다.

## 17.9 전형적인 CNN 흐름

$$
Input \rightarrow Convolution \rightarrow ReLU \rightarrow Pooling
\rightarrow Flatten \rightarrow Fully\ Connected \rightarrow Output
$$

---

# 18. Dataset, DataLoader, Batch

## 18.1 Dataset

Dataset은 하나의 입력 데이터와 그에 대응하는 Label을 제공하는 데이터 집합의 표현이다.

## 18.2 DataLoader

DataLoader는 Dataset의 여러 샘플을 Batch로 묶어 모델에 전달한다.

주요 역할:

- Batch 생성
- Batch 단위 반복
- 데이터 순서 섞기
- 데이터 로딩 관리

## 18.3 Batch

Batch는 한 번의 학습 단계에서 함께 처리하는 여러 샘플의 묶음이다.

Batch를 사용하는 이유:

- 여러 샘플을 병렬 처리할 수 있다.
- 전체 데이터를 한 번에 메모리에 올리는 부담을 줄인다.
- 한 샘플의 Gradient보다 안정적인 평균 방향을 얻을 수 있다.

이미지 Batch의 일반적인 Tensor 구조:

$$
[N,C,H,W]
$$

- $N$: Batch 크기
- $C$: 채널
- $H$: 높이
- $W$: 너비

## 18.4 학습과 평가

### 학습 모드

- 예측을 수행한다.
- Loss와 Gradient를 계산한다.
- 가중치를 수정한다.

### 평가 모드

- 학습된 가중치로 예측한다.
- 가중치를 수정하지 않는다.
- Gradient 계산이 필요하지 않다.

## 18.5 Loss와 Accuracy

- **Loss**: 예측 분포와 정답의 차이를 연속적인 값으로 표현한다.
- **Accuracy**: 전체 샘플 중 정답을 맞힌 비율이다.

학습 Loss는 계속 감소하지만 평가 Loss가 증가하거나 평가 Accuracy가 낮아지면 Overfitting을 의심할 수 있다.

---

# 19. CPU와 GPU 병렬 연산

## 19.1 CPU

- 복잡하고 강력한 소수의 코어를 사용한다.
- 분기와 제어 흐름이 많은 작업에 적합하다.
- 순차적인 작업과 다양한 종류의 연산에 강하다.

## 19.2 GPU

- 많은 연산 코어를 가진다.
- 같은 연산을 대규모 데이터에 반복 적용하는 데 적합하다.
- 이미지, 행렬, Tensor 연산을 병렬로 처리한다.
- Convolution과 행렬곱이 많은 딥러닝에서 유리하다.

GPU가 항상 CPU보다 빠른 것은 아니다.

- 데이터가 매우 작을 때
- CPU와 GPU 사이의 복사 비용이 클 때
- 순차적 분기와 제어가 많은 작업일 때

GPU의 병렬 처리 장점이 충분히 나타나지 않을 수 있다.

## 19.3 NumPy와 CuPy

- NumPy: CPU 배열 연산
- CuPy: CUDA를 이용한 GPU 배열 연산

문법은 비슷하지만 배열이 존재하는 메모리와 연산 장치가 다르다.

## 19.4 Host Memory와 Device Memory

- **Host Memory**: CPU가 사용하는 시스템 메모리
- **Device Memory**: GPU가 사용하는 메모리

일반 시스템에서는 RAM과 VRAM이 물리적으로 분리된다. Jetson은 물리 메모리를 공유하는 UMA 구조를 사용하지만 CPU 배열과 GPU 배열은 논리적으로 서로 다른 실행 영역에서 관리된다.

따라서 NumPy 배열과 CuPy 배열을 바로 함께 계산할 수 없으며 한쪽 장치에 맞게 변환해야 한다.

## 19.5 데이터 전송 비용

CPU와 GPU 사이의 데이터 이동에는 시간이 필요하다.

$$
CPU\ Memory \leftrightarrow GPU\ Memory
$$

작은 연산마다 데이터를 왕복하면 GPU 계산으로 얻은 시간 이득이 사라질 수 있다. 가능한 한 데이터를 GPU에 유지하면서 여러 연산을 수행하고 필요한 시점에만 CPU로 가져오는 것이 효율적이다.

## 19.6 병렬 처리의 의미

CPU 방식은 출력 픽셀을 하나씩 순차적으로 계산할 수 있다. GPU 방식은 이미지 배열 전체에 같은 곱셈과 덧셈을 동시에 적용할 수 있다.

중요한 점은 반복문이 존재하지 않는다는 뜻이 아니라, 반복의 각 단계에서 수행되는 **대규모 배열 연산이 병렬화**된다는 것이다.

## 19.7 GPU 동기화

GPU 연산은 CPU에 대해 비동기적으로 실행될 수 있다. CPU는 GPU 작업이 끝나기 전에 다음 명령으로 진행할 수 있다.

따라서 정확한 GPU 처리 시간을 측정하려면 GPU 작업이 완료될 때까지 기다리는 동기화가 필요하다.

## 19.8 GPU Warm-up

GPU의 첫 연산에는 다음 초기화 비용이 포함될 수 있다.

- CUDA Context 생성
- cuDNN 초기화
- 메모리 할당
- 연산 Kernel 준비

첫 번째 실행은 실제 반복 연산보다 느릴 수 있다. 본 측정 전에 같은 형태의 연산을 미리 실행해 초기화 비용을 분리하는 것이 GPU Warm-up이다.

---

# 20. PyTorch 이론

## 20.1 PyTorch

PyTorch는 Tensor 연산, 자동 미분, 신경망 구성, GPU 가속을 지원하는 딥러닝 프레임워크다.

핵심 기능:

- 다차원 Tensor 연산
- CUDA 기반 GPU 가속
- 자동 미분과 Gradient 계산
- 신경망 Layer와 Loss Function
- Optimizer
- Dataset과 DataLoader

## 20.2 Tensor와 Device

Tensor는 CPU 또는 GPU에 존재할 수 있다.

모델과 입력 Tensor는 같은 Device에 있어야 한다. CPU 모델과 GPU Tensor 또는 GPU 모델과 CPU Tensor는 직접 연산할 수 없다.

## 20.3 자동 미분

PyTorch는 순전파 과정의 연산 관계를 기록하고 Backpropagation 시 연쇄법칙을 적용해 각 파라미터의 Gradient를 자동으로 계산한다.

## 20.4 이미지 Tensor 변환

일반적인 이미지는 `(H,W,C)` 구조를 사용하지만 PyTorch 모델은 주로 `(C,H,W)` 구조를 사용한다.

또한 픽셀값을 `0~255` 정수에서 `0.0~1.0` 실수로 스케일링한다. 입력 형식과 값의 범위를 통일하면 모델의 계산과 학습을 안정적으로 수행할 수 있다.

---

# 21. MNIST와 CIFAR-10의 이론적 차이

## 21.1 MNIST

- 흑백 손글씨 숫자 이미지
- 단일 채널
- 배경이 단순함
- 객체가 대체로 중앙에 위치함
- 비교적 단순한 분류 문제

## 21.2 CIFAR-10

- 실제 사물의 RGB 컬러 이미지
- 세 개의 색상 채널
- 배경이 복잡함
- 객체의 위치, 방향, 색, 형태가 다양함
- MNIST보다 분류 난이도와 Overfitting 가능성이 높음

## 21.3 비교

| 구분 | MNIST | CIFAR-10 |
|---|---|---|
| 영상 | 흑백 손글씨 | 실제 사물 컬러 영상 |
| 채널 | 1 | 3 |
| 배경 | 단순 | 복잡 |
| 클래스 내부 변화 | 상대적으로 작음 | 큼 |
| 학습 난이도 | 낮은 편 | 높은 편 |

---

# 22. 데이터 증강과 정규화

## 22.1 Data Augmentation

데이터 증강은 원본 학습 이미지를 무작위로 변형해 새로운 학습 샘플처럼 사용하는 방법이다.

예시:

- 위치 이동 또는 Crop
- 좌우 반전
- 회전
- 밝기 변화

목적:

- 데이터의 다양성 증가
- 특정 위치, 방향, 배경을 외우는 현상 감소
- 객체의 본질적인 특징 학습
- Overfitting 완화

데이터 증강은 일반적으로 학습 데이터에만 적용한다. 평가 데이터까지 무작위로 바꾸면 평가 조건이 일정하지 않기 때문이다.

## 22.2 Normalization

정규화는 입력값의 분포를 일정한 기준으로 조정하는 과정이다.

$$
x'=\frac{x-\mu}{\sigma}
$$

- $\mu$: 평균
- $\sigma$: 표준편차

효과:

- 채널별 값의 분포 차이 감소
- Gradient의 불안정한 변화 완화
- Optimizer의 안정적인 갱신
- 더 빠른 수렴에 도움

학습과 평가의 입력 분포가 같아야 하므로 두 데이터에 같은 평균과 표준편차를 사용한다.

정규화된 값은 `0~1` 범위를 벗어날 수 있다. 이는 오류가 아니라 평균을 중심으로 표준편차 단위로 값을 표현했기 때문이다.

## 22.3 데이터 증강과 정규화 비교

| 개념 | 무엇을 바꾸는가? | 목적 |
|---|---|---|
| 데이터 증강 | 이미지의 위치·방향·모양 등 | 데이터 다양성 증가, Overfitting 완화 |
| 정규화 | 픽셀값의 분포 | Gradient와 학습 안정화 |

---

# 23. 깊은 CNN의 주요 Layer

## 23.1 채널 수 증가

Channel 수는 서로 다른 종류의 Feature Map 수를 의미한다. 채널이 많아지면 한 단계에서 더 다양한 특징을 표현할 수 있다.

- 앞쪽: 색상과 Edge
- 중간: 질감과 부분 형태
- 깊은 층: 객체의 복잡한 구조

## 23.2 Batch Normalization

Batch Normalization은 각 Batch의 Feature Map 분포를 조정해 학습을 안정화한다.

효과:

- 깊은 네트워크의 학습 안정화
- Gradient 흐름 개선
- 수렴 속도 향상에 도움

입력 이미지에 적용하는 Normalization과 CNN 내부의 Batch Normalization은 적용 대상과 위치가 다르다.

## 23.3 Adaptive Average Pooling

각 Feature Map의 공간 영역을 평균값으로 압축한다.

예:

$$
256\times4\times4 \rightarrow 256\times1\times1
$$

효과:

- Fully Connected Layer로 전달되는 Feature 수 감소
- 파라미터 수와 연산량 감소
- 지정한 출력 공간 크기로 변환 가능

## 23.4 Dropout

Dropout은 학습 중 일부 Feature를 무작위로 비활성화한다.

효과:

- 특정 Feature에 대한 과도한 의존 방지
- 여러 Feature를 함께 사용하도록 유도
- Overfitting 완화

Dropout은 학습 중에 사용하고 평가 시에는 모든 Feature를 사용한다.

---

# 24. 딥러닝 기반 객체 탐지와 Edge AI

## 24.1 객체 탐지와 탐지 방식

이미지 분류는 이미지 전체의 종류를 예측한다. **객체 탐지(Object Detection)**는 각 객체의 **종류(Class)**와 **위치(Localization)**를 함께 찾는다. 한 이미지에서 여러 객체를 탐지할 수 있다.

| 구분 | 규칙 기반 탐지 | 학습 기반 탐지 |
|---|---|---|
| 판단 기준 | 사람이 색·크기·형태 규칙을 정함 | 데이터에서 모델이 특징을 학습함 |
| 장점 | 학습 데이터가 필요 없고 판단 기준이 명확함 | 다양한 배경과 객체 변화에 대응 가능 |
| 한계 | 조명·배경·방향 변화에 민감함 | 학습 데이터와 연산 자원이 필요함 |

기존 장의 Color Segmentation → Binary Mask → Contour → Bounding Box는 규칙 기반 객체 탐지의 예다.

## 24.2 Bounding Box

**Bounding Box(BBox)**는 객체를 둘러싸는 직사각형이다. 이미지의 원점은 왼쪽 위이며 x는 오른쪽, y는 아래쪽으로 증가한다.

| 표현 | 의미 | 변환 관계 |
|---|---|---|
| $(x_1,y_1,x_2,y_2)$ | 왼쪽 위·오른쪽 아래 좌표 | $w=x_2-x_1$, $h=y_2-y_1$ |
| $(x,y,w,h)$ | 왼쪽 위 좌표·너비·높이 | $x_2=x+w$, $y_2=y+h$ |
| $(c_x,c_y,w,h)$ | 중심 좌표·너비·높이 | $x_1=c_x-w/2$, $y_1=c_y-h/2$ |
| 정규화 중심 좌표 | 중심·크기를 영상 크기로 나눈 값 | x와 너비는 영상 너비로, y와 높이는 영상 높이로 나눔 |

정규화 좌표는 서로 다른 해상도에서도 객체의 상대적인 위치와 크기를 나타낸다.

## 24.3 IoU: 박스가 얼마나 겹치는가

**Intersection over Union(IoU)**는 두 BBox의 교집합 면적을 합집합 면적으로 나눈 값이다.

$$
IoU=\frac{A_{\cap}}{A_1+A_2-A_{\cap}}
$$

- 범위는 $0\le IoU\le1$이다. 0은 겹치지 않음, 1은 완전히 같은 박스를 뜻한다.
- 교집합이 없을 때 면적은 0으로 둔다.
- 예측 박스와 정답 박스의 위치 일치도를 평가하거나 박스끼리 중복됐는지 판단할 때 사용한다.
- IoU가 높아도 객체 **종류**를 맞혔다는 뜻은 아니다.

## 24.4 NMS: 중복 박스 제거

**Non-Maximum Suppression(NMS)**는 한 객체에 대해 여러 개 나온 예측 박스에서 대표 박스를 남긴다.

1. **Confidence Threshold**보다 신뢰도가 낮은 박스를 거른다.
2. 가장 신뢰도가 높은 박스를 선택한다.
3. 선택한 박스와 나머지 박스의 IoU를 계산한다.
4. **IoU Threshold**보다 많이 겹친 박스를 제거한다.
5. 남은 박스에 반복한다.

Confidence Threshold는 예측을 믿을지, IoU Threshold는 겹친 박스를 중복으로 볼지를 결정한다. IoU 임계값이 너무 낮으면 가까운 서로 다른 객체가 제거될 수 있다.

앞 장의 **Canny NMS**는 픽셀의 Gradient 방향에서 국소 최대만 남겨 Edge를 얇게 한다. **객체 탐지 NMS**는 겹친 Bounding Box 중 대표 예측을 남긴다.

## 24.5 YOLO와 COCO

**YOLO(You Only Look Once)**는 이미지 전체에서 여러 객체의 **위치·종류·신뢰도**를 예측하는 CNN 기반 **One-stage Detector**다. 별도의 Region Proposal 단계 없이 특징을 공유하고 여러 위치를 병렬 예측해 실시간 처리에 적합하다.

- 모델 크기 `n, s, m, l, x`는 일반적으로 경량형부터 대형 순서다.
- 작은 모델은 자원을 덜 쓰고 빠르며, 큰 모델은 더 많은 자원을 써서 정확도 향상을 노린다. 실제 속도·정확도는 환경에 따라 다르다.
- **Pre-trained Model**은 데이터로 이미 학습된 가중치를 가진 모델이다.
- **COCO**는 사람, 차량, 동물 등이 다양한 배경에서 등장하는 대표적인 객체 탐지·분할 데이터셋이다. 노트북의 사전 학습 YOLO 모델은 COCO의 80개 범주를 탐지한다.

사전 학습 모델이 잘 탐지하는 객체와 환경은 학습한 클래스와 데이터 분포의 영향을 받는다.

## 24.6 실시간 성능: FPS와 EMA

**FPS(Frames Per Second)**는 초당 처리한 프레임 수다. 한 프레임의 처리 시간이 $t$초로 일정하면 $FPS=1/t$이고, 밀리초 단위면 $FPS=1000/t$이다.

- **추론 FPS**: 모델의 예측 연산만 측정한 처리량
- **End-to-End FPS**: 프레임 입력, 전처리, 추론, NMS, 시각화, 화면 출력까지 포함한 처리량
- **Latency**: 한 번의 처리에 걸리는 시간
- **Throughput**: 단위 시간에 처리한 추론 횟수

추론 FPS가 높아도 다른 단계가 느리면 실제 표시 FPS는 낮아진다. 카메라가 최대 30 FPS로 프레임을 공급한다면 관측된 30 FPS가 모델의 **최대 추론 속도**를 뜻하지는 않는다.

프레임별 FPS는 순간적인 병목으로 흔들린다. **지수 이동 평균(EMA)**은 현재 측정값과 이전 평균을 가중합해 수치를 부드럽게 표시한다.

$$
FPS_{smooth}=\alpha FPS_{current}+(1-\alpha)FPS_{previous}
$$

$\alpha$가 크면 새 변화에 빠르게 반응하고, 작으면 더 부드럽지만 반응이 느리다.

## 24.7 Edge Device와 Power Mode

Jetson 같은 **Edge Device**는 장치에서 직접 추론하지만 연산 성능, 메모리, 전력, 냉각에 제약이 있다. CPU·GPU 사용률과 클럭, 메모리 사용, 온도, 소비 전력을 함께 보아야 병목을 파악할 수 있다.

**Power Mode**는 CPU·GPU·메모리의 최대 동작 범위와 전력 한계를 조절한다. 성능을 높이면 발열과 소비 전력도 커진다. 열 또는 전력 한계에 도달하면 **Throttling**으로 클럭이 제한되어 성능이 떨어질 수 있다. 따라서 최고 설정이 항상 최고 지속 성능을 보장하지 않는다.

## 24.8 ONNX와 TensorRT

**ONNX(Open Neural Network Exchange)**는 모델을 다른 프레임워크와 추론 환경에서 사용할 수 있게 하는 교환 형식이다. 노트북에서는 PyTorch 모델과 TensorRT 사이의 중간 형식으로 사용한다.

**TensorRT**는 학습된 모델을 NVIDIA GPU에서 빠르게 **추론**하도록 최적화한다. 연산 그래프 최적화, 연산 결합, GPU 실행 최적화 등을 적용해 엔진을 만든다. 모델을 새로 학습시키는 과정은 아니다.

| 정밀도 | 이점 | 주의점 |
|---|---|---|
| FP32 | 수치 정밀도를 유지하며 실행 최적화 | 자원 부담이 상대적으로 큼 |
| FP16 | 연산·메모리 부담을 줄일 수 있음 | 정밀도 손실과 장치 지원 확인 |
| INT8 | 더 적은 비트로 자원 사용 감소 가능 | Calibration과 정확도 검증 필요 |

낮은 정밀도가 언제나 더 높은 실측 FPS를 보장하는 것은 아니다. 입력 속도와 추론 외 처리 단계가 전체 처리량을 제한할 수 있다.

## 24.9 양자화와 Calibration

**양자화(Quantization)**는 모델의 가중치 또는 연산값을 더 적은 비트로 표현하는 최적화다. 모델 크기, 메모리 사용량, 추론 시간을 줄일 수 있지만 정확도가 감소할 수 있다.

**Calibration**은 실제 사용 환경을 대표하는 이미지를 모델에 넣어 각 층의 값 분포를 살피고, 고정밀도 값을 INT8에 대응시키는 **Scale**을 정하는 과정이다. 대표성이 부족한 데이터로 Scale을 정하면 실제 입력을 부정확하게 표현해 탐지 정확도가 떨어질 수 있다.

---

# 25. 핵심 비교 총정리

## 25.1 Smoothing vs. Sharpening

| Smoothing | Sharpening |
|---|---|
| 고주파 억제 | 고주파 강조 |
| 노이즈 감소 | Edge와 세부 특징 강조 |
| 이미지가 흐려짐 | 이미지가 선명해짐 |

## 25.2 Sobel vs. Canny

| Sobel | Canny |
|---|---|
| Gradient 계산 중심 | 여러 단계를 결합한 Edge 알고리즘 |
| Edge가 두꺼울 수 있음 | NMS로 얇은 Edge 생성 |
| 노이즈에 민감 | Gaussian Smoothing으로 노이즈 완화 |

## 25.3 Opening vs. Closing

| Opening | Closing |
|---|---|
| 침식 → 팽창 | 팽창 → 침식 |
| 외부의 작은 흰색 노이즈 제거 | 내부의 검정 구멍과 끊김 연결 |

## 25.4 SLP vs. MLP

| SLP | MLP |
|---|---|
| 은닉층 없음 | 하나 이상의 은닉층 |
| 선형 분리 문제 | 비선형 문제까지 표현 |
| XOR 해결 불가 | XOR 해결 가능 |

## 25.5 Forward vs. Backpropagation

| Forward Propagation | Backpropagation |
|---|---|
| 입력에서 출력 방향 | 출력에서 입력 방향 |
| 예측값 계산 | Gradient 계산 |

## 25.6 CPU vs. GPU

| CPU | GPU |
|---|---|
| 강력한 소수의 코어 | 단순한 다수의 코어 |
| 복잡한 제어와 순차 작업 | 대규모 동일 연산의 병렬 처리 |
| 분기 처리에 강함 | 행렬·이미지·Tensor 연산에 강함 |

## 25.7 NumPy vs. CuPy vs. PyTorch

| 도구 | 기본 장치 | 핵심 목적 |
|---|---|---|
| NumPy | CPU | 일반 배열·수치 연산 |
| CuPy | GPU | NumPy와 유사한 GPU 배열 연산 |
| PyTorch | CPU/GPU | 자동 미분과 딥러닝 모델 학습 |

---

# 26. 핵심 공식

## Grayscale

$$
Gray=0.299R+0.587G+0.114B
$$

## Sobel Magnitude

$$
Magnitude=\sqrt{dx^2+dy^2}
$$

## Residual Extraction

$$
High=Original-Low
$$

## Unsharp Masking

$$
Sharpened=Original+High
$$

## Contour Centroid

$$
C_x=\frac{M_{10}}{M_{00}},\qquad
C_y=\frac{M_{01}}{M_{00}}
$$

## Harris Response

$$
R=\det(M)-k\,\mathrm{trace}(M)^2
$$

## 퍼셉트론

$$
z=\sum_iw_ix_i+b,\qquad y=f(z)
$$

## Sigmoid

$$
\sigma(x)=\frac{1}{1+e^{-x}}
$$

## ReLU

$$
ReLU(x)=\max(0,x)
$$

## Gradient Descent

$$
w_{new}=w_{old}-\eta\frac{dL}{dw}
$$

## Convolution 출력 크기

$$
Output=\left\lfloor\frac{Input+2P-K}{S}\right\rfloor+1
$$

## Normalization

$$
x'=\frac{x-\mu}{\sigma}
$$

## 두 벡터 사이의 각도

$$
\cos\theta=\frac{\vec{a}\cdot\vec{b}}{\|\vec{a}\|\|\vec{b}\|}
$$

---

# 27. 서술형으로 설명할 수 있어야 하는 문장

1. Grayscale은 RGB의 단순 평균이 아니라 인간의 밝기 민감도를 반영한 가중합이다.
2. Gaussian Filter는 중심에 큰 가중치를 주므로 Box Filter보다 자연스러운 Blur를 만든다.
3. Smoothing은 고주파를 억제하고 Sharpening은 고주파를 강조한다.
4. Canny는 Gaussian Smoothing, Sobel, NMS, Hysteresis Thresholding 순서로 Edge를 검출한다.
5. Opening은 외부 흰색 노이즈 제거, Closing은 내부 구멍과 끊김 연결에 사용한다.
6. LAB는 지각 밝기와 색상 축이 분리되어 조명 변화가 있는 상황에 유리할 수 있다.
7. Contour는 Binary Mask의 연결 영역 외곽선이므로 Mask의 품질에 영향을 받는다.
8. Harris Corner는 두 방향에서 모두 밝기 변화가 큰 지점을 찾는다.
9. Kalman Filter는 예측과 보정을 반복해 노이즈가 있는 측정값으로부터 상태를 추정한다.
10. 단층 퍼셉트론은 선형 결정 경계만 만들기 때문에 XOR을 해결할 수 없다.
11. 활성화 함수의 비선형성이 있어야 여러 층이 복잡한 비선형 관계를 표현할 수 있다.
12. Backpropagation은 Gradient를 계산하고 Optimizer는 그 Gradient로 파라미터를 수정한다.
13. CNN은 Local Connectivity와 Weight Sharing으로 이미지의 공간 특징을 효율적으로 학습한다.
14. 하나의 Kernel은 하나의 Feature Map을 생성한다.
15. 깊은 CNN은 앞 층의 단순 특징을 조합해 뒤 층에서 복잡한 특징을 학습한다.
16. GPU는 동일한 대규모 배열 연산의 병렬 처리에 유리하지만 데이터 전송 비용도 고려해야 한다.
17. Jetson의 UMA에서도 NumPy 배열과 CuPy 배열은 논리적인 연산 영역이 다르다.
18. 데이터 증강은 데이터 다양성을 높여 Overfitting을 줄이고, 정규화는 입력 분포를 조정해 학습을 안정화한다.
19. Batch Normalization은 Feature 분포를 조정하고 Dropout은 특정 Feature 의존을 줄인다.
20. GPU Warm-up은 첫 연산의 초기화 비용을 실제 반복 연산 시간과 분리하기 위해 수행한다.
21. 객체 탐지는 이미지 분류에 위치 추정을 더해 각 객체의 종류와 Bounding Box를 예측한다.
22. IoU는 두 Bounding Box의 교집합 면적을 합집합 면적으로 나눈 값이다.
23. 객체 탐지 NMS는 신뢰도가 높은 박스를 남기고 IoU가 큰 중복 박스를 제거한다.
24. YOLO는 별도의 Region Proposal 단계 없이 여러 객체를 예측하는 One-stage Detector다.
25. End-to-End FPS에는 추론뿐 아니라 입력·전처리·NMS·시각화·출력 시간이 포함된다.
26. ONNX는 모델 교환 형식이고 TensorRT는 NVIDIA GPU용 추론 최적화 도구다.
27. INT8 Calibration은 대표 입력의 값 분포를 분석해 양자화 Scale을 정한다.

---

# 부록. Linux의 최소 이론

## GUI와 CLI

- GUI: 아이콘, 창, 마우스를 이용하는 그래픽 인터페이스
- CLI: 명령어를 입력해 컴퓨터와 상호작용하는 인터페이스

## 터미널과 셸

- 터미널: 명령을 입력하고 결과를 보는 창
- 셸: 입력된 명령을 해석하고 실행하는 프로그램

## 가상환경

프로젝트별 Python 패키지와 버전을 분리해 시스템 환경과의 충돌을 줄이는 독립적인 실행 환경이다. Jetson에서는 하드웨어 가속과 연결된 시스템 라이브러리를 보존하면서 프로젝트 패키지를 관리하는 데 의미가 있다.
