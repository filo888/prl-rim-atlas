# PRL RIM Atlas

PRL RIM Atlas is a deployable Streamlit application for visual quality control and morphometry of manually segmented paramagnetic rim lesions (PRLs).

This application refers to the following publication : "XXXXXXXXXXXXX"

It supports:

- one or many ImageJ `.roi` files, directly or inside `.zip` archives;
- an optional DICOM background for each case;
- a rim ROI, a lesion-core ROI, or both;
- editable case, role, DICOM, and multi-frame assignments;
- DICOM row/column spacing, manual spacing, or honest pixel-only analysis;
- overlays, grouped metrics, QC messages, and CSV/XLSX/JSON/PNG downloads.

## Run locally

Python 3.12 is recommended.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
streamlit run app.py
```

On macOS or Linux, activate the environment with `source .venv/bin/activate`.

The app includes a synthetic, non-patient demo accessible from the sidebar.

## Input behavior

### ROI + DICOM

The ROI coordinates are rasterized on the native DICOM `Rows × Columns` matrix (`x → column`, `y → row`). The selected DICOM frame is displayed in grayscale with the masks overlaid. Physical calibration is resolved in this order:

1. per-frame functional-group `PixelSpacing`;
2. shared functional-group `PixelSpacing`;
3. top-level `PixelSpacing`.

`ImagerPixelSpacing` and `NominalScannedPixelSpacing` are reported as detector/scanner fallbacks but are not silently used as patient-plane calibration.

### ROI only

The app infers a compact shared canvas and displays masks on a white background. If row and column spacing are known, choose manual calibration. Otherwise the app returns only pixel metrics; millimetre fields and the 1.2 mm rim class remain unavailable.

### Naming and roles

The study convention is detected automatically:

- `*_mask1.roi` → rim;
- `*_mask2.roi` → lesion core.

Every inferred assignment remains editable. Arbitrary filenames and single ROIs are supported by choosing the role in the mapping table.

## Metric compatibility

The default **Study-compatible selected pixels** mode matches the supplied study masks, which are ImageJ POINT ROIs where every coordinate represents one segmented pixel. The metric engine preserves the paper-era definitions:

- rim/core overlap is removed from the rim before analysis (and reported);
- areas are mask pixel counts;
- perimeters are 4-neighbour pixel-edge perimeters;
- rim radius/thickness uses the medial axis and Euclidean distance transform;
- skeleton radii are resampled to 40–60 points by sequence index;
- SD uses `ddof=0`;
- `BROAD RIM` means mean physical thickness strictly greater than 1.2 mm.

Medial-axis tie breaking is seeded to make repeated runs deterministic. `Auto by ImageJ ROI type` is available for ordinary polygon/freehand/rectangle/oval ROIs. Unsupported line-like ROI types are rejected with an actionable message.

## Test

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

## Deploy as a link

### Front-end development

The opening page includes a locally bundled, scroll-driven Three.js narrative.
It is a conceptual illustration; the existing analysis still operates on the
uploaded 2D masks. Motion can be paused and respects reduced-motion preferences.

To edit the animation, run `npm ci`, edit `ui/frontend/`, then run
`npm run build`. Commit the generated `ui/static/story.js` with the source.
No Node.js runtime or external CDN is required in the deployed app.
See [design references and implementation notes](docs/frontend-design.md).

### Streamlit Community Cloud

1. Push this directory to a GitHub repository.
2. In [Streamlit Community Cloud](https://share.streamlit.io), create an app from the repository.
3. Select `app.py` as the entrypoint and Python 3.12 in advanced settings.
4. Deploy. `requirements.txt` and `.streamlit/config.toml` are already in the expected locations.

Community Cloud runs the repository from its root and installs the pinned Python packages from `requirements.txt`; see the [official file-organization guide](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/file-organization).

### Container / institutional hosting

The included `Dockerfile` runs the app on port `8501`:

```bash
docker build -t prl-rim-atlas .
docker run --rm -p 8501:8501 prl-rim-atlas
```

Use an institution-approved private environment for clinical or identifiable data.


