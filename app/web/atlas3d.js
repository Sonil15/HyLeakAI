/* Stage 1 — 3D Storage Atlas.
 *
 * Loaded as a module because Three.js ships ESM only. The rest of the page is a
 * classic inline script, so the two talk through window.HyLeakAtlas, which the
 * inline script defines before this runs (module scripts are deferred, classic
 * inline ones are not).
 *
 * If anything here fails — no WebGL, a missing vendor file, a shader that will
 * not compile — it calls bridge.fallbackTo2D() and the existing Canvas scatter
 * takes over. Failing silently would leave an empty box where the atlas should
 * be, which is the one outcome worth engineering against.
 */

import * as THREE from "./vendor/three.module.min.js";
import { OrbitControls } from "./vendor/OrbitControls.js";

const bridge = window.HyLeakAtlas;
if (!bridge) throw new Error("HyLeakAtlas bridge missing");

/* Tells the page the module is executing. Without this the page cannot
   distinguish "still downloading 720 KB of Three.js" from "failed", and a
   time-based guess gets that wrong on a slow connection. */
bridge.moduleStarted();

const HOST = document.getElementById("atlas3d");
const SITES = bridge.SITES;
const N = SITES.length;

/* Column indices, mirroring the comment on the SITES array. */
const CAP = 1, SEAL = 2, HET = 3, MARGIN = 8;

/* Cube half-extent. Points live in [-S, S] on each axis. */
const S = 1.0;

function fail(reason) {
  if (window.console && console.warn) console.warn("3D atlas unavailable:", reason);
  bridge.fallbackTo2D(reason);
}

/* WebGL has to be probed, not assumed: a context can be refused for reasons
   that have nothing to do with browser version (blocklisted driver, too many
   live contexts, GPU process crash). */
function webglAvailable() {
  try {
    const c = document.createElement("canvas");
    return !!(window.WebGLRenderingContext &&
              (c.getContext("webgl2") || c.getContext("webgl")));
  } catch (_) { return false; }
}

/* The whole of init() is guarded, not just renderer construction: a shader
   that will not compile, a missing Three.js export after a version bump, or a
   null element all throw *after* the renderer exists. Uncaught, the module
   dies silently and the atlas is simply blank. */
if (!webglAvailable()) fail("no WebGL context");
else {
  try { init(); }
  catch (err) { fail((err && err.message) || String(err)); }
}

function init() {
  let renderer;
  try {
    renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
  } catch (err) { fail(err.message); return; }

  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(42, 1, 0.1, 100);
  camera.position.set(2.9, 1.9, 3.1);

  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  HOST.appendChild(renderer.domElement);

  const controls = new OrbitControls(camera, renderer.domElement);
  controls.enableDamping = true;
  controls.dampingFactor = 0.08;
  controls.rotateSpeed = 0.65;
  controls.minDistance = 2.0;
  controls.maxDistance = 9.0;
  controls.target.set(0, 0, 0);

  const HOME = { pos: camera.position.clone(), target: controls.target.clone() };

  /* ---------------------------------------------------------------- *
   * Geometry
   * ---------------------------------------------------------------- */
  const positions = new Float32Array(N * 3);
  const colors = new Float32Array(N * 3);
  const sizes = new Float32Array(N);
  const live = new Float32Array(N);
  const sel = new Float32Array(N);

  for (let i = 0; i < N; i++) {
    const s = SITES[i];
    // Criteria are already min-max normalised to [0,1] across the 1,000
    // realisations, so the seal axis is scaled to the observed 0.431-0.792
    // margin range rather than to the assumed 1.0 exceedance point. The raw
    // values are on the axis labels so the physical meaning is not lost.
    positions[i * 3]     = (s[CAP]  - 0.5) * 2 * S;
    positions[i * 3 + 1] = (s[SEAL] - 0.5) * 2 * S;
    positions[i * 3 + 2] = (s[HET]  - 0.5) * 2 * S;
    live[i] = bridge.isLive(s[0]) ? 1 : 0;
    sizes[i] = 1;
    sel[i] = 0;
  }

  const geom = new THREE.BufferGeometry();
  geom.setAttribute("position", new THREE.BufferAttribute(positions, 3));
  geom.setAttribute("color", new THREE.BufferAttribute(colors, 3));
  geom.setAttribute("aSize", new THREE.BufferAttribute(sizes, 1));
  geom.setAttribute("aLive", new THREE.BufferAttribute(live, 1));
  geom.setAttribute("aSel", new THREE.BufferAttribute(sel, 1));

  /* A custom shader rather than PointsMaterial: the ring for "live prediction
     available" and the halo for "selected" are non-colour cues, so state does
     not depend on hue alone. */
  const material = new THREE.ShaderMaterial({
    transparent: true,
    depthWrite: false,
    uniforms: {
      uScale: { value: 1 },
      uRing: { value: new THREE.Color(0x10836a) },
      uSelRing: { value: new THREE.Color(0x131c20) }
    },
    vertexShader: `
      attribute float aSize;
      attribute float aLive;
      attribute float aSel;
      varying vec3 vColor;
      varying float vLive;
      varying float vSel;
      uniform float uScale;
      void main() {
        vColor = color; vLive = aLive; vSel = aSel;
        vec4 mv = modelViewMatrix * vec4(position, 1.0);
        float base = 7.0 * aSize + aSel * 9.0;
        gl_PointSize = base * uScale / max(-mv.z, 0.001) * 2.2;
        gl_Position = projectionMatrix * mv;
      }`,
    fragmentShader: `
      varying vec3 vColor;
      varying float vLive;
      varying float vSel;
      uniform vec3 uRing;
      uniform vec3 uSelRing;
      void main() {
        vec2 d = gl_PointCoord - vec2(0.5);
        float r = length(d);
        if (r > 0.5) discard;
        vec3 c = vColor;
        float a = 0.86;
        if (vSel > 0.5 && r > 0.30) { c = uSelRing; a = 1.0; }
        else if (vLive > 0.5 && r > 0.355 && vSel < 0.5) { c = uRing; a = 1.0; }
        gl_FragColor = vec4(c, a);
      }`
  });
  material.vertexColors = true;

  const cloud = new THREE.Points(geom, material);
  scene.add(cloud);

  /* ---------------------------------------------------------------- *
   * Axes, floor grid and labels — without these the third dimension
   * reads as decoration rather than data.
   * ---------------------------------------------------------------- */
  const ink = getComputedStyle(document.documentElement)
    .getPropertyValue("--text-faint").trim() || "#7C9099";

  const box = new THREE.LineSegments(
    new THREE.EdgesGeometry(new THREE.BoxGeometry(2 * S, 2 * S, 2 * S)),
    new THREE.LineBasicMaterial({ color: new THREE.Color(ink), transparent: true, opacity: 0.28 })
  );
  scene.add(box);

  const grid = new THREE.GridHelper(2 * S, 8, new THREE.Color(ink), new THREE.Color(ink));
  grid.position.y = -S;
  grid.material.transparent = true;
  grid.material.opacity = 0.16;
  scene.add(grid);

  function labelSprite(text, muted) {
    const pad = 8, font = "600 34px ui-monospace, Menlo, Consolas, monospace";
    const m = document.createElement("canvas").getContext("2d");
    m.font = font;
    const w = Math.ceil(m.measureText(text).width) + pad * 2;
    const h = 48;
    const cv = document.createElement("canvas");
    cv.width = w; cv.height = h;
    const ctx = cv.getContext("2d");
    ctx.font = font;
    ctx.fillStyle = muted ? "#7C9099" : "#4E626A";
    ctx.textBaseline = "middle";
    ctx.fillText(text, pad, h / 2);
    const tex = new THREE.CanvasTexture(cv);
    tex.minFilter = THREE.LinearFilter;
    const sp = new THREE.Sprite(new THREE.SpriteMaterial({ map: tex, transparent: true, depthTest: false }));
    sp.scale.set((w / h) * 0.20, 0.20, 1);
    return sp;
  }

  function addLabel(text, x, y, z, muted) {
    const sp = labelSprite(text, muted);
    sp.position.set(x, y, z);
    scene.add(sp);
    return sp;
  }

  /* Real 3D arrows, not "→" inside the label text.
   *
   * Labels are sprites, and a sprite always faces the camera. So a typed arrow
   * points screen-right no matter which way the axis actually runs: orbit
   * 180 degrees and every arrow still says "right", now pointing at the low end
   * of the axis. It silently lies about direction, which is the one thing the
   * arrows exist to convey. ArrowHelper is scene geometry, so it rotates with
   * the data and stays truthful from every angle. */
  const AX = [
    { dir: new THREE.Vector3(1, 0, 0), color: 0x10836a },  // capacity, right is better
    { dir: new THREE.Vector3(0, 1, 0), color: 0xc4471b },  // seal risk, up is worse
    { dir: new THREE.Vector3(0, 0, 1), color: 0xa5720a }   // heterogeneity, back is worse
  ];
  const origin = new THREE.Vector3(-S, -S, -S);
  AX.forEach(function (a) {
    const arrow = new THREE.ArrowHelper(a.dir, origin, 2 * S + 0.22, a.color, 0.20, 0.11);
    arrow.line.material.transparent = true;
    arrow.line.material.opacity = 0.75;
    scene.add(arrow);
  });

  addLabel("capacity", 0, -S - 0.26, S + 0.06, false);
  addLabel("seal risk", -S - 0.34, 0, S, false);
  addLabel("heterogeneity", S + 0.12, -S - 0.26, 0, false);
  // The raw caprock-margin range (0.43-0.79) used to be drawn at the ends of
  // the seal axis. Two bare decimals floating next to an axis read as a pair
  // of unexplained numbers rather than as a range, so the range now lives in
  // the assumptions panel where it can be stated in words. The tooltip still
  // gives each point its own raw margin.

  /* ---------------------------------------------------------------- *
   * Picking
   * ---------------------------------------------------------------- */
  const raycaster = new THREE.Raycaster();
  raycaster.params.Points.threshold = 0.035;
  const pointer = new THREE.Vector2();
  let hovered = -1;

  function pick(event) {
    const r = renderer.domElement.getBoundingClientRect();
    pointer.x = ((event.clientX - r.left) / r.width) * 2 - 1;
    pointer.y = -((event.clientY - r.top) / r.height) * 2 + 1;
    raycaster.setFromCamera(pointer, camera);
    const hits = raycaster.intersectObject(cloud);
    if (!hits.length) return -1;
    // Nearest to the camera wins, so a point behind another is not picked
    // through it.
    let best = hits[0];
    for (let i = 1; i < hits.length; i++) if (hits[i].distance < best.distance) best = hits[i];
    return best.index;
  }

  renderer.domElement.addEventListener("pointermove", function (e) {
    const i = pick(e);
    if (i === hovered) { if (i >= 0) bridge.moveTip(e.clientX, e.clientY); return; }
    hovered = i;
    if (i < 0) bridge.hideTip();
    else bridge.showTip(i, e.clientX, e.clientY);
    bridge.highlightRow(i);
  });
  renderer.domElement.addEventListener("pointerleave", function () {
    hovered = -1; bridge.hideTip(); bridge.highlightRow(-1);
  });
  renderer.domElement.addEventListener("click", function (e) {
    const i = pick(e);
    if (i >= 0) bridge.select(i);
  });

  /* ---------------------------------------------------------------- *
   * Sync with the rest of the page
   * ---------------------------------------------------------------- */
  function applyColors() {
    const scores = bridge.scores();
    const chosen = bridge.selectedIndex();
    for (let i = 0; i < N; i++) {
      const c = bridge.viridis(scores[i] / 100);
      colors[i * 3] = c[0] / 255;
      colors[i * 3 + 1] = c[1] / 255;
      colors[i * 3 + 2] = c[2] / 255;
      sel[i] = i === chosen ? 1 : 0;
    }
    geom.attributes.color.needsUpdate = true;
    geom.attributes.aSel.needsUpdate = true;
  }

  function resize() {
    const w = HOST.clientWidth || 900;
    const h = HOST.clientHeight || 440;
    renderer.setSize(w, h, false);
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
    material.uniforms.uScale.value = h / 440;
  }

  function resetView() {
    camera.position.copy(HOME.pos);
    controls.target.copy(HOME.target);
    controls.update();
  }

  bridge.update3d = applyColors;
  bridge.resize3d = resize;
  bridge.resetView = resetView;

  window.addEventListener("resize", resize);
  // Keyboard route to the reset, so the view is recoverable without a mouse.
  HOST.addEventListener("keydown", function (e) {
    if (e.key === "r" || e.key === "R" || e.key === "Home") { resetView(); e.preventDefault(); }
  });

  applyColors();
  resize();

  (function loop() {
    requestAnimationFrame(loop);
    controls.update();
    renderer.render(scene, camera);
  })();

  bridge.ready3d();
}
