# PRL RIM Atlas: front-end design

The opening is a three-chapter scientific story: observe, separate, measure.
A locally bundled Three.js sculpture represents the rim and lesion core. Native
page scrolling drives its rotation, layer separation and final slice alignment.
Cursor movement adds restrained parallax. No scroll interception or nested
scrolling area is used. Native chapter buttons provide a keyboard alternative.

The scene is explicitly conceptual: it is not a patient image, reconstruction,
measurement or diagnostic result. It never receives uploaded files or metrics.
The grayscale reference plane is generated procedurally from a synthetic phantom.

## Design references

Research consulted on 28 September 2026:

- [GSAP ScrollTrigger](https://gsap.com/docs/v3/Plugins/ScrollTrigger/): scroll
  scrubbing, pinned visual stages, actual scroll-container selection and cleanup.
- [GSAP's official AI skills](https://github.com/greensock/gsap-skills): scroll and
  performance guidance. The small three-scene timeline here uses native scrolling
  and requestAnimationFrame rather than adding a separate animation framework.
- [Anthropic frontend-design](https://github.com/anthropics/skills/blob/main/skills/frontend-design/SKILL.md):
  subject-specific identity, deliberate type hierarchy and a single memorable
  visual rather than repeated generic cards.
- [Vercel web interface guidelines](https://github.com/vercel-labs/web-interface-guidelines):
  semantic controls, visible focus, readable typography and reduced motion.
- [Three.js responsive rendering](https://threejs.org/manual/pages/responsive.html)
  and [rendering on demand](https://threejs.org/manual/pages/rendering-on-demand.html):
  bounded resolution and avoiding unnecessary rendering.
- [W3C animation from interactions](https://www.w3.org/WAI/WCAG22/Understanding/animation-from-interactions.html):
  alternatives to scroll-linked motion.

## Behavior and build

- Streamlit v2 component, with isolated styles and natural page height.
- Full narrative only before ROI files are available; a compact header then
  leaves the existing mapping, calibration, visual QC and exports in focus.
- Upload buttons open/focus the existing Streamlit upload panel.
- Pause and operating-system reduced-motion preference reveal a static story.
  Short viewports use the same readable static arrangement.
- No WebGL: an inline schematic remains visible. Context loss restores it too.
- The render loop stops when offscreen, hidden or paused; unmount disposes GPU
  resources and event listeners. Device pixel ratio is capped at 1.5.
- All scene code is served by the app. No CDN, external fonts, analytics or
  third-party runtime fetch is added.

Edit `ui/frontend/story.html`, `story.css`, `story.js` and `scene.js`.
Run `npm ci` and `npm run build` to regenerate `ui/static/story.js`; commit the
bundle so Streamlit Cloud needs no Node.js build step. Python analysis
dependencies and all `prl/` computation modules remain unchanged.
