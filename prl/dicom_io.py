from __future__ import annotations

from io import BytesIO

import numpy as np
import pydicom
from pydicom.pixels import apply_modality_lut, apply_voi_lut, pixel_array as decode_pixel_array

from .models import BinaryAsset, DicomInfo


class DicomError(ValueError):
    pass


def _as_spacing(value: object) -> tuple[float, float] | None:
    try:
        values = [float(item) for item in value]  # type: ignore[arg-type]
    except Exception:
        return None
    if len(values) != 2 or not np.isfinite(values).all() or min(values) <= 0:
        return None
    return float(values[0]), float(values[1])


def _functional_group_spacing(ds: pydicom.Dataset, frame_index: int) -> tuple[tuple[float, float], str] | None:
    per_frame = getattr(ds, "PerFrameFunctionalGroupsSequence", None)
    if per_frame and 0 <= frame_index < len(per_frame):
        measures = getattr(per_frame[frame_index], "PixelMeasuresSequence", None)
        if measures:
            spacing = _as_spacing(getattr(measures[0], "PixelSpacing", None))
            if spacing:
                return spacing, f"DICOM PerFrame PixelSpacing (frame {frame_index + 1})"
    shared = getattr(ds, "SharedFunctionalGroupsSequence", None)
    if shared:
        measures = getattr(shared[0], "PixelMeasuresSequence", None)
        if measures:
            spacing = _as_spacing(getattr(measures[0], "PixelSpacing", None))
            if spacing:
                return spacing, "DICOM Shared PixelSpacing"
    return None


def resolve_pixel_spacing(
    ds: pydicom.Dataset, frame_index: int = 0
) -> tuple[tuple[float, float] | None, str | None, tuple[float, float] | None, str | None]:
    functional = _functional_group_spacing(ds, frame_index)
    if functional:
        spacing, source = functional
    else:
        spacing = _as_spacing(getattr(ds, "PixelSpacing", None))
        source = "DICOM PixelSpacing" if spacing else None

    fallback = None
    fallback_source = None
    for attr, label in (
        ("ImagerPixelSpacing", "DICOM ImagerPixelSpacing (detector plane)"),
        ("NominalScannedPixelSpacing", "DICOM NominalScannedPixelSpacing"),
    ):
        candidate = _as_spacing(getattr(ds, attr, None))
        if candidate:
            fallback, fallback_source = candidate, label
            break
    return spacing, source, fallback, fallback_source


def _read_dataset(data: bytes, *, stop_before_pixels: bool) -> pydicom.Dataset:
    try:
        ds = pydicom.dcmread(BytesIO(data), stop_before_pixels=stop_before_pixels)
    except Exception as first_exc:
        try:
            ds = pydicom.dcmread(
                BytesIO(data), stop_before_pixels=stop_before_pixels, force=True
            )
        except Exception as exc:
            raise DicomError(f"DICOM could not be parsed: {exc}") from first_exc
    required = ("Rows", "Columns")
    if any(not hasattr(ds, attr) for attr in required):
        raise DicomError("The file is missing required DICOM image dimensions.")
    return ds


def inspect_dicom(asset: BinaryAsset, frame_index: int = 0) -> DicomInfo:
    ds = _read_dataset(asset.data, stop_before_pixels=True)
    rows, cols = int(ds.Rows), int(ds.Columns)
    frames = int(getattr(ds, "NumberOfFrames", 1) or 1)
    if rows <= 0 or cols <= 0 or frames <= 0:
        raise DicomError("The DICOM contains invalid image dimensions.")
    samples = int(getattr(ds, "SamplesPerPixel", 1) or 1)
    if rows * cols * samples > 12_000_000:
        raise DicomError("A decoded DICOM frame would exceed the application safety limit.")
    spacing, source, fallback, fallback_source = resolve_pixel_spacing(ds, frame_index)
    transfer_syntax = "Unknown"
    try:
        transfer_syntax = str(ds.file_meta.TransferSyntaxUID)
    except Exception:
        pass
    return DicomInfo(
        rows=rows,
        cols=cols,
        frames=frames,
        samples_per_pixel=int(getattr(ds, "SamplesPerPixel", 1) or 1),
        photometric_interpretation=str(
            getattr(ds, "PhotometricInterpretation", "Unknown")
        ),
        transfer_syntax=transfer_syntax,
        spacing_mm=spacing,
        spacing_source=source,
        detector_spacing_mm=fallback,
        detector_spacing_source=fallback_source,
    )


def _select_frame(
    arr: np.ndarray,
    ds: pydicom.Dataset,
    frame_index: int,
    *,
    already_selected: bool = False,
) -> np.ndarray:
    frames = int(getattr(ds, "NumberOfFrames", 1) or 1)
    samples = int(getattr(ds, "SamplesPerPixel", 1) or 1)
    if frame_index < 0 or frame_index >= frames:
        raise DicomError(f"Frame {frame_index + 1} is outside the 1–{frames} range.")
    if frames > 1 and not already_selected:
        arr = arr[frame_index]
    if samples > 1:
        if arr.ndim != 3 or arr.shape[-1] < 3:
            raise DicomError("The color DICOM pixel layout is not supported.")
        arr = np.dot(arr[..., :3], np.asarray([0.2126, 0.7152, 0.0722]))
    if arr.ndim != 2:
        raise DicomError(f"Expected a 2D frame; decoded pixel shape is {arr.shape}.")
    return np.asarray(arr)


def decode_dicom(
    asset: BinaryAsset, frame_index: int = 0
) -> tuple[np.ndarray, DicomInfo, list[str]]:
    ds = _read_dataset(asset.data, stop_before_pixels=False)
    info = inspect_dicom(asset, frame_index)
    warnings: list[str] = []
    try:
        # A file-like source plus index lets pydicom decode only the requested
        # frame instead of materializing the complete multi-frame pixel set.
        raw = _select_frame(
            np.asarray(decode_pixel_array(BytesIO(asset.data), index=frame_index)),
            ds,
            frame_index,
            already_selected=True,
        )
    except Exception as exc:
        if isinstance(exc, DicomError):
            raise
        raise DicomError(
            "DICOM pixels could not be decoded. The transfer syntax may need a "
            f"decoder not available on this server: {exc}"
        ) from exc

    try:
        display = np.asarray(apply_modality_lut(raw, ds), dtype=float)
    except Exception:
        display = raw.astype(float)
        warnings.append("The modality LUT/rescale could not be applied; raw pixel values were used.")
    if hasattr(ds, "VOILUTSequence") or (
        hasattr(ds, "WindowCenter") and hasattr(ds, "WindowWidth")
    ):
        try:
            display = np.asarray(apply_voi_lut(display, ds), dtype=float)
        except Exception:
            warnings.append("The DICOM VOI/window could not be applied; percentile contrast was used.")

    finite = display[np.isfinite(display)]
    if finite.size == 0:
        raise DicomError("The selected DICOM frame contains no finite pixel values.")
    low, high = np.percentile(finite, [1.0, 99.0])
    if high <= low:
        low, high = float(np.min(finite)), float(np.max(finite))
    if high <= low:
        normalized = np.zeros(display.shape, dtype=np.uint8)
    else:
        normalized = np.clip((display - low) / (high - low), 0.0, 1.0)
        normalized = np.rint(normalized * 255.0).astype(np.uint8)
    if str(getattr(ds, "PhotometricInterpretation", "")).upper() == "MONOCHROME1":
        normalized = 255 - normalized
    return normalized, info, warnings
