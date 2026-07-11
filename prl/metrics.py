from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Callable

import numpy as np
from scipy import ndimage as ndi
from skimage import morphology


@dataclass
class MetricResult:
    values: dict[str, Any]
    effective_rim: np.ndarray | None
    warnings: list[str]


def _as_mask(mask: np.ndarray | None, name: str) -> np.ndarray | None:
    if mask is None:
        return None
    arr = np.asarray(mask, dtype=bool)
    if arr.ndim != 2:
        raise ValueError(f"{name} must be a two-dimensional mask.")
    return arr


def _spacing(
    spacing_mm: tuple[float, float] | None,
) -> tuple[float, float] | None:
    if spacing_mm is None:
        return None
    try:
        row_mm, col_mm = float(spacing_mm[0]), float(spacing_mm[1])
    except Exception as exc:
        raise ValueError("Pixel spacing must contain row and column values.") from exc
    if not np.isfinite([row_mm, col_mm]).all() or min(row_mm, col_mm) <= 0:
        raise ValueError("Pixel spacing values must be finite and greater than zero.")
    return row_mm, col_mm


def split_background(mask: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    bg = ~mask.astype(bool)
    padded = np.pad(bg, 1, constant_values=True)
    labels, _ = ndi.label(padded, structure=ndi.generate_binary_structure(2, 1))
    border = np.unique(
        np.concatenate([labels[0, :], labels[-1, :], labels[:, 0], labels[:, -1]])
    )
    exterior = np.isin(labels, border)[1:-1, 1:-1] & bg
    return exterior, bg & ~exterior


def edge_perimeter_between(
    a: np.ndarray,
    b: np.ndarray,
    row_scale: float = 1.0,
    col_scale: float = 1.0,
    pad_b: bool = True,
) -> float:
    a_pad = np.pad(a.astype(bool), 1, constant_values=False)
    b_pad = np.pad(b.astype(bool), 1, constant_values=bool(pad_b))
    left_right = int(
        (a_pad[:, :-1] & b_pad[:, 1:]).sum()
        + (a_pad[:, 1:] & b_pad[:, :-1]).sum()
    )
    up_down = int(
        (a_pad[:-1, :] & b_pad[1:, :]).sum()
        + (a_pad[1:, :] & b_pad[:-1, :]).sum()
    )
    # A left/right interface is a vertical edge (row spacing); an up/down
    # interface is a horizontal edge (column spacing).
    return float(left_right * row_scale + up_down * col_scale)


def skeleton_endpoints(skeleton: np.ndarray) -> tuple[int, int]:
    s = skeleton.astype(np.uint8)
    neighbors = (
        ndi.convolve(s, np.ones((3, 3), dtype=np.uint8), mode="constant", cval=0)
        - s
    )
    endpoints = int(((s == 1) & (neighbors == 1)).sum())
    branch_pixels = int(((s == 1) & (neighbors > 2)).sum())
    return endpoints, branch_pixels


def ordered_skeleton_values(skeleton: np.ndarray, values: np.ndarray) -> np.ndarray:
    labels, count = ndi.label(skeleton.astype(bool), structure=np.ones((3, 3), dtype=int))
    output: list[float] = []
    for label in range(1, count + 1):
        coords = np.argwhere(labels == label)
        if not len(coords):
            continue
        index = {tuple(coord): idx for idx, coord in enumerate(coords)}
        neighbors: dict[int, list[int]] = {}
        for idx, (row, col) in enumerate(coords):
            local: list[int] = []
            for dr in (-1, 0, 1):
                for dc in (-1, 0, 1):
                    if dr == 0 and dc == 0:
                        continue
                    other = index.get((row + dr, col + dc))
                    if other is not None:
                        local.append(other)
            neighbors[idx] = local
        degree = np.asarray([len(neighbors[idx]) for idx in range(len(coords))])
        endpoints = np.where(degree == 1)[0]
        current = int(endpoints[0]) if endpoints.size else 0
        visited = {current}
        order = [current]
        while len(visited) < len(coords):
            candidates = [item for item in neighbors[current] if item not in visited]
            if candidates:
                nxt = candidates[0]
            else:
                remaining = [idx for idx in range(len(coords)) if idx not in visited]
                if not remaining:
                    break
                squared = np.sum((coords[remaining] - coords[current]) ** 2, axis=1)
                nxt = int(remaining[int(np.argmin(squared))])
            visited.add(nxt)
            order.append(nxt)
            current = nxt
        ordered = coords[np.asarray(order)]
        output.extend(values[ordered[:, 0], ordered[:, 1]].tolist())
    return np.asarray(output, dtype=float)


def resample_series(values: np.ndarray, min_n: int = 40, max_n: int = 60) -> np.ndarray:
    series = np.asarray(values, dtype=float)
    series = series[np.isfinite(series)]
    if series.size <= 1:
        return series
    sample_count = int(np.clip(series.size, min_n, max_n))
    return np.interp(
        np.linspace(0, series.size - 1, sample_count),
        np.arange(series.size, dtype=float),
        series,
    )


def ellipse_axes_from_mask(
    mask: np.ndarray, row_scale: float, col_scale: float
) -> tuple[float, float, float, float]:
    coords = np.argwhere(mask)
    if coords.shape[0] < 2:
        return np.nan, np.nan, np.nan, np.nan
    x = coords[:, 1].astype(float) * col_scale
    y = coords[:, 0].astype(float) * row_scale
    x -= x.mean()
    y -= y.mean()
    count = float(coords.shape[0])
    mu_xx = float(np.sum(x * x) / count) + col_scale**2 / 12.0
    mu_yy = float(np.sum(y * y) / count) + row_scale**2 / 12.0
    mu_xy = float(np.sum(x * y) / count)
    eigenvalues, eigenvectors = np.linalg.eigh(
        np.asarray([[mu_xx, mu_xy], [mu_xy, mu_yy]], dtype=float)
    )
    order = np.argsort(eigenvalues)[::-1]
    eigenvalues = np.clip(eigenvalues[order], 0.0, None)
    eigenvectors = eigenvectors[:, order]
    major = 4.0 * math.sqrt(eigenvalues[0]) if eigenvalues[0] > 0 else np.nan
    minor = 4.0 * math.sqrt(eigenvalues[1]) if eigenvalues[1] > 0 else np.nan
    eccentricity = (
        math.sqrt(max(0.0, 1.0 - eigenvalues[1] / eigenvalues[0]))
        if eigenvalues[0] > 0
        else np.nan
    )
    vector = eigenvectors[:, 0]
    orientation = math.atan2(vector[1], vector[0])
    return major, minor, eccentricity, orientation


def directional_diameters(
    mask: np.ndarray, row_scale: float, col_scale: float, n_angles: int = 60
) -> np.ndarray:
    coords = np.argwhere(mask)
    if not len(coords):
        return np.asarray([], dtype=float)
    xy = np.column_stack(
        [coords[:, 1].astype(float) * col_scale, coords[:, 0].astype(float) * row_scale]
    )
    angles = np.linspace(0.0, np.pi, n_angles, endpoint=False)
    return np.asarray(
        [
            float(np.ptp(xy @ np.asarray([math.cos(angle), math.sin(angle)])))
            for angle in angles
        ]
    )


def _summary(values: np.ndarray, function: Callable[[np.ndarray], float]) -> float:
    return float(function(values)) if values.size else np.nan


def _ratio(numerator: float, denominator: float) -> float:
    return float(numerator / denominator) if denominator else np.nan


def compute_metrics(
    rim_mask: np.ndarray | None,
    lesion_mask: np.ndarray | None,
    spacing_mm: tuple[float, float] | None = None,
    *,
    remove_overlap: bool = True,
) -> MetricResult:
    """Compute the paper-compatible metric family for either or both masks.

    Pixel metrics are always emitted. Millimetre metrics and the 1.2 mm class
    are emitted only when a validated row/column spacing pair is supplied.
    """

    rim_raw = _as_mask(rim_mask, "rim_mask")
    lesion = _as_mask(lesion_mask, "lesion_mask")
    if rim_raw is None and lesion is None:
        raise ValueError("At least one of rim_mask or lesion_mask is required.")
    shapes = {mask.shape for mask in (rim_raw, lesion) if mask is not None}
    if len(shapes) != 1:
        raise ValueError("Rim and lesion masks must have the same shape.")
    if rim_raw is not None and not np.any(rim_raw):
        raise ValueError("The rim ROI produced an empty mask.")
    if lesion is not None and not np.any(lesion):
        raise ValueError("The lesion ROI produced an empty mask.")

    calibrated = _spacing(spacing_mm)
    row_mm, col_mm = calibrated if calibrated else (np.nan, np.nan)
    pixel_area_mm2 = row_mm * col_mm if calibrated else np.nan
    warnings: list[str] = []

    overlap_px = int((rim_raw & lesion).sum()) if rim_raw is not None and lesion is not None else 0
    rim = rim_raw.copy() if rim_raw is not None else None
    if rim is not None and lesion is not None and remove_overlap:
        rim &= ~lesion
        if overlap_px:
            warnings.append(
                f"Removed {overlap_px} rim/core overlap pixel(s), matching the paper method."
            )
        if not rim.any():
            raise ValueError("Overlap cleanup removed the entire rim mask.")
    elif overlap_px:
        warnings.append(f"Retained {overlap_px} overlapping rim/core pixel(s).")

    if rim is None:
        union = lesion.copy()
    elif lesion is None:
        union = rim.copy()
    else:
        union = rim | lesion

    rim_area = int(rim.sum()) if rim is not None else None
    lesion_area = int(lesion.sum()) if lesion is not None else None
    total_area = int(union.sum())

    values: dict[str, Any] = {
        "mask1_area_rim_px": rim_area if rim_area is not None else np.nan,
        "mask2_area_lesion_core_px": lesion_area if lesion_area is not None else np.nan,
        "total_area_rim_plus_core_px": total_area,
        "mask1_area_rim_mm2": rim_area * pixel_area_mm2 if calibrated and rim_area is not None else np.nan,
        "mask2_area_lesion_core_mm2": lesion_area * pixel_area_mm2 if calibrated and lesion_area is not None else np.nan,
        "total_area_rim_plus_core_mm2": total_area * pixel_area_mm2 if calibrated else np.nan,
        "rim_interior_overlap_px_before_cleanup": overlap_px,
    }

    # Rim geometry and topology.
    if rim is not None:
        exterior, interior = split_background(rim)
        total_perimeter_px = edge_perimeter_between(rim, ~rim)
        external_perimeter_px = edge_perimeter_between(rim, exterior)
        internal_perimeter_px = edge_perimeter_between(rim, interior, pad_b=False)
        total_perimeter_mm = (
            edge_perimeter_between(rim, ~rim, row_mm, col_mm) if calibrated else np.nan
        )
        external_perimeter_mm = (
            edge_perimeter_between(rim, exterior, row_mm, col_mm) if calibrated else np.nan
        )
        internal_perimeter_mm = (
            edge_perimeter_between(rim, interior, row_mm, col_mm, pad_b=False)
            if calibrated
            else np.nan
        )

        # Explicit RNG makes medial-axis tie breaking reproducible across runs.
        skeleton = morphology.medial_axis(rim, rng=0)
        radii_px_raw = ordered_skeleton_values(skeleton, ndi.distance_transform_edt(rim))
        radii_px = resample_series(radii_px_raw)
        diameters_px_raw = 2.0 * radii_px_raw
        diameters_px = 2.0 * radii_px
        if calibrated:
            distances_mm = ndi.distance_transform_edt(rim, sampling=(row_mm, col_mm))
            radii_mm_raw = ordered_skeleton_values(skeleton, distances_mm)
            radii_mm = resample_series(radii_mm_raw)
            diameters_mm_raw = 2.0 * radii_mm_raw
            diameters_mm = 2.0 * radii_mm
        else:
            radii_mm = diameters_mm_raw = diameters_mm = np.asarray([], dtype=float)
        endpoints, branches = skeleton_endpoints(skeleton)
        parts = int(
            ndi.label(rim, structure=ndi.generate_binary_structure(2, 1))[1]
        )
        holes = int(
            ndi.label(interior, structure=ndi.generate_binary_structure(2, 1))[1]
        )
        closed = bool(holes > 0 or (parts == 1 and endpoints == 0))
        if parts > 1:
            warnings.append(
                f"The rim has {parts} disconnected components; skeleton summaries combine them."
            )

        thickness_mean_mm = _summary(diameters_mm, np.mean)
        values.update(
            {
                "mask1_perimeter_total_px": total_perimeter_px,
                "mask1_perimeter_total_mm": total_perimeter_mm,
                "mask1_perimeter_external_px": external_perimeter_px,
                "mask1_perimeter_external_mm": external_perimeter_mm,
                "mask1_rim_closed": closed,
                "mask1_internal_perimeter_px_if_closed": internal_perimeter_px if closed else np.nan,
                "mask1_internal_perimeter_mm_if_closed": internal_perimeter_mm if closed else np.nan,
                "mask1_breaking_points": endpoints,
                "mask1_branch_points": branches,
                "mask1_number_of_parts": parts,
                "mask1_internal_holes_count": holes,
                "mask1_number_of_sampled_radii_used": int(radii_px.size),
                "mask1_rim_radius_mean_px": _summary(radii_px, np.mean),
                "mask1_rim_radius_sd_px": _summary(radii_px, lambda item: np.std(item, ddof=0)),
                "mask1_rim_radius_mean_mm": _summary(radii_mm, np.mean),
                "mask1_rim_radius_sd_mm": _summary(radii_mm, lambda item: np.std(item, ddof=0)),
                "mask1_rim_equivalent_diameter_mean_px": _summary(diameters_px, np.mean),
                "mask1_rim_equivalent_diameter_sd_px": _summary(diameters_px, lambda item: np.std(item, ddof=0)),
                "mask1_rim_equivalent_diameter_mean_mm": thickness_mean_mm,
                "mask1_rim_equivalent_diameter_sd_mm": _summary(diameters_mm, lambda item: np.std(item, ddof=0)),
                "mask1_rim_thickness_max_px": _summary(diameters_px_raw, np.max),
                "mask1_rim_thickness_mean_px": _summary(diameters_px, np.mean),
                "mask1_rim_thickness_median_px": _summary(diameters_px, np.median),
                "mask1_rim_thickness_max_mm": _summary(diameters_mm_raw, np.max),
                "mask1_rim_thickness_mean_mm": thickness_mean_mm,
                "mask1_rim_thickness_median_mm": _summary(diameters_mm, np.median),
                "rim_class_using_1p2_mm_threshold": (
                    "BROAD RIM" if calibrated and thickness_mean_mm > 1.2 else
                    "NARROW RIM" if calibrated and np.isfinite(thickness_mean_mm) else
                    "Unavailable — pixel spacing required"
                ),
            }
        )
    else:
        for key in (
            "mask1_perimeter_total_px", "mask1_perimeter_total_mm",
            "mask1_perimeter_external_px", "mask1_perimeter_external_mm",
            "mask1_internal_perimeter_px_if_closed", "mask1_internal_perimeter_mm_if_closed",
            "mask1_breaking_points", "mask1_branch_points", "mask1_number_of_parts",
            "mask1_internal_holes_count", "mask1_number_of_sampled_radii_used",
            "mask1_rim_radius_mean_px", "mask1_rim_radius_sd_px",
            "mask1_rim_radius_mean_mm", "mask1_rim_radius_sd_mm",
            "mask1_rim_equivalent_diameter_mean_px", "mask1_rim_equivalent_diameter_sd_px",
            "mask1_rim_equivalent_diameter_mean_mm", "mask1_rim_equivalent_diameter_sd_mm",
            "mask1_rim_thickness_max_px", "mask1_rim_thickness_mean_px",
            "mask1_rim_thickness_median_px", "mask1_rim_thickness_max_mm",
            "mask1_rim_thickness_mean_mm", "mask1_rim_thickness_median_mm",
        ):
            values[key] = np.nan
        values["mask1_rim_closed"] = None
        values["rim_class_using_1p2_mm_threshold"] = "Unavailable — no rim ROI"

    # Lesion/core geometry.
    if lesion is not None:
        lesion_perimeter_px = edge_perimeter_between(lesion, ~lesion)
        lesion_perimeter_mm = (
            edge_perimeter_between(lesion, ~lesion, row_mm, col_mm)
            if calibrated
            else np.nan
        )
        directional_px = directional_diameters(lesion, 1.0, 1.0)
        directional_mm = (
            directional_diameters(lesion, row_mm, col_mm)
            if calibrated
            else np.asarray([], dtype=float)
        )
        equivalent_px = math.sqrt(4.0 * lesion_area / math.pi)
        equivalent_mm = (
            math.sqrt(4.0 * lesion_area * pixel_area_mm2 / math.pi)
            if calibrated
            else np.nan
        )
        major_px, minor_px, eccentricity_px, orientation_px = ellipse_axes_from_mask(
            lesion, 1.0, 1.0
        )
        if calibrated:
            major_mm, minor_mm, eccentricity, orientation = ellipse_axes_from_mask(
                lesion, row_mm, col_mm
            )
        else:
            major_mm = minor_mm = orientation = np.nan
            eccentricity = eccentricity_px
        values.update(
            {
                "mask2_perimeter_px": lesion_perimeter_px,
                "mask2_perimeter_mm": lesion_perimeter_mm,
                "mask2_lesion_equivalent_diameter_from_area_px": equivalent_px,
                "mask2_lesion_equivalent_diameter_from_area_mm": equivalent_mm,
                "mask2_lesion_directional_diameter_mean_px": _summary(directional_px, np.mean),
                "mask2_lesion_directional_diameter_sd_px": _summary(directional_px, lambda item: np.std(item, ddof=0)),
                "mask2_lesion_directional_diameter_mean_mm": _summary(directional_mm, np.mean),
                "mask2_lesion_directional_diameter_sd_mm": _summary(directional_mm, lambda item: np.std(item, ddof=0)),
                "mask2_major_axis_length_px": major_px,
                "mask2_minor_axis_length_px": minor_px,
                "mask2_major_axis_length_mm": major_mm,
                "mask2_minor_axis_length_mm": minor_mm,
                "mask2_lesion_eccentricity": eccentricity,
                "mask2_lesion_eccentricity_px": eccentricity_px,
                "mask2_major_axis_orientation_rad": orientation,
                "mask2_major_axis_orientation_rad_px": orientation_px,
                "mask2_geometry_coordinate_system": "physical mm" if calibrated else "pixel grid",
            }
        )
    else:
        for key in (
            "mask2_perimeter_px", "mask2_perimeter_mm",
            "mask2_lesion_equivalent_diameter_from_area_px",
            "mask2_lesion_equivalent_diameter_from_area_mm",
            "mask2_lesion_directional_diameter_mean_px",
            "mask2_lesion_directional_diameter_sd_px",
            "mask2_lesion_directional_diameter_mean_mm",
            "mask2_lesion_directional_diameter_sd_mm",
            "mask2_major_axis_length_px", "mask2_minor_axis_length_px",
            "mask2_major_axis_length_mm", "mask2_minor_axis_length_mm",
            "mask2_lesion_eccentricity", "mask2_lesion_eccentricity_px",
            "mask2_major_axis_orientation_rad", "mask2_major_axis_orientation_rad_px",
        ):
            values[key] = np.nan
        values["mask2_geometry_coordinate_system"] = "unavailable"

    whole_major_px, whole_minor_px, whole_ecc_px, whole_orientation_px = ellipse_axes_from_mask(
        union, 1.0, 1.0
    )
    if calibrated:
        whole_major_mm, whole_minor_mm, whole_ecc, whole_orientation = ellipse_axes_from_mask(
            union, row_mm, col_mm
        )
    else:
        whole_major_mm = whole_minor_mm = whole_orientation = np.nan
        whole_ecc = whole_ecc_px
    values.update(
        {
            "whole_lesion_major_axis_length_px": whole_major_px,
            "whole_lesion_minor_axis_length_px": whole_minor_px,
            "whole_lesion_major_axis_length_mm": whole_major_mm,
            "whole_lesion_minor_axis_length_mm": whole_minor_mm,
            "whole_lesion_eccentricity": whole_ecc,
            "whole_lesion_eccentricity_px": whole_ecc_px,
            "whole_lesion_major_axis_orientation_rad": whole_orientation,
            "whole_lesion_major_axis_orientation_rad_px": whole_orientation_px,
            "mask1_area_over_mask2_area_ratio": (
                _ratio(rim_area, lesion_area)
                if rim_area is not None and lesion_area is not None
                else np.nan
            ),
            "mask1_area_over_total_lesion_area_ratio": (
                _ratio(rim_area, rim_area + lesion_area)
                if rim_area is not None and lesion_area is not None
                else np.nan
            ),
            "mask1_area_over_union_area_ratio": (
                _ratio(rim_area, total_area) if rim_area is not None else np.nan
            ),
        }
    )
    if not calibrated:
        warnings.append(
            "No calibrated row/column spacing is available: physical metrics and the 1.2 mm class are unavailable."
        )
    return MetricResult(values=values, effective_rim=rim, warnings=warnings)
