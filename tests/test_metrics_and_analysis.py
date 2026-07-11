from __future__ import annotations

import numpy as np
import pytest

from prl.analysis import analyze_case
from prl.metrics import compute_metrics


def test_compute_metrics_supports_rim_without_core() -> None:
    rim = np.zeros((9, 9), dtype=bool)
    rim[2:7, 2:7] = True
    rim[3:6, 3:6] = False

    result = compute_metrics(rim, None)

    assert result.effective_rim is not None
    np.testing.assert_array_equal(result.effective_rim, rim)
    assert result.values["mask1_area_rim_px"] == 16
    assert np.isnan(result.values["mask2_area_lesion_core_px"])
    assert result.values["total_area_rim_plus_core_px"] == 16
    assert result.values["mask1_rim_closed"] is True
    assert result.values["mask2_geometry_coordinate_system"] == "unavailable"
    assert "pixel spacing required" in result.values[
        "rim_class_using_1p2_mm_threshold"
    ]
    assert any("No calibrated" in warning for warning in result.warnings)


def test_compute_metrics_supports_core_without_rim() -> None:
    core = np.zeros((8, 10), dtype=bool)
    core[2:6, 3:8] = True

    result = compute_metrics(None, core)

    assert result.effective_rim is None
    assert np.isnan(result.values["mask1_area_rim_px"])
    assert result.values["mask2_area_lesion_core_px"] == 20
    assert result.values["total_area_rim_plus_core_px"] == 20
    assert result.values["rim_class_using_1p2_mm_threshold"].endswith(
        "no rim ROI"
    )
    assert result.values["mask2_geometry_coordinate_system"] == "pixel grid"
    assert np.isnan(result.values["mask2_perimeter_mm"])


def test_overlap_cleanup_removes_only_rim_core_intersection() -> None:
    rim = np.zeros((7, 7), dtype=bool)
    core = np.zeros_like(rim)
    rim[1:6, 1:6] = True
    core[2:5, 2:5] = True

    cleaned = compute_metrics(rim, core, remove_overlap=True)

    assert cleaned.values["rim_interior_overlap_px_before_cleanup"] == 9
    assert cleaned.values["mask1_area_rim_px"] == 16
    assert cleaned.values["mask2_area_lesion_core_px"] == 9
    assert cleaned.values["total_area_rim_plus_core_px"] == 25
    assert not np.any(cleaned.effective_rim & core)
    assert any("Removed 9" in warning for warning in cleaned.warnings)

    retained = compute_metrics(rim, core, remove_overlap=False)
    assert retained.values["mask1_area_rim_px"] == 25
    assert retained.values["total_area_rim_plus_core_px"] == 25
    np.testing.assert_array_equal(retained.effective_rim, rim)
    assert any("Retained 9" in warning for warning in retained.warnings)
    assert retained.values["mask1_area_over_total_lesion_area_ratio"] == pytest.approx(
        25 / 34
    )
    assert retained.values["mask1_area_over_union_area_ratio"] == pytest.approx(1.0)


def test_nonpoint_roi_requires_auto_or_polygon_mode() -> None:
    from prl.models import BinaryAsset
    from roifile import ImagejRoi

    roi = ImagejRoi.frompoints(np.asarray([(2, 2), (6, 2), (6, 6), (2, 6)]))
    asset = BinaryAsset("polygon", "polygon.roi", roi.tobytes(), "roi", "polygon.roi")

    with pytest.raises(ValueError, match="Auto by ImageJ ROI type"):
        analyze_case("POLYGON", lesion_roi=asset, roi_mode="study_pixels")


def test_roi_only_analysis_uses_pixels_when_spacing_is_absent(
    point_roi_asset,
) -> None:
    core = point_roi_asset(
        [(20, 30), (21, 30), (20, 31), (21, 31)],
        "CASE_A_mask2.roi",
    )

    result = analyze_case("CASE_A", lesion_roi=core)

    assert result.spacing_mm is None
    assert result.spacing_source is None
    assert result.metrics["mask2_area_lesion_core_px"] == 4
    assert np.isnan(result.metrics["mask2_area_lesion_core_mm2"])
    assert result.metrics["spacing_source"].startswith("unavailable")
    assert any("No calibrated" in warning for warning in result.warnings)


def test_manual_anisotropic_spacing_drives_physical_geometry(
    point_roi_asset,
) -> None:
    core = point_roi_asset(
        [(20, 30), (21, 30), (20, 31), (21, 31)],
        "CASE_B_mask2.roi",
    )

    result = analyze_case(
        "CASE_B",
        lesion_roi=core,
        spacing_policy="manual",
        manual_spacing_mm=(2.0, 0.5),
    )

    assert result.spacing_mm == (2.0, 0.5)
    assert result.spacing_source == "Manual row/column spacing"
    assert result.metrics["pixel_area_mm2"] == pytest.approx(1.0)
    assert result.metrics["mask2_area_lesion_core_mm2"] == pytest.approx(4.0)
    # Four vertical boundary edges use row spacing; four horizontal edges use
    # column spacing: 4 * 2.0 + 4 * 0.5 = 10 mm.
    assert result.metrics["mask2_perimeter_mm"] == pytest.approx(10.0)
    assert result.metrics["mask2_geometry_coordinate_system"] == "physical mm"
    assert result.metrics["mask2_major_axis_length_mm"] > result.metrics[
        "mask2_minor_axis_length_mm"
    ]


@pytest.mark.parametrize(
    "spacing",
    [None, (0.0, 1.0), (np.nan, 1.0), (1.0, -0.25)],
)
def test_manual_spacing_must_be_present_and_positive(point_roi_asset, spacing) -> None:
    core = point_roi_asset([(1, 1)], "CASE_C_mask2.roi")

    with pytest.raises(ValueError, match="manual|finite|greater than zero"):
        analyze_case(
            "CASE_C",
            lesion_roi=core,
            spacing_policy="manual",
            manual_spacing_mm=spacing,
        )
