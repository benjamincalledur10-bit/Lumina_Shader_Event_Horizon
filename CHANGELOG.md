# Changelog

All notable changes to Lumina Event Horizon are documented in this file.

## [1.3.9] - 2026-09-19

# 🌌 Lumina Event Horizon v1.3.9 — Cinematic Focus

Bring your subject into focus. This update introduces **Cinematic Autofocus**, smoother depth-of-field effects, and compatibility improvements targeting Minecraft Java **1.8–26.3**. ✨

## 🎯 New Cinematic Autofocus

* Added automatic focus that follows what you are looking at.
* Keeps the focused subject and foreground sharp while softly blurring the background.
* Added adjustable intensity and quality controls.
* Added depth handling for Distant Horizons terrain.

## 🎬 Smoother, Cleaner Blur

* Improved **Cinematic Autofocus**, **Distance Blur**, and the previous depth-of-field mode.
* Added bilinear and trilinear filtering with smoother sampling to reduce pixelation, halos, and repeated outlines.
* Added **Cinematic quality — 64 samples**.
* Added **Ultra quality — 96 samples**.
* Adapted filtering to the rendering resolution, including **4K**.
* Improved protection against background color bleeding onto hands and nearby objects.

## 🧩 Minecraft 26.3 Compatibility

* Updated the target compatibility range to **Minecraft Java Edition 1.8–26.3**.
* Added support for Iris’s integrated enchantment glint rendering on 26.3.
* Enabled separate entity rendering when required by Iris.
* Corrected legacy identifiers for signs, skulls, banners, beds, silver shulker boxes, enchanting tables, and redstone torches.

## 💨 Motion Blur Removed

* Removed the motion blur effect and its settings.
* Removed the auxiliary bloom correction associated with motion blur.
* Checked that bloom retains its previous behavior after the removal.

## 📖 Documentation and Credits

* Updated the README, changelog, and package metadata.
* Added instructions for enabling and adjusting Cinematic Autofocus.
* Streamlined the README credits while retaining attribution to **Complementary Reimagined** and preserving the existing license.

## 🛠️ Validation and Testing

* Expanded automated checks for version metadata, settings, and compatibility requirements.
* Performed shader preprocessing checks.
* Ran isolated GPU tests of the blur filter on **Apple M4**, including **4K rendering**.
* Verified the ZIP packages published with **RC1** and **RC2**.

## 📦 Release Preparation

* Published two release candidates for testing.
* The current v1.3.9 development baseline builds on **RC2**, followed by the README credits update.

Sharper subjects, smoother backgrounds, and more control over your cinematic style. 🌠

## [1.3.9-rc.2] - 2026-09-19

### Changed

- Replaced sparse, unfiltered blur samples with explicit bilinear/trilinear
  filtering and overlapping mipmap footprints in all world-blur modes.
- Added a soft circular aperture to reduce repeated outlines and hard bokeh rings.
- Upgraded Distance Blur and legacy Depth of Field to the same cinematic filter.
- Added Cinematic (64 samples, default) and Ultra (96 samples) blur quality.
- Scaled the filtering footprint with rendering resolution, including 4K.
- Protected nearby silhouettes from mipmap leakage and clamped texture reads.

### Validation

- Passed 432 composite3 preprocessing configurations and canonical validation.
- Compiled and rendered the shared blur filter in an isolated Apple M4 OpenGL
  harness, including synthetic tests at 3840 x 2160 for constant-color preservation,
  fine-pattern smoothing, and foreground color leakage.
- Visual testing in Minecraft remains necessary to assess softness, contours,
  focus transitions, and performance on each GPU.

## [1.3.9-rc.1] - 2026-09-19

### Added

- Added optional Cinematic Autofocus with background-only circular blur,
  center focus, intensity and quality controls, and depth-aware silhouette protection.
- Added Distant Horizons depth handling to the new autofocus mode.

### Removed

- Removed motion blur rendering, controls, and its bloom-fog workaround.

### Changed

- Updated the development version and compatibility target to Minecraft Java
  Edition 1.8 through 26.3 across pack metadata and current documentation.
- Enabled separate entity draws when required by the installed Iris loader.

### Fixed

- Added Iris 26.3 inline enchantment glint for held items, dropped items, and
  armor, while retaining the legacy glint pass on older loaders.
- Restored legacy sign, skull, banner, bed, silver shulker box, enchanting table,
  and redstone torch material mappings for pre-1.13 Minecraft versions.

### Validation

- Added version and legacy/modern block-mapping regression checks.
- Full in-game verification across Minecraft 1.8 through 26.3 remains pending.

## [1.3.81] - 2026-08-17

### Fixed

- Restored the complete v1.3.2-style white radial light field around the Black
  Hole across the End sky, without the v1.3.8 outer-radius cutoff.
- Removed the incorrect orange horizontal line introduced in v1.3.81-rc.1.

## [1.3.8] - 2026-08-16

### Changed

- Reduced End sky cost by rejecting black-hole and white-hole pixels outside
  their visible radii before disk-noise sampling, while retaining full detail,
  animation, and the broad accretion glow inside the rendered effect.
- Restored the broad v1.3.2 black-hole accretion glow in The End.
- Restored the always-visible v1.3.2 White Hole light rays while preserving the
  v1.3.7 projection safety guard and Event Horizon settings.
- Renamed the canonical validation job so it no longer embeds a shader version.
- Added smoothly blended Nether fog colors and densities for Nether Wastes,
  Crimson Forest, Warped Forest, Basalt Deltas, and Soul Sand Valley.
- Added a 0-150% Nether Biome Fog Strength control without adding fog texture
  samples.
- Rebalanced lava toward natural orange local lighting with controlled surface
  emission so large lava fields do not overexpose the whole view.
- Shifted Nether Portals toward a cinematic purple-blue glow and increased
  their colored-light contribution to nearby terrain.
- Adapted Nether Storm color and opacity to the smoothly blended biome state,
  with denser gray ash in Basalt Deltas and reduced intensity in Warped Forest
  and Soul Sand Valley.
- Extended canonical validation to protect the Nether fog control, biome storm
  integration, settings exposure, and zero-texture-sample fog requirement.

### Fixed

- Moved Nether biome-density calculations out of global scope and compiled them
  only for non-macOS Nether programs to avoid an Apple OpenGL compiler crash.
- Restored complete v1.3.7-compatible `MC_OS_MAC` Nether paths for fog, storm,
  lava, portals, biome colors, and local lighting; Windows and Linux retain the
  v1.3.8 improvements.
- Restored nine-sample terrain occlusion for White Hole rays in the vertex pass.
- Restored Distant Horizons depth occlusion and viewport bounds checks for the
  White Hole ray source.
- Multiplied White Hole ray intensity by its softened source visibility so rays
  fade at terrain edges instead of passing through mountains.

## [1.3.7] - 2026-07-30

### Changed

- Added a dedicated Event Horizon Settings menu for black-hole size, accretion-disk intensity, gravitational lensing, disk rotation, the White Hole, and its energy rays.
- Centralized the Event Horizon direction, size, disk geometry, animation, and rendering constants so the sky object, End lighting, and post-processing remain aligned.
- Replaced the inherited multi-style cloud selector with one unified `Lumina Clouds` renderer and visual identity.
- Rebuilt cloud formation around multi-octave volumetric density, height-aware erosion, anvil shaping, powder scattering, and silver-lining illumination.
- Increased medium and high ray-march resolution for smoother silhouettes and denser volume definition.
- Added dedicated Lumina controls for cloud coverage, formation scale, storm density, altitude, speed, color, and shadowing.
- Removed the legacy secondary cloud layer, vanilla-cloud mode, and style-specific cloud settings.

### Fixed

- Added depth-aware White Hole ray occlusion with softened terrain-edge sampling and Distant Horizons support.
- Prevented White Hole energy rays from rendering outside the viewport or through terrain.
- Made the White Hole Rays and closed-area cloud checks discoverable as functional boolean options in Iris and OptiFine.
- Centralized End lighting on the Event Horizon direction and removed the obsolete origin-facing fallback.
- Rebuilt terrain cloud shadows from the same multi-octave density, erosion, weather, scale, and wind model used by visible Lumina Clouds.
- Projected cloud shadows toward the configured cloud layer along the active world-space light direction.
- Disabled cloud shadows automatically when cloud quality is set to Off.
- Removed an out-of-scope cloud-frequency reference that could break lighting-program compilation.
- Restored the valid shadow-map distance check used to hide volumetric clouds when the player is inside a closed area.
- Preserved the true first cloud-ray hit at close range so reflections and light shafts retain stable cloud depth.
- Prevented undefined zero-vector normalization in opaque shadow and light-shaft colors.
- Added stable End light direction handling at the exact world origin.
- Repaired invalid JSON metadata in the historical Event Horizon source copy.

## [1.3.6] - 2026-07-17

### Changed

- Renamed the canonical source directory so it matches shader version v1.3.6.
- Updated the documented compatibility range through Minecraft 26.2.

### Fixed

- Clipped cloud ray intervals before calculating capped sample spacing, avoiding
  missing or popping clouds along near-horizontal view directions.
- Guarded the White Hole flare projection against a near-zero clip-space `w`
  value and removed the unused Black Hole screen projection.

## [1.3.5] - 2026-07-13

### Added

- Added the required unchanged Complementary License Agreement 1.6 to the
  repository and downloadable shader pack.
- Added an optional White Hole light-rays effect and reorganized shader menus.
- Added missing Pale Oak sign material mappings.
- Added labels for every supported detail-quality level.

### Changed

- Updated the pack metadata and compatibility description for v1.3.5.
- Integrated the latest cloud octaves, powder effect, and scattering behavior.
- Balanced the High profile so SSAO, detail quality, and cloud quality no longer
  regress below the Medium profile.
- Limited cloud sampling workloads to reduce horizon-related performance spikes.

### Fixed

- Fixed the End light direction not matching the black hole position.
- Fixed the Einstein Ring extending across most of the End sky.
- Fixed blindness and darkness being applied twice to the black hole.
- Fixed zero-vector normalization at the center of the black and white holes.
- Fixed divisions by zero in cloud, colored-light fog, and Nether storm sampling.
- Fixed incomplete AMD cloud reflections after the sample-count safety clamp.
- Fixed duplicate smoothing-state IDs affecting biome and eye-brightness values.
- Fixed reversed `smoothstep` calls that could behave differently between GPU
  drivers.
- Fixed invalid block mappings, texture metadata, and dormant GLSL source text.
- Removed invalid empty temporary PNG files from the shader pack.

[1.3.9-rc.1]: https://github.com/benjamincalledur10-bit/Lumina_Shader_Event_Horizon/releases/tag/v1.3.9-rc.1
[1.3.6]: https://github.com/benjamincalledur10-bit/Lumina_Shader_Event_Horizon/compare/v1.3.5...v1.3.6
[1.3.5]: https://github.com/benjamincalledur10-bit/Lumina_Shader_Event_Horizon/releases/tag/v1.3.5

[1.3.9-rc.2]: https://github.com/benjamincalledur10-bit/Lumina_Shader_Event_Horizon/releases/tag/v1.3.9-rc.2

[1.3.9]: https://github.com/benjamincalledur10-bit/Lumina_Shader_Event_Horizon/releases/tag/v1.3.9
