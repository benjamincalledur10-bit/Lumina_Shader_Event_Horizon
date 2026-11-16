# Experimental Voxy integration

This is a first implementation, not a certified Voxy/Iris runtime combination.
It targets Windows/Linux with a Voxy-compatible OpenGL 4.6 GPU and Iris/Sodium.
The normal Lumina path remains available on macOS without Voxy.

## Contract and activation

The implementation targets Voxy patch schema **1** and shader macro **VOXY >= 3**.
The reviewed upstream snapshot is
[MCRcortex/voxy@5bf33350a1cc7bb7e2b5d947b236c56d878b8a7d](https://github.com/MCRcortex/voxy/tree/5bf33350a1cc7bb7e2b5d947b236c56d878b8a7d).
This is an API reference, not a claim to support every published mod version.

Each standard dimension has a guarded `voxy.json`, opaque/translucent patches
and a TAA body. Unsupported APIs, native macOS and simultaneous Distant Horizons
produce an empty descriptor. Use **one LOD mod** when testing: remove Distant Horizons from the Voxy test
instance, since a detected DH macro disables this adapter even if its renderer
is switched off.

Voxy's injected UBO supplies only the explicitly requested uniforms. The patches
read settings through `LUMINA_VOXY_PATCH`, excluding legacy uniform declarations
and dynamic globals. TAA matches Lumina's eight offsets, jitter setting and viewport.
The TAA source is reachable from the opaque/translucent include graphs so Iris
can discover it even when Voxy does not register it as an independent entry point.

## Implemented

- Opaque/cutout and translucent terrain for Overworld, Nether and End.
- Voxy's atlas/tint, face orientation and lightmap decoding; existing Lumina
  day/night/rain palettes and basic directional/block lighting.
- Water ID recognition, analytical wind normals, view-dependent transparency and
  simplified sky reflections; other translucent blocks keep their sampled alpha.
- Separate opaque/translucent depth with `vxProjInv`, converted through the
  Voxy and Iris model-view matrices into the consuming pass's view space, reused by Lumina's existing
  LOD fog/cloud/reflection paths. LODs are not blitted into vanilla depth.
- No extra screen-sized depth textures. The internal DH-style names alias Voxy's
  actual depth samplers only when Voxy is the active LOD provider. Render distance
  converts Voxy's chunks to the block units expected by those paths.
- Finite color/alpha checks and initialized normal/material/transmission outputs.

The original sampler names `vxDepthTexOpaque` and `vxDepthTexTrans` are preserved
for [Iris's depth transformer](https://github.com/IrisShaders/Iris/blob/26.3/common/src/main/java/net/irisshaders/iris/pipeline/transform/transformer/DepthTransformer.java).
Iris recognizes them and converts reads on reverse-depth renderers. Do not add a
second manual `1-depth` conversion to those reads. Voxy similarly transforms
`gl_FragCoord` inside injected patch code and supplies matching conventional
projection uniforms.

## Limits and unverified behavior

Distant materials use simplified lighting, not the complete nearby IPBR/POM,
normal-map, colored-voxel-light or material-specific effect pipeline. Near terrain
keeps that pipeline. Distant water has sky-only reflections, not terrain SSR,
volumetric reflected clouds or complete near-water absorption parity. LODs do not
cast new shadow-map geometry, and the initial adapter does not sample cast shadows.
There is no distant-grass waving or new entity/particle renderer.

Actual Voxy/Iris loading, uniform binding, alpha sorting, near/LOD seams, moving
camera behavior, fog/cloud intersections, depth conversion on real drivers and
FPS have **not been tested in Minecraft**. Native macOS GPU checks execute isolated
shader math with a GLSL-150 equivalent interface; they do not run Voxy or establish
Windows/Linux compatibility. Those platforms still need the runtime checklist.

## Checks

With a C preprocessor and `glslangValidator` available:

```sh
python3 scripts/check_voxy.py
python3 scripts/check_rain_solar_preprocess.py
python3 scripts/validate_canonical.py --base-ref HEAD^
```

On native macOS, `python3 scripts/check_voxy.py --gpu` additionally exercises the
isolated patch calculations, not the OpenGL-4.6 Voxy renderer.

## Validation recorded on 2026-11-16

- 36 injected-program/TAA GLSL compilations and 66 Voxy-enabled Lumina consumer
  compilations, including custom-image paths.
- 390 existing rain/solar GLSL variants and 624 water preprocessing variants.
- 72 non-Voxy preprocessed variants have identical tokens to the previous commit:
  three dimensions, Potato/High, native-Mac/other paths and DH enabled/disabled.
- Isolated native GPU calculations passed for opaque/glass/water/emissive IDs,
  six faces, four solar phases and dry/rain cases; the actual projection aliases
  also round-trip with different Iris and Voxy camera matrices.
- Existing water, shoreline, rain/puddle and Apple linker regressions passed.
- Canonical inventory: 389 shaders, 738 includes and 412 package files.

These results do not replace the runtime checklist below.

## Runtime acceptance checklist (Windows/Linux)

1. Use a matching Minecraft/Fabric/Sodium/Iris/Voxy combination, no other LOD
   renderer, and an empty shader-options file for the development ZIP.
2. Start without Voxy, then enable Voxy and verify reload/dimension changes.
   Check logs for missing uniforms, malformed patch data and shader errors.
3. Test Overworld/Nether/End in Potato/Medium/High/Ultra, day/night and rain.
4. Walk across near/LOD boundaries, rotate the camera, and check fog and clouds
   against mountains at several render distances. Verify TAA on/off while moving.
5. Test water/glass behind and in front of opaque terrain, overlapping water,
   underwater views and near-water reflections of LOD mountains.
6. Compare frame times and VRAM with Voxy off/on at fixed resolution/settings.
   Repeat on at least one NVIDIA and one AMD/Intel driver before promoting support.
