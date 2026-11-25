"""
Module 7 — ORB feature matching.

Oriented FAST and Rotated BRIEF keypoint extraction and
Hamming-distance nearest-neighbour matching with ratio filtering.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Tuple

import cv2
import numpy as np
from PIL import Image

import config


@dataclass
class ORBResult:
    img_a:          Image.Image
    img_b:          Image.Image
    kp_a_vis:       Image.Image    # keypoints drawn on img_a
    kp_b_vis:       Image.Image
    raw_matches_vis: Image.Image
    filtered_matches_vis: Image.Image
    n_kp_a:         int
    n_kp_b:         int
    n_raw_matches:  int
    n_filtered:     int
    good_matches:   List[Tuple[int,int,float]]  # (idx_a, idx_b, distance)
    kp_a_coords:    List[Tuple[float,float]]
    kp_b_coords:    List[Tuple[float,float]]
    error:          Optional[str] = None


def _to_gray(img: Image.Image) -> np.ndarray:
    return cv2.cvtColor(np.array(img.convert("RGB")), cv2.COLOR_RGB2GRAY)


def _pil(arr: np.ndarray) -> Image.Image:
    if arr.ndim == 2:
        return Image.fromarray(arr)
    return Image.fromarray(cv2.cvtColor(arr, cv2.COLOR_BGR2RGB))


def match(img_a: Image.Image, img_b: Image.Image,
          n_features: int = config.ORB_N_FEATURES,
          ratio_thresh: float = config.ORB_RATIO_THRESH) -> ORBResult:
    """Run ORB on two PIL images and return rich result object."""
    try:
        gray_a = _to_gray(img_a)
        gray_b = _to_gray(img_b)

        orb = cv2.ORB_create(nfeatures=n_features, edgeThreshold=8, patchSize=15)
        kp_a, des_a = orb.detectAndCompute(gray_a, None)
        kp_b, des_b = orb.detectAndCompute(gray_b, None)

        # Keypoint visualisations
        kp_a_vis_arr = cv2.drawKeypoints(
            gray_a, kp_a, None,
            flags=cv2.DRAW_MATCHES_FLAGS_DRAW_RICH_KEYPOINTS,
            color=(37,99,235))
        kp_b_vis_arr = cv2.drawKeypoints(
            gray_b, kp_b, None,
            flags=cv2.DRAW_MATCHES_FLAGS_DRAW_RICH_KEYPOINTS,
            color=(37,99,235))

        if des_a is None or des_b is None or len(kp_a) < 2 or len(kp_b) < 2:
            blank = _make_blank(img_a, img_b, "Insufficient keypoints")
            return ORBResult(
                img_a, img_b, _pil(kp_a_vis_arr), _pil(kp_b_vis_arr),
                blank, blank,
                len(kp_a), len(kp_b), 0, 0, [], [], [],
                error="Insufficient keypoints for matching."
            )

        # Brute-force Hamming, kNN k=2 for ratio test
        bf = cv2.BFMatcher(cv2.NORM_HAMMING)
        knn_matches = bf.knnMatch(des_a, des_b, k=2)

        # Lowe ratio test
        good: List[cv2.DMatch] = []
        for pair in knn_matches:
            if len(pair) == 2:
                m, n = pair
                if m.distance < ratio_thresh * n.distance:
                    good.append(m)

        # Mutual (cross-check) filter
        knn_rev    = bf.knnMatch(des_b, des_a, k=2)
        good_rev   = {(m.queryIdx, m.trainIdx) for pair in knn_rev
                      if len(pair) == 2 and pair[0].distance < ratio_thresh * pair[1].distance
                      for m in [pair[0]]}
        mutual     = [m for m in good if (m.trainIdx, m.queryIdx) in good_rev]

        # Raw match visualisation
        raw_arr = cv2.drawMatches(
            gray_a, kp_a, gray_b, kp_b, good[:50], None,
            flags=cv2.DrawMatchesFlags_NOT_DRAW_SINGLE_POINTS)

        # Filtered match visualisation
        filt_arr = cv2.drawMatches(
            gray_a, kp_a, gray_b, kp_b, mutual[:50], None,
            matchColor=(37,99,235),
            flags=cv2.DrawMatchesFlags_NOT_DRAW_SINGLE_POINTS)

        good_tuples = [(m.queryIdx, m.trainIdx, float(m.distance)) for m in mutual]
        kp_a_coords = [(kp_a[m.queryIdx].pt[0], kp_a[m.queryIdx].pt[1]) for m in mutual]
        kp_b_coords = [(kp_b[m.trainIdx].pt[0], kp_b[m.trainIdx].pt[1]) for m in mutual]

        return ORBResult(
            img_a=img_a, img_b=img_b,
            kp_a_vis=_pil(kp_a_vis_arr),
            kp_b_vis=_pil(kp_b_vis_arr),
            raw_matches_vis=_pil(raw_arr),
            filtered_matches_vis=_pil(filt_arr),
            n_kp_a=len(kp_a), n_kp_b=len(kp_b),
            n_raw_matches=len(good),
            n_filtered=len(mutual),
            good_matches=good_tuples,
            kp_a_coords=kp_a_coords,
            kp_b_coords=kp_b_coords,
        )
    except Exception as exc:
        blank = Image.new("RGB", (400, 100), "white")
        return ORBResult(img_a, img_b, blank, blank, blank, blank,
                         0, 0, 0, 0, [], [], [], error=str(exc))


def _make_blank(img_a: Image.Image, img_b: Image.Image, msg: str) -> Image.Image:
    w = img_a.width + img_b.width
    h = max(img_a.height, img_b.height)
    out = Image.new("RGB", (w, h), (248,250,252))
    return out
