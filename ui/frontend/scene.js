import * as THREE from 'three';

// An illustrative sculpture, constructed from geometry and a synthetic phantom.
// This component never receives uploaded images, segmentations, or measurements.
export function createScene(canvas, { onReady, onUnavailable } = {}) {
  let renderer;
  let disposed = false;
  const geometries = new Set();
  const materials = new Set();
  const textures = new Set();
  const noop = { update() {}, resize() {}, dispose() {} };
  const clamp = (value, low = 0, high = 1) => Math.max(low, Math.min(high, value));
  const ease = (value) => { const x = clamp(value); return x * x * (3 - 2 * x); };
  const mix = (a, b, t) => a + (b - a) * t;
  const geometry = (value) => { geometries.add(value); return value; };
  const material = (value) => { materials.add(value); return value; };

  try {
    const context = canvas.getContext('webgl2', {
      alpha: true, antialias: true, powerPreference: 'low-power',
      premultipliedAlpha: true, preserveDrawingBuffer: false,
    });
    if (!context) throw new Error('WebGL 2 is unavailable.');
    renderer = new THREE.WebGLRenderer({ canvas, context, alpha: true, antialias: true });
    renderer.setPixelRatio(Math.min(globalThis.devicePixelRatio || 1, 1.5));
    renderer.setClearColor(0x071722, 0);
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.32;
  } catch (error) {
    renderer?.dispose();
    onUnavailable?.(error);
    return noop;
  }

  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(32, 1, 0.1, 30);
  camera.position.set(0, 0, 8.9);
  scene.add(new THREE.HemisphereLight(0xcbeefa, 0x293046, 2.0));
  const key = new THREE.DirectionalLight(0xffe1d9, 4.1);
  key.position.set(-3, 4, 5);
  scene.add(key);
  const fill = new THREE.DirectionalLight(0x63daf0, 2.6);
  fill.position.set(4, -2, 3);
  scene.add(fill);
  const edge = new THREE.DirectionalLight(0xff6c86, 2.5);
  edge.position.set(-1, -3, -2);
  scene.add(edge);

  const sculpture = new THREE.Group();
  sculpture.position.set(0, 0.08, 0);
  scene.add(sculpture);
  const rim = new THREE.Group();
  const core = new THREE.Group();
  const plane = new THREE.Group();
  sculpture.add(plane, core, rim);

  // Low-frequency contour variation reads as a hand-segmented shape, not a torus.
  const boundary = (theta) => 1.36 * (
    1 + 0.047 * Math.sin(theta * 3 + 0.7)
      + 0.029 * Math.cos(theta * 5 - 0.3)
      + 0.016 * Math.sin(theta * 8 + 0.4)
  );
  const rimGeometry = geometry(new THREE.BufferGeometry());
  const around = 192;
  const cross = 24;
  const positions = [];
  const indices = [];
  for (let i = 0; i <= around; i += 1) {
    const theta = (i / around) * Math.PI * 2;
    const width = 0.15 + 0.035 * Math.sin(theta * 3 - 0.5)
      + 0.013 * Math.cos(theta * 7);
    for (let j = 0; j <= cross; j += 1) {
      const phi = (j / cross) * Math.PI * 2;
      const r = boundary(theta) + width * Math.cos(phi);
      positions.push(
        r * Math.cos(theta) * 1.08,
        r * Math.sin(theta) * 0.90,
        0.19 * Math.sin(phi) + 0.035 * Math.sin(theta * 2),
      );
      if (i < around && j < cross) {
        const a = i * (cross + 1) + j;
        const b = (i + 1) * (cross + 1) + j;
        indices.push(a, b, a + 1, b, b + 1, a + 1);
      }
    }
  }
  rimGeometry.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3));
  rimGeometry.setIndex(indices);
  rimGeometry.computeVertexNormals();
  const rimSurface = material(new THREE.MeshPhysicalMaterial({
    color: 0xf1788e, roughness: 0.30, metalness: 0.16,
    clearcoat: 0.58, clearcoatRoughness: 0.30,
    emissive: 0x721c36, emissiveIntensity: 0.10,
  }));
  rim.add(new THREE.Mesh(rimGeometry, rimSurface));

  const coreGeometry = geometry(new THREE.SphereGeometry(1, 80, 48));
  const corePositions = coreGeometry.attributes.position;
  for (let i = 0; i < corePositions.count; i += 1) {
    const x = corePositions.getX(i);
    const y = corePositions.getY(i);
    const z = corePositions.getZ(i);
    const theta = Math.atan2(y, x);
    const contour = boundary(theta) - 0.19;
    corePositions.setXYZ(i, x * contour * 1.08, y * contour * 0.90, z * 0.24);
  }
  coreGeometry.computeVertexNormals();
  const coreSurface = material(new THREE.MeshPhysicalMaterial({
    color: 0x69d8df, roughness: 0.28, metalness: 0.06,
    transparent: true, opacity: 0.70, depthWrite: false,
    clearcoat: 0.65, clearcoatRoughness: 0.25,
    emissive: 0x0d7c8e, emissiveIntensity: 0.16,
  }));
  const coreMesh = new THREE.Mesh(coreGeometry, coreSurface);
  coreMesh.renderOrder = 2;
  core.add(coreMesh);

  function contourLine(radiusOffset, z, color, opacity, target = rim) {
    const points = [];
    for (let i = 0; i < 192; i += 1) {
      const theta = (i / 192) * Math.PI * 2;
      const r = boundary(theta) + radiusOffset;
      points.push(new THREE.Vector3(
        r * Math.cos(theta) * 1.08,
        r * Math.sin(theta) * 0.90,
        z + (target === rim ? 0.035 * Math.sin(theta * 2) : 0),
      ));
    }
    const line = new THREE.LineLoop(
      geometry(new THREE.BufferGeometry().setFromPoints(points)),
      material(new THREE.LineBasicMaterial({ color, transparent: true, opacity, depthWrite: false })),
    );
    line.renderOrder = 3;
    target.add(line);
    return line;
  }
  contourLine(0.13, 0.085, 0xffc0c8, 0.46);
  contourLine(-0.15, 0.075, 0xffdae2, 0.34);
  contourLine(-0.23, 0.072, 0xb4ffff, 0.66, core);
  contourLine(-0.33, 0.12, 0x7ed8e5, 0.18, core);

  // The reference plane is a procedural grayscale phantom, not patient data.
  const size = 160;
  const pixels = new Uint8Array(size * size * 4);
  for (let y = 0; y < size; y += 1) {
    for (let x = 0; x < size; x += 1) {
      const nx = (x / (size - 1) - 0.5) * 2;
      const ny = (y / (size - 1) - 0.5) * 2;
      const ellipse = Math.sqrt((nx / 0.81) ** 2 + (ny / 0.90) ** 2);
      const outline = Math.exp(-(((ellipse - 0.83) / 0.026) ** 2));
      const matter = clamp((0.82 - ellipse) * 18);
      const ripple = Math.sin(nx * 27 + Math.sin(ny * 14) * 2.5)
        * Math.sin(ny * 22 + Math.cos(nx * 13) * 1.3);
      const midline = Math.exp(-((nx / 0.026) ** 2)) * matter;
      const value = clamp(0.045 + matter * (0.145 + ripple * 0.027)
        + outline * 0.11 - midline * 0.09);
      const offset = (y * size + x) * 4;
      pixels[offset] = Math.round(value * 240);
      pixels[offset + 1] = Math.round(value * 250);
      pixels[offset + 2] = Math.round(value * 255);
      pixels[offset + 3] = 255;
    }
  }
  const phantom = new THREE.DataTexture(pixels, size, size, THREE.RGBAFormat);
  phantom.colorSpace = THREE.SRGBColorSpace;
  phantom.minFilter = THREE.LinearFilter;
  phantom.magFilter = THREE.LinearFilter;
  phantom.needsUpdate = true;
  textures.add(phantom);
  const planeMaterial = material(new THREE.MeshBasicMaterial({
    map: phantom, transparent: true, opacity: 0.65, side: THREE.DoubleSide,
    depthWrite: false,
  }));
  plane.add(new THREE.Mesh(geometry(new THREE.PlaneGeometry(4.02, 3.82)), planeMaterial));

  const gridPoints = [];
  for (let i = -8; i <= 8; i += 1) {
    const p = i * 0.235;
    gridPoints.push(-1.88, p, 0.01, 1.88, p, 0.01);
    gridPoints.push(p, -1.88, 0.01, p, 1.88, 0.01);
  }
  const gridGeometry = geometry(new THREE.BufferGeometry());
  gridGeometry.setAttribute('position', new THREE.Float32BufferAttribute(gridPoints, 3));
  const gridMaterial = material(new THREE.LineBasicMaterial({
    color: 0x6f9ca8, transparent: true, opacity: 0.105, depthWrite: false,
  }));
  plane.add(new THREE.LineSegments(gridGeometry, gridMaterial));

  // Crop corners suggest an imaging field without asserting a physical scale.
  const corners = [];
  for (const x of [-1, 1]) {
    for (const y of [-1, 1]) {
      corners.push(x * 2.04, y * 1.72, 0.016, x * 2.04, y * 1.94, 0.016);
      corners.push(x * 2.04, y * 1.94, 0.016, x * 1.82, y * 1.94, 0.016);
    }
  }
  const cornersGeometry = geometry(new THREE.BufferGeometry());
  cornersGeometry.setAttribute('position', new THREE.Float32BufferAttribute(corners, 3));
  plane.add(new THREE.LineSegments(cornersGeometry, material(new THREE.LineBasicMaterial({
    color: 0x8db4bb, transparent: true, opacity: 0.54, depthWrite: false,
  }))));

  const samplePositions = [];
  for (let i = 0; i < 66; i += 1) {
    const theta = (i / 66) * Math.PI * 2;
    const r = boundary(theta) + 0.15;
    samplePositions.push(r * Math.cos(theta) * 1.08, r * Math.sin(theta) * 0.90,
      0.12 + 0.035 * Math.sin(theta * 2));
  }
  const samples = geometry(new THREE.BufferGeometry());
  samples.setAttribute('position', new THREE.Float32BufferAttribute(samplePositions, 3));
  const samplesMaterial = material(new THREE.PointsMaterial({
    color: 0xffd3d9, size: 0.022, transparent: true, opacity: 0.65,
    sizeAttenuation: true, depthWrite: false,
  }));
  rim.add(new THREE.Points(samples, samplesMaterial));

  let lastWidth = 0;
  let lastHeight = 0;
  const resize = (width, height) => {
    if (disposed || width <= 0 || height <= 0) return;
    const w = Math.round(width);
    const h = Math.round(height);
    if (w === lastWidth && h === lastHeight) return;
    lastWidth = w;
    lastHeight = h;
    renderer.setSize(w, h, false);
    camera.aspect = w / h;
    // Preserve the full sculpture at narrow portrait breakpoints.
    camera.position.z = camera.aspect < 1 ? 8.9 / camera.aspect : 8.9;
    camera.updateProjectionMatrix();
  };

  const update = (progress = 0, pointerX = 0, pointerY = 0, time = 0) => {
    if (disposed) return;
    const p = clamp(progress);
    const explode = Math.sin(Math.PI * ease(p));
    const settle = ease((p - 0.62) / 0.38);
    const opening = ease(p / 0.28);
    const px = clamp(pointerX, -1, 1);
    const py = clamp(pointerY, -1, 1);
    sculpture.rotation.set(
      mix(-0.70 - explode * 0.22, 0.015, settle) + py * 0.048 * (1 - settle),
      mix(-0.25, 0, settle) + px * 0.068 * (1 - settle),
      mix(-0.14, 0.035, settle),
    );
    sculpture.position.y = 0.06 + Math.sin(time * 0.35) * 0.016 * (1 - settle);
    sculpture.scale.setScalar(mix(0.97, 1.05, settle));
    rim.position.set(0, explode * 0.08, mix(0.15 + explode * 0.82, 0.027, settle));
    core.position.set(0, -explode * 0.055, mix(0.08 - explode * 0.08, 0.006, settle));
    plane.position.z = mix(-0.43 - explode * 0.46, -0.16, settle);
    rim.scale.z = mix(1, 0.11, settle);
    core.scale.z = mix(1, 0.12, settle);
    planeMaterial.opacity = mix(0.45, 0.80, settle);
    gridMaterial.opacity = mix(0.075, 0.13, opening) * (1 - settle * 0.35);
    coreSurface.opacity = mix(0.68, 0.90, settle);
    samplesMaterial.opacity = 0.38 + opening * 0.20;
    renderer.render(scene, camera);
  };

  const dispose = () => {
    if (disposed) return;
    disposed = true;
    canvas.removeEventListener('webglcontextlost', onContextLost);
    geometries.forEach((item) => item.dispose());
    materials.forEach((item) => item.dispose());
    textures.forEach((item) => item.dispose());
    scene.clear();
    renderer.dispose();
  };
  const onContextLost = (event) => {
    event.preventDefault();
    dispose();
    onUnavailable?.(new Error('The graphics context was interrupted.'));
  };
  canvas.addEventListener('webglcontextlost', onContextLost);
  try {
    resize(canvas.clientWidth || 640, canvas.clientHeight || 560);
    update();
    onReady?.();
  } catch (error) {
    dispose();
    onUnavailable?.(error);
    return noop;
  }
  return { update, resize, dispose };
}
