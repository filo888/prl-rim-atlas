from __future__ import annotations

from io import BytesIO
from typing import Callable

import numpy as np
import pytest
from pydicom.dataset import FileDataset, FileMetaDataset
from pydicom.uid import ExplicitVRLittleEndian, MRImageStorage, generate_uid
from roifile import ImagejRoi, ROI_TYPE

from prl.models import BinaryAsset


def _binary_asset(name: str, data: bytes, kind: str) -> BinaryAsset:
    return BinaryAsset(
        uid=f"test-{name}",
        name=name,
        data=data,
        kind=kind,
        source_name=name,
    )


@pytest.fixture
def point_roi_asset() -> Callable[..., BinaryAsset]:
    def factory(
        points_xy: np.ndarray | list[tuple[int, int]],
        name: str = "CASE_PRL1_mask1.roi",
        *,
        c: int = 0,
        z: int = 0,
        t: int = 0,
    ) -> BinaryAsset:
        points = np.asarray(points_xy, dtype=np.int32)
        roi = ImagejRoi.frompoints(points, name=name.removesuffix(".roi"))
        roi.roitype = ROI_TYPE.POINT
        roi.c_position = c
        roi.z_position = z
        roi.t_position = t
        return _binary_asset(name, roi.tobytes(), "roi")

    return factory


@pytest.fixture
def dicom_asset() -> Callable[..., BinaryAsset]:
    def factory(
        image: np.ndarray,
        *,
        name: str = "synthetic.dcm",
        spacing: tuple[float, float] | None = (0.7, 0.3),
        detector_spacing: tuple[float, float] | None = None,
        photometric: str = "MONOCHROME2",
    ) -> BinaryAsset:
        pixels = np.asarray(image, dtype=np.uint16)
        if pixels.ndim not in (2, 3):
            raise ValueError("Synthetic test DICOMs must be 2D or multi-frame 3D.")

        file_meta = FileMetaDataset()
        file_meta.MediaStorageSOPClassUID = MRImageStorage
        file_meta.MediaStorageSOPInstanceUID = generate_uid()
        file_meta.TransferSyntaxUID = ExplicitVRLittleEndian
        file_meta.ImplementationClassUID = generate_uid()
        ds = FileDataset(None, {}, file_meta=file_meta, preamble=b"\0" * 128)
        ds.SOPClassUID = MRImageStorage
        ds.SOPInstanceUID = file_meta.MediaStorageSOPInstanceUID
        ds.Modality = "MR"
        ds.Rows, ds.Columns = pixels.shape[-2:]
        if pixels.ndim == 3:
            ds.NumberOfFrames = pixels.shape[0]
        ds.SamplesPerPixel = 1
        ds.PhotometricInterpretation = photometric
        ds.PixelRepresentation = 0
        ds.HighBit = 15
        ds.BitsStored = 16
        ds.BitsAllocated = 16
        if spacing is not None:
            ds.PixelSpacing = [float(spacing[0]), float(spacing[1])]
        if detector_spacing is not None:
            ds.ImagerPixelSpacing = [
                float(detector_spacing[0]),
                float(detector_spacing[1]),
            ]
        ds.PixelData = pixels.astype("<u2").tobytes()
        output = BytesIO()
        ds.save_as(output, enforce_file_format=True)
        return _binary_asset(name, output.getvalue(), "dicom")

    return factory
