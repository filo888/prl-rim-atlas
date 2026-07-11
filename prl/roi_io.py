from __future__ import annotations

import math
import re
from collections.abc import Iterable

import numpy as np
from roifile import ImagejRoi, ROI_TYPE
from skimage import draw

from .models import BinaryAsset, Canvas, RoiInfo


class RoiError(ValueError):
    pass


class RoiOutOfBoundsError(RoiError):
    pass


ROLE_RIM = "Rim (mask 1)"
ROLE_LESION = "Lesion core (mask 2)"
ROLE_CHOOSE = "Choose role…"
ROLE_IGNORE = "Ignore"

_LEGACY_NAME_RE = re.compile(
    r"^\s*(?P<patient>\d+)_PRL(?P<lesion>\d+)(?:[\s_-]+)?"
    r"mask\s*(?P<mask>[12])(?!\d)(?P<tail>.*)$",
    re.IGNORECASE,
)


def _strip_roi_suffix(name: str) -> str:
    leaf = name.replace("\\", "/").rsplit("/", 1)[-1]
    return leaf[:-4] if leaf.lower().endswith(".roi") else leaf


def suggest_case_and_role(name: str) -> tuple[str, str]:
    stem = _strip_roi_suffix(name).strip()
    match = _LEGACY_NAME_RE.match(stem)
    if match:
        case = f"{match.group('patient')}_PRL{match.group('lesion')}"
        role = ROLE_RIM if match.group("mask") == "1" else ROLE_LESION
        return case, role

    lowered = stem.lower()
    role = ROLE_CHOOSE
    if re.search(r"(?:^|[_\s-])(rim|mask\s*1)(?:$|[_\s(.-])", lowered):
        role = ROLE_RIM
    elif re.search(
        r"(?:^|[_\s-])(lesion|core|mask\s*2)(?:$|[_\s(.-])", lowered
    ):
        role = ROLE_LESION

    case = re.sub(
        r"(?:[_\s-]+)?(?:mask\s*[12]|rim|lesion|core)(?:\s*\(\d+\))?.*$",
        "",
        stem,
        flags=re.IGNORECASE,
    ).strip(" _-")
    return case or "Case 1", role


def read_roi(data: bytes) -> ImagejRoi:
    if not data.startswith(b"Iout"):
        raise RoiError("The file does not have a valid ImageJ ROI header (Iout).")
    try:
        roi = ImagejRoi.frombytes(data)
    except Exception as exc:  # roifile exposes several low-level exceptions
        raise RoiError(f"ImageJ ROI could not be parsed: {exc}") from exc
    return roi


def extract_coordinates(roi: ImagejRoi) -> np.ndarray:
    # Prefer explicit subpixel coordinates when present; otherwise coordinates()
    # already applies the ImageJ top/left offset for integer coordinates.
    subpixel = getattr(roi, "subpixel_coordinates", None)
    if subpixel is not None:
        arr = np.asarray(subpixel, dtype=float)
        if arr.size:
            return arr.reshape(-1, arr.shape[-1])[:, :2]

    try:
        value = roi.coordinates()
    except Exception as exc:
        raise RoiError(f"ROI coordinates could not be decoded: {exc}") from exc
    arr = np.asarray(value, dtype=float)
    if not arr.size:
        raise RoiError("The ROI contains no coordinates.")
    if arr.ndim == 3:
        arr = arr.reshape(-1, arr.shape[-1])
    if arr.ndim != 2 or arr.shape[1] < 2:
        raise RoiError("The ROI coordinate array is not two-dimensional.")
    arr = arr[:, :2]
    if not np.isfinite(arr).all():
        raise RoiError("The ROI contains non-finite coordinates.")
    return arr


def inspect_roi(asset: BinaryAsset) -> RoiInfo:
    roi = read_roi(asset.data)
    coords = extract_coordinates(roi)
    case, role = suggest_case_and_role(asset.name)
    roi_type = int(getattr(roi, "roitype", ROI_TYPE.UNKNOWN))
    try:
        roi_type_name = ROI_TYPE(roi_type).name.replace("_", " ").title()
    except ValueError:
        roi_type_name = f"Type {roi_type}"
    return RoiInfo(
        roi_type=roi_type,
        roi_type_name=roi_type_name,
        coordinate_count=int(coords.shape[0]),
        min_x=float(np.min(coords[:, 0])),
        max_x=float(np.max(coords[:, 0])),
        min_y=float(np.min(coords[:, 1])),
        max_y=float(np.max(coords[:, 1])),
        # Hyperstack ROIs encode the slice in z_position; ordinary stack ROIs
        # use position. Both are 1-based in ImageJ.
        position=int(
            getattr(roi, "z_position", 0)
            or getattr(roi, "position", 0)
            or 0
        ),
        suggested_case=case,
        suggested_role=role,
        c_position=int(getattr(roi, "c_position", 0) or 0),
        z_position=int(getattr(roi, "z_position", 0) or 0),
        t_position=int(getattr(roi, "t_position", 0) or 0),
    )


def infer_canvas(
    roi_assets: Iterable[BinaryAsset],
    padding_px: int = 12,
    max_dimension: int = 4096,
    max_pixels: int = 12_000_000,
) -> Canvas:
    coords = [extract_coordinates(read_roi(asset.data)) for asset in roi_assets]
    if not coords:
        raise RoiError("At least one ROI is required to infer a canvas.")
    all_coords = np.concatenate(coords, axis=0)
    min_x = int(math.floor(float(np.min(all_coords[:, 0]))))
    max_x = int(math.ceil(float(np.max(all_coords[:, 0]))))
    min_y = int(math.floor(float(np.min(all_coords[:, 1]))))
    max_y = int(math.ceil(float(np.max(all_coords[:, 1]))))
    col_origin = min_x - padding_px
    row_origin = min_y - padding_px
    cols = max_x - min_x + 1 + 2 * padding_px
    rows = max_y - min_y + 1 + 2 * padding_px
    if rows <= 0 or cols <= 0:
        raise RoiError("The inferred ROI canvas has invalid dimensions.")
    if rows > max_dimension or cols > max_dimension or rows * cols > max_pixels:
        raise RoiError(
            f"The inferred canvas ({rows} × {cols}) exceeds the safety limit."
        )
    return Canvas(
        shape=(rows, cols),
        row_origin=row_origin,
        col_origin=col_origin,
        source="roi_inferred_crop",
    )


def _validate_bounds(
    xs: np.ndarray,
    ys: np.ndarray,
    shape: tuple[int, int],
    asset_name: str,
) -> None:
    bad = (xs < 0) | (ys < 0) | (xs >= shape[1]) | (ys >= shape[0])
    if np.any(bad):
        count = int(np.count_nonzero(bad))
        raise RoiOutOfBoundsError(
            f"{asset_name}: {count} ROI coordinate(s) fall outside the selected "
            f"{shape[0]} × {shape[1]} image. Check the DICOM mapping/frame."
        )


def roi_to_mask(
    asset: BinaryAsset,
    canvas: Canvas,
    mode: str = "study_pixels",
) -> tuple[np.ndarray, str]:
    roi = read_roi(asset.data)
    coords = extract_coordinates(roi)
    xs = coords[:, 0] - canvas.col_origin
    ys = coords[:, 1] - canvas.row_origin
    roi_type = int(getattr(roi, "roitype", ROI_TYPE.UNKNOWN))

    resolved = mode
    if mode == "auto":
        if roi_type == int(ROI_TYPE.POINT):
            resolved = "study_pixels"
        elif roi_type in {
            int(ROI_TYPE.POLYGON),
            int(ROI_TYPE.FREEHAND),
            int(ROI_TYPE.TRACED),
        }:
            resolved = "polygon"
        elif roi_type == int(ROI_TYPE.RECT):
            resolved = "rectangle"
        elif roi_type == int(ROI_TYPE.OVAL):
            resolved = "oval"
        else:
            raise RoiError(
                f"{asset.name}: ROI type {ROI_TYPE(roi_type).name if roi_type in ROI_TYPE._value2member_map_ else roi_type} "
                "is not a filled-area ROI. Choose study pixels only if every "
                "coordinate intentionally represents one mask pixel."
            )

    mask = np.zeros(canvas.shape, dtype=bool)
    if resolved == "study_pixels":
        xi = np.rint(xs).astype(int)
        yi = np.rint(ys).astype(int)
        _validate_bounds(xi, yi, canvas.shape, asset.name)
        mask[yi, xi] = True
        return mask, "point coordinates (paper-compatible)"

    if resolved == "polygon":
        if len(xs) < 3:
            raise RoiError(f"{asset.name}: at least three points are needed for a polygon.")
        _validate_bounds(xs, ys, canvas.shape, asset.name)
        return (
            draw.polygon2mask(canvas.shape, np.column_stack([ys, xs])).astype(bool),
            "filled polygon",
        )

    left = float(getattr(roi, "left", np.min(coords[:, 0]))) - canvas.col_origin
    top = float(getattr(roi, "top", np.min(coords[:, 1]))) - canvas.row_origin
    right = float(getattr(roi, "right", np.max(coords[:, 0]) + 1)) - canvas.col_origin
    bottom = float(getattr(roi, "bottom", np.max(coords[:, 1]) + 1)) - canvas.row_origin
    _validate_bounds(
        np.asarray([left, max(left, right - 1)]),
        np.asarray([top, max(top, bottom - 1)]),
        canvas.shape,
        asset.name,
    )
    rr0, rr1 = int(math.floor(top)), int(math.ceil(bottom))
    cc0, cc1 = int(math.floor(left)), int(math.ceil(right))
    if resolved == "rectangle":
        mask[rr0:rr1, cc0:cc1] = True
        return mask, "filled rectangle"
    if resolved == "oval":
        center_r = (top + bottom - 1) / 2.0
        center_c = (left + right - 1) / 2.0
        radius_r = max((bottom - top) / 2.0, 0.5)
        radius_c = max((right - left) / 2.0, 0.5)
        rr, cc = draw.ellipse(center_r, center_c, radius_r, radius_c, shape=canvas.shape)
        mask[rr, cc] = True
        return mask, "filled oval"

    raise RoiError(f"Unknown ROI rasterization mode: {mode}")
