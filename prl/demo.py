from __future__ import annotations

from functools import lru_cache
from io import BytesIO

import numpy as np
from pydicom.dataset import FileDataset, FileMetaDataset
from pydicom.uid import ExplicitVRLittleEndian, MRImageStorage
from roifile import ImagejRoi, ROI_TYPE


def _point_roi(points_xy: np.ndarray, name: str) -> bytes:
    roi = ImagejRoi.frompoints(points_xy.astype(np.int32), name=name)
    roi.roitype = ROI_TYPE.POINT
    return roi.tobytes()


def _demo_dicom(image: np.ndarray) -> bytes:
    file_meta = FileMetaDataset()
    file_meta.MediaStorageSOPClassUID = MRImageStorage
    file_meta.MediaStorageSOPInstanceUID = "1.2.826.0.1.3680043.10.543.2026071101"
    file_meta.TransferSyntaxUID = ExplicitVRLittleEndian
    file_meta.ImplementationClassUID = "1.2.826.0.1.3680043.10.543.1"
    ds = FileDataset(None, {}, file_meta=file_meta, preamble=b"\0" * 128)
    ds.SOPClassUID = MRImageStorage
    ds.SOPInstanceUID = file_meta.MediaStorageSOPInstanceUID
    ds.Modality = "MR"
    ds.Rows, ds.Columns = image.shape
    ds.SamplesPerPixel = 1
    ds.PhotometricInterpretation = "MONOCHROME2"
    ds.PixelRepresentation = 0
    ds.HighBit = 15
    ds.BitsStored = 16
    ds.BitsAllocated = 16
    ds.PixelSpacing = [0.55, 0.55]
    ds.WindowCenter = 1450
    ds.WindowWidth = 1800
    ds.PixelData = image.astype("<u2").tobytes()
    output = BytesIO()
    ds.save_as(output, enforce_file_format=True)
    return output.getvalue()


@lru_cache(maxsize=1)
def demo_files() -> tuple[tuple[str, bytes], ...]:
    size = 160
    rows, cols = np.ogrid[:size, :size]
    center_r, center_c = 82, 78
    radius2 = (rows - center_r) ** 2 + (cols - center_c) ** 2
    rng = np.random.default_rng(1107)
    background = 620 + 180 * np.sin(cols / 17.0) + 120 * np.cos(rows / 23.0)
    tissue = 450 * np.exp(-(((rows - 80) / 58) ** 2 + ((cols - 80) / 49) ** 2))
    lesion_signal = 710 * np.exp(-radius2 / (2 * 13**2))
    image = np.clip(background + tissue + lesion_signal + rng.normal(0, 42, (size, size)), 0, 4095)
    core = radius2 <= 14**2
    rim = (radius2 >= 16**2) & (radius2 <= 20**2)
    lesion_points = np.column_stack(np.where(core))[:, ::-1]
    rim_points = np.column_stack(np.where(rim))[:, ::-1]
    return (
        ("DEMO_PRL1.dcm", _demo_dicom(image.astype(np.uint16))),
        ("DEMO_PRL1_mask1.roi", _point_roi(rim_points, "synthetic_rim")),
        ("DEMO_PRL1_mask2.roi", _point_roi(lesion_points, "synthetic_core")),
    )
