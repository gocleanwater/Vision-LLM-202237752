"""Confidence Thresholding과 NMS를 순서대로 적용한다."""

import numpy as np


def calculate_iou(bbox_a, bbox_b):
    x1_a, y1_a, x2_a, y2_a = bbox_a
    x1_b, y1_b, x2_b, y2_b = bbox_b

    intersection_width = max(0, min(x2_a, x2_b) - max(x1_a, x1_b))
    intersection_height = max(0, min(y2_a, y2_b) - max(y1_a, y1_b))
    intersection_area = intersection_width * intersection_height

    bbox_a_area = max(0, x2_a - x1_a) * max(0, y2_a - y1_a)
    bbox_b_area = max(0, x2_b - x1_b) * max(0, y2_b - y1_b)
    union_area = bbox_a_area + bbox_b_area - intersection_area

    if union_area == 0:
        return 0.0

    return intersection_area / union_area


# TODO: Confidence Thresholding 함수 정의
# TODO: Confidence Score가 특정 임계값보다 낮으면 해당 BBox 제거


def prune_low_conf(boxes, scores, conf_threshold=0.5):
    """
    Confidence Thresholding 적용

    Parameters
    ----------
    boxes : list
        Bounding Box 목록
        각 박스는 (x1, y1, x2, y2) 형식

    scores : list
        각 Bounding Box의 Confidence Score

    conf_threshold : float
        Bounding Box를 유지하기 위한 최소 Confidence Score

    Returns
    -------
    pruned_boxes : list
        Confidence Score가 임계값 이상인 Bounding Box 목록

    pruned_scores : list
        Confidence Score가 임계값 이상인 Bounding Box의 Confidence Score 목록
    """

    boxes_scores_zip = zip(boxes, scores)

    pruned_boxes_scores_list = [
        (box, score)
        for (box, score) in boxes_scores_zip
        if score >= conf_threshold
    ]

    pruned_boxes = [box for (box, score) in pruned_boxes_scores_list]
    pruned_scores = [score for (box, score) in pruned_boxes_scores_list]

    return pruned_boxes, pruned_scores


# TODO: NMS 함수 정의
# TODO: np.sort() 함수를 사용하면 1차원 배열을 정렬
# TODO: np.argsort() 함수를 사용하면 1차원 배열의 정렬된 인덱스를 반환


def apply_nms(boxes, scores, iou_threshold=0.5):
    """
    NMS 적용

    Parameters
    ----------
    boxes : list
        Bounding Box 목록
        각 박스는 (x1, y1, x2, y2) 형식

    scores : list
        각 Bounding Box의 Confidence Score

    iou_threshold : float
        중복 Bounding Box를 제거할 IoU 기준값

    Returns
    -------
    nms_boxes : list
        NMS 적용 후 유지된 Bounding Box 목록

    nms_scores : list
        NMS 적용 후 유지된 Bounding Box의 Confidence Score 목록
    """

    # Confidence Score가 높은 BBox의 인덱스부터 정렬
    sorted_indices = np.argsort(scores)[::-1] # [::-1]로 오름차순을 내림차순으로!!

    nms_boxes = []
    nms_scores = []

    while len(sorted_indices) > 0:
        # 남아 있는 BBox 중 Confidence Score가 가장 높은 BBox 선택
        highest_score_idx = sorted_indices[0]

        nms_boxes.append(boxes[highest_score_idx])
        nms_scores.append(scores[highest_score_idx])

        remaining_indices = sorted_indices[1:]
        keep_indices = []

        # 선택한 BBox와 많이 겹치지 않는 BBox만 다음 비교에 유지
        for index in remaining_indices:
            iou = calculate_iou(boxes[highest_score_idx], boxes[index])

            if iou <= iou_threshold:
                keep_indices.append(index)

        sorted_indices = np.array(keep_indices, dtype=int)

    return nms_boxes, nms_scores


def main():
    boxes = [
        (10, 10, 50, 50),
        (12, 12, 48, 48),
        (100, 100, 150, 150),
        (200, 200, 240, 240),
    ]
    scores = [0.95, 0.90, 0.80, 0.30]

    pruned_boxes, pruned_scores = prune_low_conf(
        boxes,
        scores,
        conf_threshold=0.5,
    )
    nms_boxes, nms_scores = apply_nms(
        pruned_boxes,
        pruned_scores,
        iou_threshold=0.5,
    )

    print("Original BBoxes:", len(boxes))
    print("After Confidence Thresholding:", len(pruned_boxes))
    print("After NMS:", len(nms_boxes))
    print("NMS BBoxes:", nms_boxes)
    print("NMS Scores:", nms_scores)


if __name__ == "__main__":
    main()
