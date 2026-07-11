from __future__ import annotations

import numpy as np
import pytest

from prl.models import Canvas
from prl.roi_io import (
    ROLE_RIM,
    RoiOutOfBoundsError,
    infer_canvas,
    inspect_roi,
    roi_to_mask,
)


def test_point_roi_is_parsed_and_rasterized_with_canvas_origin(
    point_roi_asset,
) -> None:
    asset = point_roi_asset(
        [(12, 20), (14, 21), (13, 22)],
        "007_PRL2_mask1.roi",
    )

    info = inspect_roi(asset)
    assert info.roi_type_name == "Point"
    assert info.coordinate_count == 3
    assert (info.min_x, info.max_x, info.min_y, info.max_y) == (
        12.0,
        14.0,
        20.0,
        22.0,
    )
    assert info.suggested_case == "007_PRL2"
    assert info.suggested_role == ROLE_RIM

    canvas = Canvas(shape=(5, 6), row_origin=19, col_origin=11, source="test")
    mask, method = roi_to_mask(asset, canvas, mode="auto")
    expected = np.zeros(canvas.shape, dtype=bool)
    expected[[1, 2, 3], [1, 3, 2]] = True
    np.testing.assert_array_equal(mask, expected)
    assert method == "point coordinates (paper-compatible)"


def test_point_roi_infers_a_padded_crop(point_roi_asset) -> None:
    asset = point_roi_asset([(12, 20), (14, 22)], "crop_mask1.roi")

    canvas = infer_canvas([asset], padding_px=4)

    assert canvas.shape == (11, 11)
    assert canvas.row_origin == 16
    assert canvas.col_origin == 8
    assert canvas.source == "roi_inferred_crop"
    mask, _ = roi_to_mask(asset, canvas)
    assert mask.sum() == 2
    assert mask[4, 4]
    assert mask[6, 6]


def test_point_roi_outside_dicom_canvas_is_rejected(point_roi_asset) -> None:
    asset = point_roi_asset([(1, 1), (5, 2)], "outside_mask1.roi")
    canvas = Canvas(shape=(5, 5), source="dicom")

    with pytest.raises(RoiOutOfBoundsError, match="1 ROI coordinate.*outside"):
        roi_to_mask(asset, canvas, mode="study_pixels")


def test_hyperstack_z_position_drives_suggested_frame(point_roi_asset) -> None:
    asset = point_roi_asset([(1, 1), (2, 2)], "stack_mask1.roi", z=3)

    info = inspect_roi(asset)

    assert info.position == 3
    assert info.z_position == 3
    assert info.c_position == 0
    assert info.t_position == 0
