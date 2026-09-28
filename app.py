from __future__ import annotations

import hashlib
import html
import math
import re
from typing import Any

import numpy as np
import pandas as pd
import streamlit as st

from prl.analysis import analyze_case
from prl.demo import demo_files
from prl.dicom_io import DicomError, inspect_dicom
from prl.exports import export_csv, export_excel, export_json
from prl.ingest import UploadError, process_uploads
from prl.models import BinaryAsset, CaseResult
from prl.roi_io import (
    ROLE_CHOOSE,
    ROLE_IGNORE,
    ROLE_LESION,
    ROLE_RIM,
    RoiError,
    infer_canvas,
    inspect_roi,
)
from prl.visualization import overlay_png_bytes, render_overlay
from ui.styles import APP_CSS
from ui.landing import render_landing, render_workspace_header


st.set_page_config(
    page_title="PRL RIM Atlas",
    page_icon="◉",
    layout="wide",
    initial_sidebar_state="auto",
    menu_items={"About": "PRL RIM Atlas — research-use morphometry workspace"},
)
st.markdown(APP_CSS, unsafe_allow_html=True)


ROI_ONLY = "ROI only · white background"
ROLE_OPTIONS = [ROLE_RIM, ROLE_LESION, ROLE_CHOOSE, ROLE_IGNORE]


def session_process_uploads(
    files: tuple[tuple[str, bytes], ...],
) -> tuple[list[BinaryAsset], list[str]]:
    # Intentionally not st.cache_data: uploaded medical-image bytes must remain
    # scoped to the user's active Streamlit session.
    return process_uploads(list(files))


def finite(value: Any) -> bool:
    if value is None:
        return False
    try:
        return bool(np.isfinite(float(value)))
    except (TypeError, ValueError):
        return False


def format_number(value: Any, decimals: int = 2) -> str:
    if isinstance(value, (bool, np.bool_)):
        return "Yes" if bool(value) else "No"
    if not finite(value):
        return "—"
    number = float(value)
    if abs(number - round(number)) < 1e-10 and abs(number) < 10000:
        return f"{int(round(number)):,}"
    return f"{number:,.{decimals}f}"


def upload_signature(assets: list[BinaryAsset]) -> str:
    return hashlib.sha256("|".join(asset.uid for asset in assets).encode()).hexdigest()[:16]


def analysis_fingerprint(
    asset_signature: str,
    mapping: pd.DataFrame,
    spacing_policy: str,
    manual_spacing: tuple[float, float] | None,
    roi_mode: str,
    remove_overlap: bool,
) -> str:
    columns = [
        "Use",
        "ROI file",
        "Case",
        "Role",
        "DICOM background",
        "Frame",
        "Asset UID",
    ]
    payload = mapping.loc[:, columns].fillna("").astype(str).to_csv(index=False)
    payload += repr(
        (asset_signature, spacing_policy, manual_spacing, roi_mode, bool(remove_overlap))
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def normalize_case(value: str) -> str:
    value = value.replace("\\", "/").rsplit("/", 1)[-1]
    value = re.sub(r"\.(dcm|dicom|roi)$", "", value, flags=re.IGNORECASE)
    value = re.sub(r"(?:[_\s-]+)?mask\s*[12].*$", "", value, flags=re.IGNORECASE)
    return re.sub(r"[^a-z0-9]", "", value.lower())


def dicom_labels(dicom_assets: list[BinaryAsset]) -> tuple[dict[str, BinaryAsset], dict[str, str]]:
    label_to_asset: dict[str, BinaryAsset] = {}
    uid_to_label: dict[str, str] = {}
    for asset in dicom_assets:
        try:
            info = inspect_dicom(asset)
            detail = f"{info.rows}×{info.cols}"
            if info.frames > 1:
                detail += f" · {info.frames} frames"
        except Exception:
            detail = "header needs review"
        leaf = asset.name.replace("\\", "/").rsplit("/", 1)[-1]
        label = f"{leaf} · {detail}"
        if label in label_to_asset:
            label += f" · {asset.uid[-4:]}"
        label_to_asset[label] = asset
        uid_to_label[asset.uid] = label
    return label_to_asset, uid_to_label


def best_dicom_label(
    case_name: str,
    dicom_assets: list[BinaryAsset],
    uid_to_label: dict[str, str],
) -> str:
    if not dicom_assets:
        return ROI_ONLY
    if len(dicom_assets) == 1:
        return uid_to_label[dicom_assets[0].uid]
    target = normalize_case(case_name)
    matches = [
        asset for asset in dicom_assets if normalize_case(asset.name) == target
    ]
    return uid_to_label[matches[0].uid] if len(matches) == 1 else ROI_ONLY


def build_mapping(
    roi_assets: list[BinaryAsset], dicom_assets: list[BinaryAsset]
) -> tuple[pd.DataFrame, dict[str, BinaryAsset]]:
    label_to_dicom, uid_to_label = dicom_labels(dicom_assets)
    rows: list[dict[str, Any]] = []
    for asset in roi_assets:
        try:
            info = inspect_roi(asset)
            case_name = info.suggested_case
            role = info.suggested_role
            roi_type = f"{info.roi_type_name} · {info.coordinate_count:,} points"
            frame = max(1, info.position)
            use = True
        except Exception as exc:
            case_name, role, roi_type, frame, use = "Needs review", ROLE_IGNORE, f"Invalid · {exc}", 1, False
        rows.append(
            {
                "Use": use,
                "ROI file": asset.name,
                "ROI type": roi_type,
                "Case": case_name,
                "Role": role,
                "DICOM background": best_dicom_label(
                    case_name, dicom_assets, uid_to_label
                ),
                "Frame": frame,
                "Asset UID": asset.uid,
            }
        )
    return pd.DataFrame(rows), label_to_dicom


def validate_assignments(
    mapping: pd.DataFrame,
    roi_by_uid: dict[str, BinaryAsset],
    dcm_by_label: dict[str, BinaryAsset],
) -> tuple[list[dict[str, Any]], list[str]]:
    problems: list[str] = []
    included = mapping.loc[mapping["Use"].astype(bool)].copy()
    included = included.loc[included["Role"] != ROLE_IGNORE]
    if included.empty:
        return [], ["Select at least one ROI for analysis."]
    if (included["Role"] == ROLE_CHOOSE).any():
        names = included.loc[included["Role"] == ROLE_CHOOSE, "ROI file"].tolist()
        problems.append("Choose Rim or Lesion core for: " + ", ".join(map(str, names[:5])))
    included["Case"] = included["Case"].astype(str).str.strip()
    if (included["Case"] == "").any():
        problems.append("Every included ROI needs a case label.")

    assignments: list[dict[str, Any]] = []
    for case_id, group in included.groupby("Case", sort=False):
        rim_rows = group.loc[group["Role"] == ROLE_RIM]
        lesion_rows = group.loc[group["Role"] == ROLE_LESION]
        if len(rim_rows) > 1:
            problems.append(f"{case_id}: more than one rim ROI is selected.")
        if len(lesion_rows) > 1:
            problems.append(f"{case_id}: more than one lesion-core ROI is selected.")
        if rim_rows.empty and lesion_rows.empty:
            problems.append(f"{case_id}: no analyzable role is selected.")
            continue
        dcm_choices = set(group["DICOM background"].astype(str))
        if len(dcm_choices) > 1:
            problems.append(f"{case_id}: all ROIs in a case must use the same DICOM.")
            continue
        frame_values: set[int] = set()
        invalid_frame = False
        for raw_value in group["Frame"]:
            try:
                numeric = float(raw_value)
            except (TypeError, ValueError):
                numeric = np.nan
            if not np.isfinite(numeric) or numeric < 1 or not numeric.is_integer():
                problems.append(
                    f"{case_id}: frame must be a whole number of 1 or greater."
                )
                invalid_frame = True
                break
            frame_values.add(int(numeric))
        if invalid_frame:
            continue
        if len(frame_values) > 1:
            problems.append(f"{case_id}: all ROIs in a case must use the same frame.")
            continue
        dcm_label = next(iter(dcm_choices))
        dcm_asset = None if dcm_label == ROI_ONLY else dcm_by_label.get(dcm_label)
        if dcm_label != ROI_ONLY and dcm_asset is None:
            problems.append(f"{case_id}: the selected DICOM is no longer available.")
            continue
        rim_asset = (
            roi_by_uid.get(str(rim_rows.iloc[0]["Asset UID"])) if len(rim_rows) == 1 else None
        )
        lesion_asset = (
            roi_by_uid.get(str(lesion_rows.iloc[0]["Asset UID"]))
            if len(lesion_rows) == 1
            else None
        )
        assignments.append(
            {
                "case_id": str(case_id),
                "rim_roi": rim_asset,
                "lesion_roi": lesion_asset,
                "dicom": dcm_asset,
                "frame_number": next(iter(frame_values)),
            }
        )
    return assignments, list(dict.fromkeys(problems))


def validate_batch_budget(assignments: list[dict[str, Any]]) -> list[str]:
    """Bound aggregate decoded/mask memory before starting a batch."""
    total_pixels = 0
    for assignment in assignments:
        try:
            if assignment["dicom"] is not None:
                info = inspect_dicom(
                    assignment["dicom"], int(assignment["frame_number"]) - 1
                )
                pixels = info.rows * info.cols
            else:
                canvas = infer_canvas(
                    [
                        asset
                        for asset in (
                            assignment["rim_roi"],
                            assignment["lesion_roi"],
                        )
                        if asset is not None
                    ]
                )
                pixels = canvas.shape[0] * canvas.shape[1]
        except Exception as exc:
            return [f"{assignment['case_id']}: preflight failed: {exc}"]
        total_pixels += pixels
        if total_pixels > 50_000_000:
            return [
                "The mapped batch exceeds the 50-million-pixel session safety budget. "
                "Analyze it in smaller batches."
            ]
    return []


def section_heading(kicker: str, title: str, copy: str) -> None:
    st.markdown(
        f'<div class="section-kicker">{html.escape(kicker)}</div>'
        f'<div class="section-title">{html.escape(title)}</div>'
        f'<div class="section-copy">{html.escape(copy)}</div>',
        unsafe_allow_html=True,
    )


def render_stepper(has_rois: bool, has_results: bool) -> None:
    states = ["active", "", ""]
    if has_rois:
        states = ["done", "active", ""]
    if has_results:
        states = ["done", "done", "active"]
    labels = ["Upload files", "Map & calibrate", "Explore results"]
    parts = [
        f'<div class="step {states[index]}"><b>{index + 1}</b><strong>{label}</strong></div>'
        for index, label in enumerate(labels)
    ]
    st.markdown('<div class="stepper">' + "".join(parts) + "</div>", unsafe_allow_html=True)


def render_onboarding() -> None:
    st.markdown(
        """
        <div class="feature-grid">
          <div class="feature-card">
            <div class="feature-icon rim">◉</div>
            <h3>ROI + DICOM</h3>
            <p>Place the rim and lesion masks directly over the source slice. Row and column spacing are read from calibrated DICOM metadata.</p>
            <ul class="mini-list"><li>Mask 1 → rim</li><li>Mask 2 → lesion core</li><li>Automatic mm and mm² metrics</li></ul>
          </div>
          <div class="feature-card">
            <div class="feature-icon core">▦</div>
            <h3>ROI only</h3>
            <p>Review colorful masks on a clean white canvas. Add known row/column spacing, or keep every result honestly in pixel units.</p>
            <ul class="mini-list"><li>Rim only, core only, or both</li><li>Manual calibration is optional</li><li>No default spacing is invented</li></ul>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.info(
        "Start in the upload panel, or open the synthetic demo. ZIP archives containing ROI/DICOM files are supported too.",
        icon="↖",
    )


def summary_strip(roi_count: int, dcm_count: int, case_count: int, calibrated_count: int) -> None:
    items = [
        ("ROI files", f"{roi_count:,}"),
        ("DICOM files", f"{dcm_count:,}"),
        ("Mapped cases", f"{case_count:,}"),
        ("DICOM calibrated", f"{calibrated_count:,}"),
    ]
    markup = "".join(
        f'<div class="summary-item"><div class="summary-label">{label}</div>'
        f'<div class="summary-value">{value}</div></div>'
        for label, value in items
    )
    st.markdown(f'<div class="summary-strip">{markup}</div>', unsafe_allow_html=True)


def kpi_card(label: str, value: str, note: str, tint: str) -> str:
    return (
        f'<div class="kpi-card" style="--tint:{tint}">'
        f'<div class="kpi-label">{html.escape(label)}</div>'
        f'<div class="kpi-value">{html.escape(value)}</div>'
        f'<div class="kpi-note">{html.escape(note)}</div></div>'
    )


def metric_table(
    result: CaseResult,
    specs: list[tuple[str, str, str | None, str, str]],
    physical: bool,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for label, pixel_key, mm_key, pixel_unit, mm_unit in specs:
        key = mm_key if physical and mm_key else pixel_key
        unit = mm_unit if physical and mm_key else pixel_unit
        value = result.metrics.get(key)
        if isinstance(value, (bool, np.bool_)):
            display = "Yes" if value else "No"
        elif isinstance(value, str):
            display = value
        else:
            display = format_number(value, 3)
        rows.append({"Metric": label, "Value": display, "Unit": unit})
    return pd.DataFrame(rows)


RIM_SPECS = [
    ("Rim area", "mask1_area_rim_px", "mask1_area_rim_mm2", "px²", "mm²"),
    ("Total perimeter", "mask1_perimeter_total_px", "mask1_perimeter_total_mm", "pixel-edge", "mm"),
    ("External perimeter", "mask1_perimeter_external_px", "mask1_perimeter_external_mm", "pixel-edge", "mm"),
    ("Internal perimeter (if closed)", "mask1_internal_perimeter_px_if_closed", "mask1_internal_perimeter_mm_if_closed", "pixel-edge", "mm"),
    ("Mean radius", "mask1_rim_radius_mean_px", "mask1_rim_radius_mean_mm", "px", "mm"),
    ("Radius SD", "mask1_rim_radius_sd_px", "mask1_rim_radius_sd_mm", "px", "mm"),
    ("Mean rim thickness", "mask1_rim_thickness_mean_px", "mask1_rim_thickness_mean_mm", "px", "mm"),
    ("Median rim thickness", "mask1_rim_thickness_median_px", "mask1_rim_thickness_median_mm", "px", "mm"),
    ("Maximum rim thickness", "mask1_rim_thickness_max_px", "mask1_rim_thickness_max_mm", "px", "mm"),
    ("Closed rim (legacy rule)", "mask1_rim_closed", None, "", ""),
    ("Breaking points", "mask1_breaking_points", None, "skeleton pixels", "skeleton pixels"),
    ("Branch points", "mask1_branch_points", None, "skeleton pixels", "skeleton pixels"),
    ("Connected parts", "mask1_number_of_parts", None, "", ""),
    ("Internal holes", "mask1_internal_holes_count", None, "", ""),
]

LESION_SPECS = [
    ("Lesion-core area", "mask2_area_lesion_core_px", "mask2_area_lesion_core_mm2", "px²", "mm²"),
    ("Perimeter", "mask2_perimeter_px", "mask2_perimeter_mm", "pixel-edge", "mm"),
    ("Area-equivalent diameter", "mask2_lesion_equivalent_diameter_from_area_px", "mask2_lesion_equivalent_diameter_from_area_mm", "px", "mm"),
    ("Mean directional diameter", "mask2_lesion_directional_diameter_mean_px", "mask2_lesion_directional_diameter_mean_mm", "px", "mm"),
    ("Directional diameter SD", "mask2_lesion_directional_diameter_sd_px", "mask2_lesion_directional_diameter_sd_mm", "px", "mm"),
    ("Major axis", "mask2_major_axis_length_px", "mask2_major_axis_length_mm", "px", "mm"),
    ("Minor axis", "mask2_minor_axis_length_px", "mask2_minor_axis_length_mm", "px", "mm"),
    ("Eccentricity", "mask2_lesion_eccentricity_px", "mask2_lesion_eccentricity", "", ""),
    ("Major-axis orientation", "mask2_major_axis_orientation_rad_px", "mask2_major_axis_orientation_rad", "rad", "rad"),
]

WHOLE_SPECS = [
    ("Whole-lesion area", "total_area_rim_plus_core_px", "total_area_rim_plus_core_mm2", "px²", "mm²"),
    ("Whole-lesion major axis", "whole_lesion_major_axis_length_px", "whole_lesion_major_axis_length_mm", "px", "mm"),
    ("Whole-lesion minor axis", "whole_lesion_minor_axis_length_px", "whole_lesion_minor_axis_length_mm", "px", "mm"),
    ("Whole-lesion eccentricity", "whole_lesion_eccentricity_px", "whole_lesion_eccentricity", "", ""),
    ("Rim / core area", "mask1_area_over_mask2_area_ratio", None, "ratio", "ratio"),
    ("Rim / (rim + core), legacy", "mask1_area_over_total_lesion_area_ratio", None, "ratio", "ratio"),
    ("Rim / union area", "mask1_area_over_union_area_ratio", None, "ratio", "ratio"),
    ("Submitted overlap", "rim_interior_overlap_px_before_cleanup", None, "px²", "px²"),
]


def batch_summary(results: list[CaseResult]) -> pd.DataFrame:
    rows = []
    for result in results:
        metrics = result.metrics
        rows.append(
            {
                "Case": result.case_id,
                "Rim": "Yes" if result.rim_mask is not None else "No",
                "Lesion core": "Yes" if result.lesion_mask is not None else "No",
                "DICOM": "Yes" if result.dicom_file else "No",
                "Spacing": result.spacing_source or "Pixels only",
                "Rim area (px²)": metrics.get("mask1_area_rim_px"),
                "Core area (px²)": metrics.get("mask2_area_lesion_core_px"),
                "Mean thickness (mm)": metrics.get("mask1_rim_thickness_mean_mm"),
                "Rim class": metrics.get("rim_class_using_1p2_mm_threshold"),
                "QC warnings": len(result.warnings),
            }
        )
    return pd.DataFrame(rows)


def render_results(results: list[CaseResult], errors: list[dict[str, str]]) -> None:
    section_heading(
        "Results workspace",
        "Morphometry, in context",
        "Inspect each mask visually, switch units, and export the full audit-ready result set.",
    )
    top_left, top_right = st.columns([3, 1])
    with top_left:
        selected_name = st.selectbox(
            "Active case", [result.case_id for result in results], key="active_case"
        )
    result = next(item for item in results if item.case_id == selected_name)
    with top_right:
        if result.spacing_mm:
            unit_label = st.radio(
                "Display units",
                ["Millimetres", "Pixels"],
                horizontal=True,
                label_visibility="collapsed",
            )
            physical = unit_label == "Millimetres"
        else:
            st.markdown('<span class="status-chip warn">Pixel units only</span>', unsafe_allow_html=True)
            physical = False

    metrics = result.metrics
    if physical:
        total_value = f"{format_number(metrics.get('total_area_rim_plus_core_mm2'))} mm²"
        thickness_value = f"{format_number(metrics.get('mask1_rim_thickness_mean_mm'))} mm"
        diameter_value = f"{format_number(metrics.get('mask2_lesion_equivalent_diameter_from_area_mm'))} mm"
        unit_note = result.spacing_source or "calibrated"
    else:
        total_value = f"{format_number(metrics.get('total_area_rim_plus_core_px'))} px²"
        thickness_value = f"{format_number(metrics.get('mask1_rim_thickness_mean_px'))} px"
        diameter_value = f"{format_number(metrics.get('mask2_lesion_equivalent_diameter_from_area_px'))} px"
        unit_note = "native pixel grid"
    if result.rim_mask is None:
        thickness_value = "Not supplied"
    if result.lesion_mask is None:
        diameter_value = "Not supplied"
    rim_state = metrics.get("rim_class_using_1p2_mm_threshold")
    if not result.spacing_mm and result.rim_mask is not None:
        closed = metrics.get("mask1_rim_closed")
        rim_state = "Closed" if closed else "Open / broken"
    cards = [
        kpi_card("Whole-lesion area", total_value, unit_note, "#eafafb"),
        kpi_card("Mean rim thickness", thickness_value, "medial-axis EDT", "#fff0f4"),
        kpi_card("Core equivalent diameter", diameter_value, "area-derived", "#eef7d4"),
        kpi_card("Rim status", str(rim_state), "1.2 mm class only when calibrated", "#f4f1ff"),
    ]
    st.markdown('<div class="kpi-grid">' + "".join(cards) + "</div>", unsafe_allow_html=True)

    viewer, controls = st.columns([2.55, 1], gap="large")
    with controls:
        st.markdown("#### Viewer controls")
        view = st.radio("Field of view", ["Focused lesion", "Full slice"], horizontal=True)
        opacity = st.slider("Mask opacity", 0.15, 0.95, 0.62, 0.05)
        layer_a, layer_b = st.columns(2)
        with layer_a:
            show_rim = st.toggle("Rim", value=result.rim_mask is not None, disabled=result.rim_mask is None)
        with layer_b:
            show_lesion = st.toggle("Core", value=result.lesion_mask is not None, disabled=result.lesion_mask is None)
        st.markdown(
            '<div class="legend"><span><i class="swatch rim"></i> Rim / mask 1</span>'
            '<span><i class="swatch core"></i> Lesion core / mask 2</span></div>',
            unsafe_allow_html=True,
        )
        status_class = "warn" if result.warnings else "ready"
        status_text = f"{len(result.warnings)} QC warning(s)" if result.warnings else "QC checks clear"
        st.markdown(
            f'<span class="status-chip {status_class}">{html.escape(status_text)}</span>',
            unsafe_allow_html=True,
        )
        st.caption(
            f"Canvas {result.canvas.shape[0]} × {result.canvas.shape[1]} · "
            + (f"DICOM frame {result.frame_number}" if result.dicom_file else "ROI-inferred canvas")
        )
        png = overlay_png_bytes(
            result,
            opacity=opacity,
            focused=view == "Focused lesion",
            show_rim=show_rim,
            show_lesion=show_lesion,
        )
        st.download_button(
            "Download overlay PNG",
            png,
            file_name=f"{result.case_id}_overlay.png",
            mime="image/png",
            width="stretch",
        )
    with viewer:
        image = render_overlay(
            result,
            opacity=opacity,
            focused=view == "Focused lesion",
            show_rim=show_rim,
            show_lesion=show_lesion,
        )
        st.image(image, width="stretch")

    overview_tab, rim_tab, lesion_tab, full_tab, qc_tab = st.tabs(
        ["Overview", "Rim", "Lesion core", "Full metrics", "QC & provenance"]
    )
    with overview_tab:
        st.markdown("#### Whole-lesion relationships")
        st.dataframe(metric_table(result, WHOLE_SPECS, physical), hide_index=True, width="stretch")
        if len(results) > 1:
            st.markdown("#### Batch overview")
            st.dataframe(batch_summary(results), hide_index=True, width="stretch")
    with rim_tab:
        if result.rim_mask is None:
            st.info("No rim ROI was assigned to this case.")
        else:
            st.dataframe(metric_table(result, RIM_SPECS, physical), hide_index=True, width="stretch")
            st.caption(
                "Paper method: 4-edge perimeter; deterministic medial-axis Euclidean distance thickness; 40–60 resampled radii."
            )
    with lesion_tab:
        if result.lesion_mask is None:
            st.info("No lesion-core ROI was assigned to this case.")
        else:
            st.dataframe(metric_table(result, LESION_SPECS, physical), hide_index=True, width="stretch")
            st.caption("Directional diameters are sampled at 60 angles; ellipse axes use second central moments.")
    with full_tab:
        full_rows = []
        for key, value in result.metrics.items():
            if isinstance(value, (bool, np.bool_)):
                display = "Yes" if value else "No"
            elif value is None or (isinstance(value, float) and not math.isfinite(value)):
                display = ""
            elif isinstance(value, (float, np.floating)):
                display = format_number(value, 6)
            else:
                display = str(value)
            full_rows.append(
                {
                    "Field": key,
                    "Value": display,
                    "Description": key.replace("mask1", "rim").replace("mask2", "lesion core").replace("_", " ").strip().capitalize(),
                }
            )
        st.dataframe(pd.DataFrame(full_rows), hide_index=True, width="stretch", height=520)
    with qc_tab:
        qc_left, qc_right = st.columns(2)
        with qc_left:
            st.markdown("#### Input & calibration")
            provenance = pd.DataFrame(
                [
                    ("DICOM", result.dicom_file or "Not supplied"),
                    ("Rim ROI", result.rim_file or "Not supplied"),
                    ("Lesion ROI", result.lesion_file or "Not supplied"),
                    ("Spacing", result.spacing_source or "Unavailable — pixel metrics only"),
                    ("Rasterization", metrics.get("roi_mode")),
                    ("Analysis", metrics.get("analysis_version")),
                ],
                columns=["Item", "Value"],
            )
            st.dataframe(provenance, hide_index=True, width="stretch")
        with qc_right:
            st.markdown("#### QC messages")
            if result.warnings:
                for warning in result.warnings:
                    st.warning(warning)
            else:
                st.success("No automated QC warnings for this case.")
            if errors:
                st.error(f"{len(errors)} other case(s) failed. See the batch export for details.")

    st.markdown("#### Export this analysis")
    download_columns = st.columns(3)
    with download_columns[0]:
        st.download_button(
            "Download CSV",
            export_csv(results),
            file_name="prl_rim_atlas_metrics.csv",
            mime="text/csv",
            width="stretch",
        )
    with download_columns[1]:
        st.download_button(
            "Download Excel + QC",
            export_excel(results, errors),
            file_name="prl_rim_atlas_results.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            width="stretch",
        )
    with download_columns[2]:
        st.download_button(
            "Download reproducibility JSON",
            export_json(results, errors),
            file_name="prl_rim_atlas_record.json",
            mime="application/json",
            width="stretch",
        )


# Sidebar: upload and session controls.
with st.sidebar:
    st.markdown(
        """
        <div class="brand-lockup">
          <div class="brand-mark">◉</div>
          <div><div class="brand-name">PRL RIM Atlas</div><div class="brand-sub">Morphometry studio</div></div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown("### 1 · Add files")
    uploaded_files = st.file_uploader(
        "ImageJ ROI, DICOM, or ZIP",
        type=["roi", "dcm", "dicom", "zip"],
        accept_multiple_files=True,
        help="Upload one or many files. ZIP archives are inspected in memory and are never extracted to a persistent folder.",
    )
    demo_col, clear_col = st.columns(2)
    with demo_col:
        if st.button("Try demo", width="stretch"):
            st.session_state["demo_mode"] = True
            st.rerun()
    with clear_col:
        if st.button("Clear demo", width="stretch", disabled=not st.session_state.get("demo_mode", False)):
            st.session_state["demo_mode"] = False
            st.rerun()
    st.markdown("---")
    st.markdown(
        '<div class="privacy-note"><strong>Research-use privacy</strong><br>Files stay in this session. Public deployments should receive de-identified DICOMs only.</div>',
        unsafe_allow_html=True,
    )

if uploaded_files:
    st.session_state["demo_mode"] = False
    raw_files = tuple((item.name, item.getvalue()) for item in uploaded_files)
elif st.session_state.get("demo_mode", False):
    raw_files = demo_files()
else:
    raw_files = tuple()

assets: list[BinaryAsset] = []
upload_notices: list[str] = []
upload_failure = None
if raw_files:
    try:
        assets, upload_notices = session_process_uploads(tuple(raw_files))
    except UploadError as exc:
        upload_failure = str(exc)

roi_assets = [asset for asset in assets if asset.kind == "roi"]
dicom_assets = [asset for asset in assets if asset.kind == "dicom"]
results: list[CaseResult] = st.session_state.get("analysis_results", [])
errors: list[dict[str, str]] = st.session_state.get("analysis_errors", [])

if not roi_assets and not upload_failure:
    render_landing()
else:
    render_workspace_header()
render_stepper(bool(roi_assets), bool(results))

if upload_failure:
    st.error(upload_failure)

if not roi_assets:
    section_heading(
        "Start here",
        "Two inputs, one coherent workflow",
        "Use DICOM when available, or analyze masks alone without pretending pixels are millimetres.",
    )
    render_onboarding()
else:
    current_signature = upload_signature(assets)
    if st.session_state.get("upload_signature") != current_signature:
        mapping_df, _ = build_mapping(roi_assets, dicom_assets)
        st.session_state["upload_signature"] = current_signature
        st.session_state["mapping_source"] = mapping_df
        st.session_state["analysis_results"] = []
        st.session_state["analysis_errors"] = []
        st.session_state.pop("analysis_fingerprint", None)
        st.session_state.pop("mapping_editor", None)
        results, errors = [], []

    initial_mapping, dcm_by_label = build_mapping(roi_assets, dicom_assets)
    mapping_source = st.session_state.get("mapping_source", initial_mapping)
    calibrated_dicom = 0
    for asset in dicom_assets:
        try:
            calibrated_dicom += int(inspect_dicom(asset).spacing_mm is not None)
        except Exception:
            pass
    suggested_cases = mapping_source.loc[mapping_source["Use"], "Case"].nunique()
    summary_strip(len(roi_assets), len(dicom_assets), int(suggested_cases), calibrated_dicom)
    for notice in upload_notices:
        st.caption(notice)

    section_heading(
        "File map",
        "Confirm what each mask represents",
        "Filename detection has made a first pass. Edit the case, role, DICOM, or frame wherever needed.",
    )
    dcm_options = [ROI_ONLY, *dcm_by_label.keys()]
    edited_mapping = st.data_editor(
        mapping_source,
        hide_index=True,
        width="stretch",
        height=min(560, 78 + 35 * len(mapping_source)),
        column_order=[
            "Use",
            "ROI file",
            "Case",
            "Role",
            "DICOM background",
            "Frame",
            "ROI type",
        ],
        column_config={
            "Use": st.column_config.CheckboxColumn("Use", width="small"),
            "ROI file": st.column_config.TextColumn("ROI file", width="medium"),
            "ROI type": st.column_config.TextColumn("Detected", width="medium"),
            "Case": st.column_config.TextColumn("Case", width="medium", required=True),
            "Role": st.column_config.SelectboxColumn("Role", options=ROLE_OPTIONS, required=True, width="medium"),
            "DICOM background": st.column_config.SelectboxColumn("DICOM background", options=dcm_options, required=True, width="large"),
            "Frame": st.column_config.NumberColumn(
                "Frame",
                min_value=1,
                step=1,
                format="%d",
                width="small",
                required=True,
            ),
            "Asset UID": None,
        },
        disabled=["ROI file", "ROI type"],
        key="mapping_editor",
    )

    section_heading(
        "Calibration & method",
        "Choose how space becomes measurement",
        "Calibrated DICOM spacing is preferred. Manual calibration is available for ROI-only studies.",
    )
    settings_left, settings_right = st.columns(2, gap="large")
    with settings_left:
        spacing_label = st.radio(
            "Measurement units",
            [
                "Use calibrated DICOM spacing; ROI-only stays in pixels",
                "Use manual spacing for every case",
                "Pixels only (ignore DICOM spacing)",
            ],
            help="Detector-plane spacing tags are not used automatically as patient-plane calibration.",
        )
        spacing_policy = {
            "Use calibrated DICOM spacing; ROI-only stays in pixels": "dicom_or_pixels",
            "Use manual spacing for every case": "manual",
            "Pixels only (ignore DICOM spacing)": "pixels_only",
        }[spacing_label]
        manual_spacing = None
        if spacing_policy == "manual":
            row_col = st.columns(2)
            with row_col[0]:
                row_spacing = st.number_input("Row spacing (mm)", min_value=0.0001, value=0.449219, format="%.6f")
            with row_col[1]:
                col_spacing = st.number_input("Column spacing (mm)", min_value=0.0001, value=0.449219, format="%.6f")
            manual_spacing = (float(row_spacing), float(col_spacing))
    with settings_right:
        roi_label = st.selectbox(
            "ROI interpretation",
            [
                "Study-compatible selected pixels",
                "Auto by ImageJ ROI type",
                "Fill every ROI as a polygon",
            ],
            help="The supplied study masks are POINT ROIs, so selected-pixel mode reproduces their intended mask area.",
        )
        roi_mode = {
            "Study-compatible selected pixels": "study_pixels",
            "Auto by ImageJ ROI type": "auto",
            "Fill every ROI as a polygon": "polygon",
        }[roi_label]
        remove_overlap = st.toggle(
            "Remove rim pixels overlapping the lesion core",
            value=True,
            help="Enabled in the paper method. The submitted overlap count is always reported for QC.",
        )
        st.caption("Medial-axis tie breaking is seeded for reproducible runs.")

    current_analysis_fingerprint = analysis_fingerprint(
        current_signature,
        edited_mapping,
        spacing_policy,
        manual_spacing,
        roi_mode,
        remove_overlap,
    )
    stored_fingerprint = st.session_state.get("analysis_fingerprint")
    if (
        stored_fingerprint
        and stored_fingerprint != current_analysis_fingerprint
        and st.session_state.get("analysis_results")
    ):
        st.session_state["analysis_results"] = []
        st.session_state["analysis_errors"] = []
        results, errors = [], []
        st.info(
            "Mapping or method settings changed. Run the analysis again to refresh results."
        )

    if st.button("Analyze mapped cases", type="primary", width="stretch"):
        roi_by_uid = {asset.uid: asset for asset in roi_assets}
        assignments, problems = validate_assignments(edited_mapping, roi_by_uid, dcm_by_label)
        if not problems:
            problems.extend(validate_batch_budget(assignments))
        if problems:
            for problem in problems:
                st.error(problem)
        else:
            progress = st.progress(0.0, text="Preparing analysis…")
            completed: list[CaseResult] = []
            failed: list[dict[str, str]] = []
            for index, assignment in enumerate(assignments):
                progress.progress(
                    index / max(1, len(assignments)),
                    text=f"Analyzing {assignment['case_id']} ({index + 1}/{len(assignments)})",
                )
                try:
                    completed.append(
                        analyze_case(
                            **assignment,
                            manual_spacing_mm=manual_spacing,
                            spacing_policy=spacing_policy,
                            roi_mode=roi_mode,
                            remove_overlap=remove_overlap,
                        )
                    )
                except Exception as exc:
                    failed.append({"case_name": assignment["case_id"], "error": str(exc)})
            progress.progress(1.0, text=f"Complete · {len(completed)} case(s) analyzed")
            st.session_state["analysis_results"] = completed
            st.session_state["analysis_errors"] = failed
            st.session_state["analysis_fingerprint"] = current_analysis_fingerprint
            results, errors = completed, failed
            if completed:
                st.success(f"Analyzed {len(completed)} case(s)." + (f" {len(failed)} failed QC." if failed else ""))
            else:
                st.error("No cases completed successfully. Review the errors below.")
            for failure in failed[:10]:
                st.error(f"{failure['case_name']}: {failure['error']}")

    results = st.session_state.get("analysis_results", results)
    errors = st.session_state.get("analysis_errors", errors)
    if results:
        st.markdown("---")
        render_results(results, errors)

st.markdown(
    '<div class="footer-note">PRL RIM Atlas · Research use only · Validate segmentations visually before scientific interpretation</div>',
    unsafe_allow_html=True,
)
