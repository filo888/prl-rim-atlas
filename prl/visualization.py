from __future__ import annotations

from io import BytesIO

import numpy as np
from PIL import Image
from scipy import ndimage as ndi

from .models import CaseResult


RIM_COLOR = np.asarray([239, 78, 119], dtype=float)
LESION_COLOR = np.asarray([25, 182, 200], dtype=float)


def _crop_bounds(mask: np.ndarray, padding: int = 18) -> tuple[slice, slice]:
    coordinates = np.argwhere(mask)
    if not len(coordinates):
        return slice(0, mask.shape[0]), slice(0, mask.shape[1])
    row_min, col_min = np.min(coordinates, axis=0)
    row_max, col_max = np.max(coordinates, axis=0)
    return (
        slice(max(0, int(row_min) - padding), min(mask.shape[0], int(row_max) + padding + 1)),
        slice(max(0, int(col_min) - padding), min(mask.shape[1], int(col_max) + padding + 1)),
    )


def _blend(rgb: np.ndarray, mask: np.ndarray, color: np.ndarray, opacity: float) -> None:
    if not np.any(mask):
        return
    rgb[mask] = rgb[mask] * (1.0 - opacity) + color * opacity
    outline = ndi.binary_dilation(mask, iterations=1) & ~mask
    rgb[outline] = rgb[outline] * 0.2 + color * 0.8


def render_overlay(
    result: CaseResult,
    *,
    opacity: float = 0.62,
    focused: bool = True,
    show_rim: bool = True,
    show_lesion: bool = True,
) -> Image.Image:
    shape = result.canvas.shape
    if result.dicom_image is None:
        rgb = np.full((*shape, 3), 250.0, dtype=float)
        # A faint grid makes pixel-based geometry legible on a white canvas.
        rgb[::16, :, :] = 244.0
        rgb[:, ::16, :] = 244.0
    else:
        base = np.asarray(result.dicom_image, dtype=np.uint8)
        if base.shape != shape:
            raise ValueError(
                f"DICOM image shape {base.shape} does not match analysis canvas {shape}."
            )
        rgb = np.repeat(base[..., None], 3, axis=2).astype(float)

    if show_lesion and result.lesion_mask is not None:
        _blend(rgb, result.lesion_mask, LESION_COLOR, opacity)
    if show_rim and result.rim_mask is not None:
        _blend(rgb, result.rim_mask, RIM_COLOR, opacity)

    if focused:
        rows, cols = _crop_bounds(result.union_mask)
        rgb = rgb[rows, cols]
    image = Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8), mode="RGB")
    # Render calibrated images with their physical row/column aspect ratio.
    # Nearest-neighbour resampling keeps point-ROI boundaries inspectable.
    if result.spacing_mm:
        row_mm, col_mm = result.spacing_mm
        physical_width = image.width * col_mm
        physical_height = image.height * row_mm
        scale = 900.0 / max(physical_width, physical_height)
        target = (
            max(1, int(round(physical_width * scale))),
            max(1, int(round(physical_height * scale))),
        )
        image = image.resize(target, resample=Image.Resampling.NEAREST)
    else:
        longest = max(image.size)
        if longest < 720:
            factor = min(8, max(2, 720 // max(1, longest)))
            image = image.resize(
                (image.width * factor, image.height * factor),
                resample=Image.Resampling.NEAREST,
            )
    return image


def overlay_png_bytes(result: CaseResult, **kwargs: object) -> bytes:
    buffer = BytesIO()
    render_overlay(result, **kwargs).save(buffer, format="PNG", optimize=True)
    return buffer.getvalue()
