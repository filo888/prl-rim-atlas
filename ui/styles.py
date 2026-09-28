APP_CSS = r"""
<style>
:root {
  --ink: #152f40;
  --muted: #617787;
  --paper: #f5f8fb;
  --panel: rgba(255,255,255,.86);
  --line: rgba(22,50,59,.11);
  --rim: #ef4e77;
  --rim-soft: #fff0f4;
  --core: #19b6c8;
  --core-soft: #eafafb;
  --lime: #a6ebe3;
  --navy: #071722;
}

html, body, [class*="css"] { font-family: "Aptos", "Segoe UI", Inter, sans-serif; }
.stApp {
  color: var(--ink);
  background: #f5f8fb;
}
[data-testid="stHeader"] { background: transparent; }
[data-testid="stToolbar"] { right: 0; }
.block-container { max-width: 1600px; padding: 4.4rem 2.2rem 3rem; }
[data-testid="stSidebarCollapseButton"] { visibility: visible !important; }
[data-testid="stExpandSidebarButton"] { color:#152f40; border:1px solid #cad7e1; border-radius:7px; background:#fff; }

section[data-testid="stSidebar"] {
  background: #0b2230;
  border-right: 0;
  box-shadow: 14px 0 45px rgba(14,43,53,.08);
}
section[data-testid="stSidebar"] * { color: #edf7f5; }
section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p,
section[data-testid="stSidebar"] small { color: #b9cfce; }
section[data-testid="stSidebar"] hr { border-color: rgba(255,255,255,.12); }
section[data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] {
  background: rgba(255,255,255,.075);
  border: 1px dashed rgba(198,232,107,.56);
  border-radius: 18px;
}
section[data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] button {
  background: #a6ebe3; color: #152f40; border: 0;
}
section[data-testid="stSidebar"] .stButton > button:not(:disabled) {
  background: rgba(255,255,255,.08) !important;
  color: #f5fffc !important;
  border: 1px solid rgba(255,255,255,.28) !important;
}
section[data-testid="stSidebar"] .stButton > button:not(:disabled) p { color:#f5fffc !important; }
section[data-testid="stSidebar"] .stButton > button:not(:disabled):hover {
  background: rgba(198,232,107,.15) !important;
  border-color: #c6e86b !important;
}
section[data-testid="stSidebar"] button[data-testid="stBaseButton-secondary"]:not(:disabled) {
  background: #a6ebe3 !important;
  color: #17343c !important;
  border-color: #a6ebe3 !important;
}
section[data-testid="stSidebar"] button[data-testid="stBaseButton-secondary"]:not(:disabled) p {
  color: #17343c !important;
}
section[data-testid="stSidebar"] [data-baseweb="select"] > div,
section[data-testid="stSidebar"] input {
  background: rgba(255,255,255,.09) !important;
  border-color: rgba(255,255,255,.18) !important;
  color: white !important;
}

.brand-lockup { display:flex; align-items:center; gap:.72rem; margin:.2rem 0 1.35rem; }
.brand-mark {
  width: 2.45rem; height: 2.45rem; border-radius: 13px; display:grid; place-items:center;
  background: #15394b;
  color:#f47f96; font-weight:900; box-shadow: inset 0 0 0 1px rgba(109,219,214,.25);
}
.brand-name { font-size:1.03rem; font-weight:800; letter-spacing:.02em; color:#fff; }
.brand-sub { font-size:.78rem; letter-spacing:.03em; color:#a6c1cb; }

.hero {
  position: relative; overflow:hidden; min-height: 235px; border-radius: 30px;
  padding: 2.3rem 2.65rem; margin-bottom: 1.15rem;
  color:#f8fffc; background:
    linear-gradient(118deg, rgba(16,47,58,.99), rgba(18,67,77,.95) 58%, rgba(19,86,93,.91));
  box-shadow: 0 22px 60px rgba(16,47,58,.17);
}
.hero:before, .hero:after { content:""; position:absolute; border-radius:999px; pointer-events:none; }
.hero:before { width:370px; height:370px; right:-85px; top:-170px; border:52px solid rgba(25,182,200,.16); }
.hero:after { width:240px; height:240px; right:185px; bottom:-180px; border:36px solid rgba(239,78,119,.13); }
.hero-kicker { color:var(--lime); font-size:.76rem; letter-spacing:.16em; text-transform:uppercase; font-weight:800; }
.hero h1 { color:white; max-width:850px; margin:.48rem 0 .55rem; font-size:clamp(2.2rem,4vw,4rem); line-height:.98; letter-spacing:-.045em; }
.hero p { max-width:740px; margin:0; color:#cce0df; font-size:1.02rem; line-height:1.55; }
.hero-meta { display:flex; gap:.55rem; flex-wrap:wrap; margin-top:1.35rem; }
.hero-chip { border:1px solid rgba(255,255,255,.18); background:rgba(255,255,255,.075); border-radius:99px; padding:.42rem .72rem; color:#e9f5f2; font-size:.78rem; }

.stepper { display:grid; grid-template-columns:repeat(3,1fr); gap:.7rem; margin:1rem 0 1.55rem; }
.step { display:flex; align-items:center; gap:.7rem; border:1px solid var(--line); border-radius:16px; background:rgba(255,255,255,.66); padding:.72rem .9rem; color:var(--muted); }
.step b { display:grid; place-items:center; width:1.7rem; height:1.7rem; border-radius:50%; background:#e7ecea; color:#6b7d80; font-size:.75rem; }
.step strong { font-size:.82rem; color:inherit; }
.step.done { border-color:rgba(25,182,200,.28); background:#f2fbfa; color:#1b6770; }
.step.done b { background:var(--core); color:white; }
.step.active { border-color:rgba(239,78,119,.35); background:#fff5f7; color:#ad3152; box-shadow:0 8px 24px rgba(239,78,119,.08); }
.step.active b { background:var(--rim); color:white; }

.section-kicker { margin-top:.35rem; color:#8a9a9c; font-size:.73rem; text-transform:uppercase; letter-spacing:.14em; font-weight:800; }
.section-title { margin:.15rem 0 .25rem; color:var(--ink); font-size:1.62rem; font-weight:850; letter-spacing:-.025em; }
.section-copy { color:var(--muted); margin-bottom:1rem; }

.feature-grid { display:grid; grid-template-columns:repeat(2,1fr); gap:1rem; }
.feature-card, .soft-card {
  border:1px solid var(--line); border-radius:24px; padding:1.45rem; background:var(--panel);
  box-shadow:0 14px 40px rgba(31,56,62,.055); backdrop-filter:blur(10px);
}
.feature-icon { width:2.55rem; height:2.55rem; display:grid; place-items:center; border-radius:14px; font-size:1.2rem; margin-bottom:.8rem; }
.feature-icon.rim { background:var(--rim-soft); color:var(--rim); }
.feature-icon.core { background:var(--core-soft); color:#048799; }
.feature-card h3 { margin:.1rem 0 .4rem; font-size:1.05rem; color:var(--ink); }
.feature-card p { margin:0; color:var(--muted); line-height:1.5; }
.mini-list { margin:.8rem 0 0; padding:0; list-style:none; color:#52696f; font-size:.86rem; }
.mini-list li { margin:.4rem 0; }
.mini-list li:before { content:"\2713"; color:#0c9caf; font-weight:900; margin-right:.5rem; }

.summary-strip { display:grid; grid-template-columns:repeat(4,1fr); gap:.7rem; margin:.8rem 0 1.35rem; }
.summary-item { border-radius:18px; padding:1rem 1.05rem; background:rgba(255,255,255,.75); border:1px solid var(--line); }
.summary-label { color:#7a8d90; text-transform:uppercase; letter-spacing:.09em; font-size:.66rem; font-weight:800; }
.summary-value { margin-top:.2rem; color:var(--ink); font-size:1.22rem; font-weight:850; }

.kpi-grid { display:grid; grid-template-columns:repeat(4,1fr); gap:.75rem; margin:.85rem 0 1.2rem; }
.kpi-card { position:relative; overflow:hidden; min-height:128px; border-radius:20px; padding:1.05rem 1.08rem; background:#fff; border:1px solid var(--line); box-shadow:0 10px 30px rgba(22,50,59,.05); }
.kpi-card:after { content:""; position:absolute; width:74px; height:74px; border-radius:50%; right:-30px; top:-31px; background:var(--tint,#eafafb); }
.kpi-label { color:#73878b; font-size:.72rem; text-transform:uppercase; letter-spacing:.09em; font-weight:800; }
.kpi-value { color:var(--ink); margin-top:.48rem; font-size:1.55rem; font-weight:900; letter-spacing:-.035em; line-height:1.05; }
.kpi-note { color:#8b9a9c; margin-top:.42rem; font-size:.72rem; }

.legend { display:flex; gap:.7rem; flex-wrap:wrap; align-items:center; color:#667b80; font-size:.78rem; margin:.5rem 0 .8rem; }
.legend span { display:inline-flex; align-items:center; gap:.35rem; }
.swatch { width:.7rem; height:.7rem; border-radius:4px; display:inline-block; }
.swatch.rim { background:var(--rim); box-shadow:0 0 0 3px rgba(239,78,119,.12); }
.swatch.core { background:var(--core); box-shadow:0 0 0 3px rgba(25,182,200,.12); }

.status-line { display:flex; align-items:center; justify-content:space-between; gap:1rem; margin:.2rem 0 .4rem; }
.status-chip { display:inline-flex; align-items:center; gap:.38rem; border-radius:99px; padding:.38rem .66rem; font-size:.72rem; font-weight:800; }
.status-chip.ready { background:#eaf8ee; color:#267043; }
.status-chip.warn { background:#fff6e4; color:#8a5e0a; }
.privacy-note { border-left:3px solid var(--lime); padding:.25rem 0 .25rem .7rem; color:#b9cfce; font-size:.76rem; line-height:1.4; }

[data-testid="stVerticalBlockBorderWrapper"] { border-color:var(--line) !important; border-radius:22px !important; background:rgba(255,255,255,.63); }
[data-testid="stDataFrame"] { border:1px solid var(--line); border-radius:16px; overflow:hidden; }
[data-baseweb="tab-list"] { gap:.25rem; border-bottom:1px solid var(--line); }
[data-baseweb="tab"] { border-radius:12px 12px 0 0; padding:.65rem .9rem; }
[data-baseweb="tab"][aria-selected="true"] { color:var(--rim); background:#fff4f7; }
.stButton > button, .stDownloadButton > button { border-radius:12px; font-weight:750; border-color:rgba(22,50,59,.14); min-height:2.65rem; }
.stButton > button[kind="primary"] { background:linear-gradient(120deg,#ef4e77,#f26f69); border:0; box-shadow:0 9px 20px rgba(239,78,119,.2); }
.stButton > button:hover, .stDownloadButton > button:hover { border-color:var(--rim); color:var(--rim); }
[data-testid="stAlert"] { border-radius:15px; }
div[data-testid="stImage"] img { border-radius:20px; border:1px solid var(--line); box-shadow:0 16px 45px rgba(22,50,59,.10); image-rendering:auto; }
.footer-note { color:#819194; font-size:.76rem; text-align:center; padding:2rem 0 .5rem; }

@media (max-width: 900px) {
  .hero { padding:1.6rem; min-height:0; }
  .stepper, .summary-strip, .kpi-grid { grid-template-columns:repeat(2,1fr); }
  .feature-grid { grid-template-columns:1fr; }
}
@media (max-width: 560px) {
  .stepper, .summary-strip, .kpi-grid { grid-template-columns:1fr; }
  .hero h1 { font-size:2.25rem; }
}

/* Quiet workbench surfaces complement the richer, isolated opening narrative. */
.workspace-header { display:flex; justify-content:space-between; align-items:flex-end; gap:2rem; padding:1rem 0 2rem; margin-bottom:1rem; border-bottom:1px solid #d9e3ec; }
.workspace-eyebrow { color:#637d8e; font-size:.92rem; font-weight:600; }
.workspace-header h1 { color:var(--ink); font-size:clamp(2rem,3.2vw,3.3rem); font-weight:680; line-height:1.15; letter-spacing:-.055em; margin:.8rem 0 .6rem; }
.workspace-header p { color:var(--muted); font-size:1rem; margin:0; }
.workspace-key { display:flex; gap:1.2rem; color:#617787; font-size:.85rem; padding-bottom:.25rem; white-space:nowrap; }
.workspace-key span { display:flex; align-items:center; gap:.45rem; }
.stepper { margin:1.4rem 0 2rem; gap:1rem; }
.step { border-radius:8px; background:#fff; padding:.9rem 1rem; box-shadow:none; }
.step.active { background:#fff; border-color:#df7890; color:#a13c58; box-shadow:inset 0 -2px 0 #df7890; }
.step.done { background:#f0f8f9; border-color:#b9d9df; }
.section-kicker { font-size:.8rem; color:#617787; letter-spacing:.04em; text-transform:none; margin-top:.75rem; }
.section-title { font-size:1.7rem; font-weight:680; line-height:1.25; margin:.35rem 0 .5rem; }
.section-copy { max-width:850px; line-height:1.6; }
.feature-card,.soft-card { border-radius:12px; box-shadow:none; background:#fff; padding:1.65rem; }
.feature-card h3 { font-size:1.15rem; font-weight:650; }
.feature-card p { line-height:1.65; }
.feature-icon { border-radius:8px; }
.summary-item { border-radius:8px; background:#fff; }
.summary-label,.kpi-label { font-size:.8rem; letter-spacing:.015em; text-transform:none; color:#607789; }
.summary-value,.kpi-value { font-variant-numeric:tabular-nums; font-weight:680; }
.kpi-card { border-radius:12px; box-shadow:none; border-top:3px solid var(--tint,#d3eced); padding:1.25rem; }
.kpi-card:after { display:none; }
.kpi-value { font-size:1.85rem; }
.kpi-note { font-size:.8rem; line-height:1.4; color:#617787; }
[data-baseweb="tab"] { border-radius:7px 7px 0 0; }
.stButton > button,.stDownloadButton > button { border-radius:7px; font-weight:600; transition:background .2s,border-color .2s; }
.stButton > button[kind="primary"] { background:#173f52; box-shadow:none; color:#fff; }
.stButton > button[kind="primary"]:hover { background:#21596e; color:#fff; }
.stDownloadButton > button { background:#fff; }
[data-testid="stDataFrame"],div[data-testid="stImage"] img { border-radius:10px; box-shadow:none; }
section[data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] { border-color:#76b8c2; border-radius:10px; }
section[data-testid="stSidebar"] [data-testid="stFileChip"] { background:#153646; border:1px solid #416471; }
section[data-testid="stSidebar"] [data-testid="stFileChip"] button { background:transparent !important; color:#dceef2 !important; border:0; }
.footer-note { font-size:.8rem; line-height:1.6; }
button:focus-visible,a:focus-visible { outline:3px solid #218da1; outline-offset:3px; }
@media(max-width:900px) { .block-container { padding-left:1.2rem; padding-right:1.2rem; } .workspace-header { flex-direction:column; align-items:flex-start; gap:1rem; } }
@media(max-width:560px) { .block-container { padding:3.8rem .7rem 2rem; } .feature-card { padding:1.15rem; } .section-title { font-size:1.45rem; } }
@media(prefers-reduced-motion:reduce) { *,*:before,*:after { animation:none!important; transition:none!important; scroll-behavior:auto!important; } }
</style>
"""
