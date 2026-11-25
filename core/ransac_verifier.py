"""
Module 8 — RANSAC geometric verification.

Filters ORB matches using homography estimation with RANSAC.
Separates geometric inliers (green) from outliers (red).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Tuple

import cv2
import numpy as np
from PIL import Image

from core.orb_matcher import ORBResult
import config


@dataclass
class RANSACResult:
    matches_before:   int
    inlier_count:     int
    outlier_count:    int
    inlier_ratio:     float
    homography:       Optional[np.ndarray]
    inlier_vis:       Image.Image    # green inliers + red outliers
    geometric_ok:     bool
    spatial_coverage: float          # fraction of image covered by inlier pts
    summary:          str
    error:            Optional[str] = None


def verify(orb: ORBResult,
           min_inliers: int = config.RANSAC_MIN_INLIERS,
           inlier_ratio_min: float = config.RANSAC_INLIER_RATIO_MIN) -> RANSACResult:

    if orb.error:
        return _empty(0, f"ORB step failed: {orb.error}")

    n = len(orb.good_matches)
    if n < 4:
        return _empty(n, f"Too few filtered matches ({n}) for RANSAC homography (need ≥ 4).")

    gray_a = cv2.cvtColor(np.array(orb.img_a.convert("RGB")), cv2.COLOR_RGB2GRAY)
    gray_b = cv2.cvtColor(np.array(orb.img_b.convert("RGB")), cv2.COLOR_RGB2GRAY)

    pts_a = np.float32(orb.kp_a_coords).reshape(-1,1,2)
    pts_b = np.float32(orb.kp_b_coords).reshape(-1,1,2)

    try:
        H, mask = cv2.findHomography(pts_a, pts_b, cv2.RANSAC, config.RANSAC_REPROJ_THRESH)
    except Exception as exc:
        return _empty(n, f"Homography estimation failed: {exc}")

    if mask is None or H is None:
        return _empty(n, "RANSAC could not find a homography.")

    mask_flat  = mask.ravel().tolist()
    inliers    = int(sum(mask_flat))
    outliers   = n - inliers
    ratio      = inliers / max(n, 1)

    # Build inlier/outlier visualisation
    # Reconstruct keypoints from stored coordinates
    kp_a = [cv2.KeyPoint(x=float(c[0]), y=float(c[1]), size=5) for c in orb.kp_a_coords]
    kp_b = [cv2.KeyPoint(x=float(c[0]), y=float(c[1]), size=5) for c in orb.kp_b_coords]
    dm   = [cv2.DMatch(_queryIdx=i, _trainIdx=i, _distance=0) for i in range(n)]

    inlier_matches  = [dm[i] for i in range(n) if mask_flat[i]]
    outlier_matches = [dm[i] for i in range(n) if not mask_flat[i]]

    vis = cv2.drawMatches(gray_a, kp_a, gray_b, kp_b,
                          inlier_matches, None,
                          matchColor=(34,197,94),
                          flags=cv2.DrawMatchesFlags_NOT_DRAW_SINGLE_POINTS)
    # Draw outliers onto the same canvas using the original two images.
    vis = cv2.drawMatches(gray_a, kp_a, gray_b, kp_b, outlier_matches, vis,
                          matchColor=(185,28,28),
                          flags=cv2.DrawMatchesFlags_DRAW_OVER_OUTIMG |
                                cv2.DrawMatchesFlags_NOT_DRAW_SINGLE_POINTS)

    vis_pil = Image.fromarray(cv2.cvtColor(vis, cv2.COLOR_BGR2RGB))

    # Spatial coverage of inlier points
    if inliers > 0:
        inlier_pts = np.array(orb.kp_a_coords)[np.array(mask_flat, dtype=bool)]
        x_range = float(inlier_pts[:,0].max() - inlier_pts[:,0].min())
        y_range = float(inlier_pts[:,1].max() - inlier_pts[:,1].min())
        coverage = (x_range * y_range) / max(gray_a.shape[0] * gray_a.shape[1], 1)
        coverage = min(coverage, 1.0)
    else:
        coverage = 0.0

    geometric_ok = (inliers >= min_inliers and ratio >= inlier_ratio_min)

    if geometric_ok:
        summary = (
            f"{inliers}/{n} matches are geometric inliers (ratio {ratio:.0%}). "
            "A consistent geometric transformation exists between the two regions — "
            "possible copy-move or duplicated signature candidate."
        )
    else:
        summary = (
            f"Only {inliers}/{n} inliers (ratio {ratio:.0%}) — "
            "below the minimum threshold for a confident geometric match."
        )

    return RANSACResult(
        matches_before=n,
        inlier_count=inliers,
        outlier_count=outliers,
        inlier_ratio=ratio,
        homography=H,
        inlier_vis=vis_pil,
        geometric_ok=geometric_ok,
        spatial_coverage=coverage,
        summary=summary,
    )


def _empty(n: int, msg: str) -> RANSACResult:
    blank = Image.new("RGB", (400, 100), (248,250,252))
    return RANSACResult(n, 0, n, 0.0, None, blank, False, 0.0, msg)
