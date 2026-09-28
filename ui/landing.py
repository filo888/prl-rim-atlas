"""Presentation-only, locally bundled scroll narrative. No patient data enters it."""

from pathlib import Path

import streamlit as st


_ROOT = Path(__file__).resolve().parent
_story = st.components.v2.component(
    "prl_atlas_story",
    html=(_ROOT / "frontend" / "story.html").read_text(encoding="utf-8"),
    css=(_ROOT / "frontend" / "story.css").read_text(encoding="utf-8"),
    js=(_ROOT / "static" / "story.js").read_text(encoding="utf-8"),
    isolate_styles=True,
)


def render_landing() -> None:
    _story(key="prl_atlas_story", height="content", width="stretch")


def render_workspace_header() -> None:
    st.markdown(
        '<div class="workspace-header"><div><span class="workspace-eyebrow">PRL RIM Atlas</span>'
        '<h1>Your morphometry workspace.</h1>'
        '<p>From manually delineated masks to reproducible measurements.</p></div>'
        '<div class="workspace-key"><span><i class="swatch rim"></i>Rim</span>'
        '<span><i class="swatch core"></i>Lesion core</span></div></div>',
        unsafe_allow_html=True,
    )
