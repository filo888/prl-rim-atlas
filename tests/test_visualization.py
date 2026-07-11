from __future__ import annotations

import numpy as np

from prl.models import Canvas, CaseResult
from prl.visualization import render_overlay


def test_calibrated_overlay_uses_physical_pixel_aspect_ratio() -> None:
    mask = np.zeros((20, 20), dtype=bool)
    mask[5:15, 5:15] = True
    result = CaseResult(
        case_id="ASPECT",
        metrics={},
        rim_mask=None,
        lesion_mask=mask,
        dicom_image=None,
        spacing_mm=(2.0, 0.5),
        spacing_source="manual",
        canvas=Canvas((20, 20)),
    )

    image = render_overlay(result, focused=False)

    assert image.height / image.width == 4.0
