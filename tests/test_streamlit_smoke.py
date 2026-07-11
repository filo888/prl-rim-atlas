from __future__ import annotations

from pathlib import Path

from streamlit.testing.v1 import AppTest

from ui.styles import APP_CSS


def test_streamlit_toolbar_remains_available_for_sidebar_reopen() -> None:
    assert '[data-testid="stToolbar"] { display:none; }' not in APP_CSS


def test_streamlit_initial_load_has_no_exception() -> None:
    app_path = Path(__file__).resolve().parents[1] / "app.py"

    app = AppTest.from_file(str(app_path)).run(timeout=30)

    assert list(app.exception) == []
    assert len(app.sidebar.file_uploader) == 1
    assert app.sidebar.file_uploader[0].label == "ImageJ ROI, DICOM, or ZIP"
    assert [button.label for button in app.sidebar.button] == [
        "Try demo",
        "Clear demo",
    ]
    assert app.sidebar.button[1].disabled is True


def test_method_change_invalidates_completed_results() -> None:
    app_path = Path(__file__).resolve().parents[1] / "app.py"
    app = AppTest.from_file(str(app_path), default_timeout=60).run()
    app.sidebar.button[0].click().run()
    app.button[0].click().run()
    assert any(item.label == "Active case" for item in app.selectbox)

    app.radio[0].set_value("Pixels only (ignore DICOM spacing)").run()

    assert not any(item.label == "Active case" for item in app.selectbox)
    assert any("settings changed" in item.value for item in app.info)
