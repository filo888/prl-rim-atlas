import { createScene } from './scene.js';

// This component receives no uploaded files, metrics, or patient metadata.
export default function ({ parentElement }) {
  const root = parentElement.querySelector('.atlas-story');
  if (!root) return;
  const stage = root.querySelector('.story-stage');
  const canvas = root.querySelector('canvas');
  const sceneWrap = root.querySelector('.scene-wrap');
  const chapters = [...root.querySelectorAll('[data-chapter]')];
  const chapterButtons = [...root.querySelectorAll('[data-go]')];
  const toggle = root.querySelector('.motion-toggle');
  const progressBar = root.querySelector('.story-progress span');
  const rimLabel = root.querySelector('.label-rim');
  const coreLabel = root.querySelector('.label-core');
  const scale = root.querySelector('.scene-scale');
  const host = parentElement.host || parentElement;
  const scroller = host.closest('[data-testid="stMain"]') || document.scrollingElement;
  const scrollTarget = scroller === document.scrollingElement ? window : scroller;
  const media = window.matchMedia('(prefers-reduced-motion: reduce)');
  const shortViewport = window.matchMedia('(max-height: 650px), (max-width: 760px) and (max-height: 740px)');
  const controller = new AbortController();
  const events = { signal: controller.signal };
  let userPaused = media.matches;
  let paused = userPaused || shortViewport.matches;
  let disposed = false;
  let inView = true;
  let frame = 0;
  let progress = 0;
  let targetProgress = 0;
  let pointer = { x: 0, y: 0 };
  let smoothedPointer = { x: 0, y: 0 };
  let lastRender = 0;
  let needsLayout = true;
  let scrollStart = 0;
  let scrollTravel = 1;
  let stageBounds;
  let scene;
  root.classList.add('enhanced');

  function layout() {
    const bounds = root.getBoundingClientRect();
    const scrollBounds = scroller === document.scrollingElement ? { top: 0 } : scroller.getBoundingClientRect();
    const top = parseFloat(getComputedStyle(stage).top) || 0;
    stageBounds = stage.getBoundingClientRect();
    scrollStart = bounds.top - scrollBounds.top + scroller.scrollTop - top;
    scrollTravel = Math.max(1, root.offsetHeight - stage.offsetHeight);
    scene?.resize(sceneWrap.clientWidth, sceneWrap.clientHeight);
    needsLayout = false;
  }

  function setChapterState() {
    const position = progress * 2;
    const active = Math.round(position);
    chapters.forEach((chapter, i) => {
      const distance = Math.abs(position - i);
      const opacity = Math.max(0, Math.min(1, (0.62 - distance) / 0.25));
      chapter.style.opacity = paused ? '1' : opacity.toFixed(3);
      chapter.style.visibility = paused || opacity > 0.005 ? 'visible' : 'hidden';
      chapter.style.transform = paused ? 'none' : `translate3d(0,${(i - position) * 28}px,0)`;
      chapter.inert = !paused && i !== active;
      chapter.setAttribute('aria-hidden', String(!paused && i !== active));
    });
    chapterButtons.forEach((button, i) => {
      if (i === active) button.setAttribute('aria-current', 'step');
      else button.removeAttribute('aria-current');
    });
    const reveal = Math.min(1, Math.max(0, (progress - .18) * 5));
    rimLabel.style.opacity = paused ? '1' : String(reveal);
    coreLabel.style.opacity = paused ? '1' : String(reveal);
    rimLabel.style.transform = coreLabel.style.transform = `translateY(${(1 - reveal) * 8}px)`;
    scale.style.opacity = String(Math.max(0, (progress - .72) / .28));
    progressBar.style.transform = `scaleX(${progress})`;
    root.dataset.chapter = String(active);
    root.dataset.progress = progress.toFixed(3);
  }

  function render(time = 0) {
    frame = 0;
    if (disposed || !inView || document.hidden) return;
    if (needsLayout) layout();
    targetProgress = Math.max(0, Math.min(1, (scroller.scrollTop - scrollStart) / scrollTravel));
    if (!paused) {
      progress += (targetProgress - progress) * .13;
      if (Math.abs(targetProgress - progress) < .0005) progress = targetProgress;
      smoothedPointer.x += (pointer.x - smoothedPointer.x) * .06;
      smoothedPointer.y += (pointer.y - smoothedPointer.y) * .06;
    }
    if (time - lastRender > 30 || paused || !lastRender) {
      scene?.update(paused ? .42 : progress, paused ? 0 : smoothedPointer.x, paused ? 0 : smoothedPointer.y, paused ? 0 : time / 1000);
      setChapterState();
      lastRender = time;
    }
    if (!paused) frame = requestAnimationFrame(render);
  }

  function requestRender() {
    if (!frame && !disposed && inView && !document.hidden) frame = requestAnimationFrame(render);
  }

  function setPaused(value, preservePosition = false) {
    const previousTop = stage.getBoundingClientRect().top;
    userPaused = value;
    paused = userPaused || shortViewport.matches;
    root.classList.toggle('static-mode', paused);
    root.classList.toggle('short-screen', shortViewport.matches);
    toggle.textContent = paused ? 'Enable motion' : 'Pause motion';
    toggle.setAttribute('aria-pressed', String(paused));
    toggle.title = paused ? 'Enable the animated scroll story' : 'Show the story without animation';
    if (preservePosition) scroller.scrollTop += stage.getBoundingClientRect().top - previousTop;
    needsLayout = true;
    lastRender = 0;
    requestRender();
  }

  function goTo(index) {
    if (paused) {
      chapters[index].scrollIntoView({ behavior: 'auto', block: 'center' });
      return;
    }
    layout();
    scroller.scrollTo({ top: scrollStart + scrollTravel * index / 2, behavior: 'smooth' });
  }

  function openUploads() {
    const sidebar = document.querySelector('[data-testid="stSidebar"]');
    const expand = document.querySelector('[data-testid="stExpandSidebarButton"]');
    if (sidebar?.getAttribute('aria-expanded') === 'false') expand?.click();
    const reveal = () => {
      if (disposed) return;
      const upload = sidebar?.querySelector('[data-testid="stFileUploaderDropzone"] button');
      upload?.focus({ preventScroll: true });
      sidebar?.querySelector('[data-testid="stSidebarContent"]')?.scrollTo({ top: 0, behavior: 'auto' });
    };
    // React's native sidebar transition completes before focusing its upload button.
    window.setTimeout(reveal, 350);
  }

  root.querySelectorAll('[data-upload]').forEach(button => button.addEventListener('click', openUploads, events));
  root.querySelector('[data-next]').addEventListener('click', () => goTo(1), events);
  root.querySelector('.story-brand').addEventListener('click', event => { event.preventDefault(); goTo(0); }, events);
  chapterButtons.forEach(button => button.addEventListener('click', () => goTo(Number(button.dataset.go)), events));
  toggle.addEventListener('click', () => setPaused(!paused, true), events);
  media.addEventListener('change', event => setPaused(event.matches, true), events);
  shortViewport.addEventListener('change', () => setPaused(userPaused, true), events);
  stage.addEventListener('pointermove', event => {
    if (paused || event.pointerType === 'touch') return;
    const rect = stageBounds || stage.getBoundingClientRect();
    pointer.x = Math.max(-1, Math.min(1, (event.clientX - rect.left) / rect.width * 2 - 1));
    pointer.y = Math.max(-1, Math.min(1, (event.clientY - rect.top) / rect.height * 2 - 1));
    sceneWrap.style.setProperty('--pointer-x', `${pointer.x * 16}px`);
    sceneWrap.style.setProperty('--pointer-y', `${pointer.y * 12}px`);
    requestRender();
  }, { ...events, passive: true });
  stage.addEventListener('pointerleave', () => { pointer = { x: 0, y: 0 }; requestRender(); }, events);
  scrollTarget.addEventListener('scroll', requestRender, { ...events, passive: true });
  document.addEventListener('visibilitychange', () => {
    if (document.hidden) { cancelAnimationFrame(frame); frame = 0; }
    else { needsLayout = true; requestRender(); }
  }, events);

  scene = createScene(canvas, {
    onReady: () => root.classList.add('webgl-ready'),
    onUnavailable: () => {
      root.classList.remove('webgl-ready');
      root.classList.add('webgl-unavailable');
      canvas.hidden = true;
    },
  });
  const resize = new ResizeObserver(() => { needsLayout = true; requestRender(); });
  resize.observe(root);
  resize.observe(sceneWrap);
  const visibility = new IntersectionObserver(entries => {
    inView = entries[0].isIntersecting;
    if (!inView) { cancelAnimationFrame(frame); frame = 0; }
    else { needsLayout = true; requestRender(); }
  }, { root: scroller === document.scrollingElement ? null : scroller, rootMargin: '100px' });
  visibility.observe(root);
  setPaused(userPaused);

  return () => {
    disposed = true;
    controller.abort();
    resize.disconnect();
    visibility.disconnect();
    cancelAnimationFrame(frame);
    scene?.dispose();
  };
}
