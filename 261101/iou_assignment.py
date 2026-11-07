"""두 Bounding Box의 좌표를 변환하고 IoU를 계산한다."""


# TODO: 1) BBox 좌표를 (x,y,w,h)에서 (x1,y1,x2,y2)로 변환하는 함수 정의
# TODO: 2) IoU 계산 함수 정의
def convert_bbox_coord(bbox):
    x, y, w, h = bbox
    return x, y, x + w, y + h


def calculate_iou(bbox_a, bbox_b):
    x1_a, y1_a, x2_a, y2_a = bbox_a
    x1_b, y1_b, x2_b, y2_b = bbox_b

    intersection_width = max(0, min(x2_a, x2_b) - max(x1_a, x1_b))
    intersection_height = max(0, min(y2_a, y2_b) - max(y1_a, y1_b))
    intersection_area = intersection_width * intersection_height

    bbox_a_area = max(0, x2_a - x1_a) * max(0, y2_a - y1_a)
    bbox_b_area = max(0, x2_b - x1_b) * max(0, y2_b - y1_b)
    union_area = bbox_a_area + bbox_b_area - intersection_area

    # TODO: ZeroDivisionError 주의
    if union_area == 0:
        return 0.0

    return intersection_area / union_area


def main():
    bbox_a_xywh = (0, 0, 10, 10)
    bbox_b_xywh = (5, 5, 10, 10)

    bbox_a = convert_bbox_coord(bbox_a_xywh)
    bbox_b = convert_bbox_coord(bbox_b_xywh)
    iou = calculate_iou(bbox_a, bbox_b)

    print("BBox A (x, y, w, h):", bbox_a_xywh)
    print("BBox B (x, y, w, h):", bbox_b_xywh)
    print("BBox A (x1, y1, x2, y2):", bbox_a)
    print("BBox B (x1, y1, x2, y2):", bbox_b)
    print(f"IoU: {iou:.4f}")


if __name__ == "__main__":
    main()
