APP_CSS = r"""
<style>
:root {
  --ink: #16323b;
  --muted: #60747a;
  --paper: #fbfcf9;
  --panel: rgba(255,255,255,.86);
  --line: rgba(22,50,59,.11);
  --rim: #ef4e77;
  --rim-soft: #fff0f4;
  --core: #19b6c8;
  --core-soft: #eafafb;
  --lime: #c6e86b;
  --navy: #102f3a;
}

html, body, [class*="css"] { font-family: "Aptos", "Segoe UI", Inter, sans-serif; }
.stApp {
  color: var(--ink);
  background:
    radial-gradient(circle at 92% 2%, rgba(25,182,200,.11), transparent 28rem),
    radial-gradient(circle at 6% 26%, rgba(239,78,119,.08), transparent 26rem),
    #f4f7f3;
}
[data-testid="stHeader"] { background: transparent; }
[data-testid="stToolbar"] { right: 1rem; }
.block-container { max-width: 1480px; padding-top: 1.3rem; padding-bottom: 3rem; }

section[data-testid="stSidebar"] {
  background: linear-gradient(180deg, #102f3a 0%, #143b46 58%, #17343c 100%);
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
  background: #c6e86b; color: #17343c; border: 0;
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
  background: #c6e86b !important;
  color: #17343c !important;
  border-color: #c6e86b !important;
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
  background: conic-gradient(from 210deg, var(--rim), #ffb67f, var(--lime), var(--core), var(--rim));
  color:#102f3a; font-weight:900; box-shadow: inset 0 0 0 5px rgba(255,255,255,.2);
}
.brand-name { font-size:1.03rem; font-weight:800; letter-spacing:.02em; color:#fff; }
.brand-sub { font-size:.72rem; text-transform:uppercase; letter-spacing:.14em; color:#9fc0bf; }

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
</style>
"""
