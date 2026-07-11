from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np


@dataclass(frozen=True)
class BinaryAsset:
    """An uploaded file, optionally originating inside a ZIP archive."""

    uid: str
    name: str
    data: bytes
    kind: str
    source_name: str
    archive_member: str | None = None


@dataclass(frozen=True)
class RoiInfo:
    roi_type: int
    roi_type_name: str
    coordinate_count: int
    min_x: float
    max_x: float
    min_y: float
    max_y: float
    position: int
    suggested_case: str
    suggested_role: str
    c_position: int
    z_position: int
    t_position: int


@dataclass(frozen=True)
class DicomInfo:
    rows: int
    cols: int
    frames: int
    samples_per_pixel: int
    photometric_interpretation: str
    transfer_syntax: str
    spacing_mm: tuple[float, float] | None
    spacing_source: str | None
    detector_spacing_mm: tuple[float, float] | None = None
    detector_spacing_source: str | None = None


@dataclass(frozen=True)
class Canvas:
    shape: tuple[int, int]
    row_origin: int = 0
    col_origin: int = 0
    source: str = "dicom"


@dataclass
class CaseResult:
    case_id: str
    metrics: dict[str, Any]
    rim_mask: np.ndarray | None
    lesion_mask: np.ndarray | None
    dicom_image: np.ndarray | None
    spacing_mm: tuple[float, float] | None
    spacing_source: str | None
    canvas: Canvas
    rim_file: str | None = None
    lesion_file: str | None = None
    dicom_file: str | None = None
    frame_number: int = 1
    warnings: list[str] = field(default_factory=list)

    @property
    def union_mask(self) -> np.ndarray:
        if self.rim_mask is None and self.lesion_mask is None:
            return np.zeros(self.canvas.shape, dtype=bool)
        if self.rim_mask is None:
            return self.lesion_mask.astype(bool)
        if self.lesion_mask is None:
            return self.rim_mask.astype(bool)
        return self.rim_mask.astype(bool) | self.lesion_mask.astype(bool)
