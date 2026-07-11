from __future__ import annotations

from importlib.metadata import version
from typing import Any

import numpy as np

from .dicom_io import DicomError, decode_dicom, inspect_dicom
from .metrics import compute_metrics
from .models import BinaryAsset, Canvas, CaseResult
from .roi_io import ROI_TYPE, infer_canvas, inspect_roi, roi_to_mask


ANALYSIS_VERSION = "PRL-RIM-Atlas 1.0 / deterministic paper method"


def _validate_manual_spacing(
    spacing_mm: tuple[float, float] | None,
) -> tuple[float, float] | None:
    if spacing_mm is None:
        return None
    values = tuple(float(value) for value in spacing_mm)
    if len(values) != 2 or not np.isfinite(values).all() or min(values) <= 0:
        raise ValueError("Manual row and column spacing must be finite and greater than zero.")
    return values[0], values[1]


def analyze_case(
    case_id: str,
    *,
    rim_roi: BinaryAsset | None = None,
    lesion_roi: BinaryAsset | None = None,
    dicom: BinaryAsset | None = None,
    frame_number: int = 1,
    manual_spacing_mm: tuple[float, float] | None = None,
    spacing_policy: str = "dicom_or_pixels",
    roi_mode: str = "study_pixels",
    remove_overlap: bool = True,
) -> CaseResult:
    if rim_roi is None and lesion_roi is None:
        raise ValueError(f"{case_id}: assign at least one ROI.")
    case_id = str(case_id).strip()
    if not case_id:
        raise ValueError("Every included ROI needs a case label.")
    if frame_number < 1:
        raise ValueError(f"{case_id}: DICOM frame numbers are 1-based.")

    warnings: list[str] = []
    dicom_image = None
    dicom_info = None
    frame_index = frame_number - 1
    if dicom is not None:
        dicom_info = inspect_dicom(dicom, frame_index)
        if frame_number > dicom_info.frames:
            raise ValueError(
                f"{case_id}: frame {frame_number} exceeds the DICOM's {dicom_info.frames} frame(s)."
            )
        canvas = Canvas(shape=(dicom_info.rows, dicom_info.cols), source="dicom_rows_columns")
        try:
            dicom_image, decoded_info, decode_warnings = decode_dicom(dicom, frame_index)
            dicom_info = decoded_info
            warnings.extend(decode_warnings)
        except DicomError as exc:
            warnings.append(
                f"DICOM background could not be rendered, but dimensions remain usable: {exc}"
            )
    else:
        canvas = infer_canvas([asset for asset in (rim_roi, lesion_roi) if asset is not None])

    manual_spacing = _validate_manual_spacing(manual_spacing_mm)
    if spacing_policy == "manual":
        if manual_spacing is None:
            raise ValueError(f"{case_id}: manual spacing was selected but no values were provided.")
        spacing = manual_spacing
        spacing_source = "Manual row/column spacing"
    elif spacing_policy == "pixels_only":
        spacing = None
        spacing_source = None
    elif spacing_policy == "dicom_or_pixels":
        spacing = dicom_info.spacing_mm if dicom_info is not None else None
        spacing_source = dicom_info.spacing_source if dicom_info is not None else None
        if dicom_info is not None and spacing is None and dicom_info.detector_spacing_mm:
            warnings.append(
                f"{dicom_info.detector_spacing_source} is present but was not used as patient-plane calibration. "
                "Choose manual calibration to use a confirmed value."
            )
    else:
        raise ValueError(f"Unknown spacing policy: {spacing_policy}")

    rim_mask = lesion_mask = None
    rasterization: dict[str, str] = {}
    for role, asset in (("rim", rim_roi), ("lesion core", lesion_roi)):
        if asset is None:
            continue
        roi_info = inspect_roi(asset)
        if roi_info.c_position > 1 or roi_info.t_position > 1:
            raise ValueError(
                f"{asset.name}: ImageJ hyperstack channel/time metadata "
                f"(C={roi_info.c_position}, T={roi_info.t_position}) cannot be mapped "
                "unambiguously to a single DICOM frame. Export the intended slice ROI "
                "or provide a plain stack ROI."
            )
        if roi_mode == "study_pixels" and roi_info.roi_type != int(ROI_TYPE.POINT):
            raise ValueError(
                f"{asset.name} is a {roi_info.roi_type_name} ROI but is being treated as isolated pixels. "
                "Choose Auto by ImageJ ROI type (or polygon fill) for non-POINT ROIs."
            )
        mask, method = roi_to_mask(asset, canvas, mode=roi_mode)
        rasterization[role] = method
        if role == "rim":
            rim_mask = mask
        else:
            lesion_mask = mask

    metric_result = compute_metrics(
        rim_mask,
        lesion_mask,
        spacing,
        remove_overlap=remove_overlap,
    )
    warnings.extend(metric_result.warnings)
    effective_rim = metric_result.effective_rim

    provenance: dict[str, Any] = {
        "case_name": case_id,
        "analysis_version": ANALYSIS_VERSION,
        "medial_axis_rng_seed": 0,
        "scikit_image_version": version("scikit-image"),
        "mask1_file": rim_roi.name if rim_roi else "not supplied",
        "mask2_file": lesion_roi.name if lesion_roi else "not supplied",
        "dcm_file": dicom.name if dicom else "not supplied",
        "dicom_used": dicom is not None,
        "dicom_frame_number": frame_number if dicom else np.nan,
        "roi_mode": roi_mode,
        "rim_rasterization": rasterization.get("rim", "not supplied"),
        "lesion_rasterization": rasterization.get("lesion core", "not supplied"),
        "remove_rim_interior_overlap": remove_overlap,
        "pixel_spacing_row_mm": spacing[0] if spacing else np.nan,
        "pixel_spacing_col_mm": spacing[1] if spacing else np.nan,
        "pixel_area_mm2": spacing[0] * spacing[1] if spacing else np.nan,
        "spacing_source": spacing_source or "unavailable — pixel metrics only",
        "image_rows": canvas.shape[0],
        "image_cols": canvas.shape[1],
        "image_shape_source": canvas.source,
        "canvas_row_origin": canvas.row_origin,
        "canvas_col_origin": canvas.col_origin,
    }
    metrics = {**provenance, **metric_result.values}
    return CaseResult(
        case_id=case_id,
        metrics=metrics,
        rim_mask=effective_rim,
        lesion_mask=lesion_mask,
        dicom_image=dicom_image,
        spacing_mm=spacing,
        spacing_source=spacing_source,
        canvas=canvas,
        rim_file=rim_roi.name if rim_roi else None,
        lesion_file=lesion_roi.name if lesion_roi else None,
        dicom_file=dicom.name if dicom else None,
        frame_number=frame_number,
        warnings=list(dict.fromkeys(warnings)),
    )
