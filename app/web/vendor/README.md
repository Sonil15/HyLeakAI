# Vendored third-party code

Pinned rather than loaded from a CDN so the page is fully self-contained: it
renders with no internet access, and a CDN outage or blocked domain during a
demo cannot take the 3D view down. FastAPI serves this directory same-origin
from the Cloud Run image.

| File | Source | Version |
|---|---|---|
| `three.module.min.js` | https://unpkg.com/three@0.180.0/build/three.module.min.js | 0.180.0 |
| `three.core.min.js` | https://unpkg.com/three@0.180.0/build/three.core.min.js | 0.180.0 |
| `OrbitControls.js` | https://unpkg.com/three@0.180.0/examples/jsm/controls/OrbitControls.js | 0.180.0 |

Three.js is MIT licensed.

`three.module.min.js` imports `three.core.min.js` by relative path. Both are
required: downloading only the first yields a 404 at runtime and the 3D view
never appears, with nothing logged that points at the cause.

## Local modification

`OrbitControls.js` ships with a bare import specifier, `from 'three'`, which
only resolves via an import map. The single import was rewritten to
`from './three.module.min.js'`. Import maps are widely but not universally
supported, and an unresolved bare specifier fails the entire module graph with
no visible error — the 3D view would simply never appear. This is the only
change; re-apply it if the file is re-downloaded.
