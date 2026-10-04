# Changelog

All notable changes to Lumina Event Horizon are documented in this file.

## [1.4.0-beta.4] - 2026-10-04

- Rebuilt Overworld clouds with a shared three-dimensional density field, rounded height profiles, regional coverage, and finer edge erosion at Medium/High. All qualities use the same layer geometry and wind; water reflections use the same base shape with a smaller sampling budget.
- Replaced additive opacity with distance-aware Beer–Lambert absorption and front-to-back transmittance. Corrected ray sample positions and terrain clipping, including horizontal rays and cameras inside/above the cloud layer. Lighting probes now estimate internal sunlight attenuation, with forward scattering, ambient shading and a bounded multiple-scattering approximation.
- Ground cloud shadows now sample the shared density field at the actual configured/offset layer altitude; they fade at grazing light angles and disappear above the cloud layer. Repeated sky reflection calls no longer compound cloud color multipliers.
- Main-ray budgets are 32/48/64 samples for Low/Medium/High; reflections use up to 16 and the AMD compatibility cap remains active. These are work limits, not measured performance claims.
- Added portable cloud integration preprocessing and native macOS GPU tests for density bounds, coverage/rain behavior, ray clipping, quality opacity consistency, shadows, and a synthetic sky render. Canonical validation (400 package files), 768 water and 150 cloud preprocessing configurations, and isolated native Apple M4 GPU checks passed. Minecraft appearance, motion, actual frame times and final artistic polish remain for in-game testing.


- Added a distinct High water-reflection option (value 3) and selected it in the High, Very High and Ultra profiles. Existing lower reflection modes retain their algorithms and the standalone default remains Medium.
- High Overworld water traces front-to-back scene-depth crossings with up to 48 adaptive steps and seven bisection refinements, using the actual wave normal. Invalid/discontinuous intersections fall back to the sky; this path does not substitute mirrored terrain for missing geometry.
- Added explicitly clamped bilinear scene filtering with sqrt-encoded texels decoded before interpolation, smooth hit-confidence border fading, and detailed sky effects at normal detail. High DH water uses opaque DH depth; regular High water can reconstruct DH hits when regular depth is empty, using the matching DH projection.
- Expanded preprocessing to 768 configurations and native macOS GPU tests to include High hits/fallbacks, dither independence, edge fading, linear HDR filtering, texture borders, and DH reconstruction with different near/far planes. These isolated checks passed on Apple M4. Full in-game visual, temporal and frame-time testing remains pending; High increases GPU work and cannot recover off-screen scene geometry.

## [1.4.0-beta.3] - 2026-10-04

- Upgraded Overworld water coloration with a restrained cool tint, reduced saturation, clearer shallows, and stronger wavelength-dependent absorption at depth. Potato now uses bottom depth for absorption, transparency, and wave scaling; biome and custom-color controls remain active. Depth does not explicitly classify river/ocean biomes.
- Added crossing broad swells and independently advected medium/fine waves. Rain increases surface activity; derivative filtering reduces unresolved fine ripples. Wave normals are bounded at extreme slider values, normalized before Fresnel evaluation, and respect water speed/size controls. Existing vertex displacement is unchanged.
- Balanced work by quality: Potato replaces one normal texture fetch with analytical swells while adding one bottom-depth fetch; material quality 2 uses one parallax iteration instead of two. Water SSR uses 12 march iterations at normal detail and 16 at high detail, with three refinements. These are work budgets, not measured FPS claims.
- Improved Sky only and Potato water reflections with the full atmospheric sky gradient and consistent wave direction. Sky only still performs no terrain reflection lookup. Water SSR requires a refined terrain hit, rejects invalid/off-screen projections, preserves confidence independently of scene alpha, and fades at screen borders. Removed water-only edge jitter from both reflection methods.
- Corrected DH mirrored reflection depth reconstruction to use the DH depth texture with its matching projection. Added a glossy DH water material response, protected near-zero mirrored projection divisors, zero biome-tint normalization, and underwater alpha divisors.
- Added `scripts/check_water_preprocess.py` and `scripts/check_water_beta3_gpu.py`. Canonical validation and 624 preprocessing configurations passed. Isolated native Apple M4 checks cover full materials in all three dimensions, styles and quality levels; above/below-water branches; bounded normals; monotone opacity/attenuation; animated and speed-zero waves; and synthetic terrain-hit/sky/off-screen/zero-W reflection cases.
- This beta also includes the rendering polish below. Minecraft integration, actual shoreline/DH seams, temporal behavior in motion, artistic balance, and frame-time impact remain pending visual testing.

- Guarded zero and near-zero water-foam thresholds to prevent undefined divisions while preserving the existing shoreline response for ordinary inputs.
- Preserved the Distant Horizons underwater material's full-reflection override when world-space reflections are active. Other DH paths continue to derive their reflection response from the updated wave normal, including the Overworld Schlick curve.
- Moved selective bloom extraction to full resolution in composite3, before mipmap generation. Reuses colortex8's HDR storage after SSR consumption in composite1, retaining small bright-source energy without altering the sharp scene output. The selective path adds an HDR output write and mipmap generation; disabling selective bloom retains the previous bloom path.
- Added reproducible native macOS GPU regression checks in `scripts/check_render_polish_gpu.py`. Isolated Apple M4 checks passed for degenerate foam, DH underwater/non-water/quality/reflection branches, hue preservation, actual mipmap energy retention, and selective/legacy bloom tile compilation. Preprocessing passed 96 dimension/blur/bloom configurations. Canonical validation passed; Minecraft loader integration, visual balance, and frame-time impact remain pending.

## [1.4.0-beta.2] - 2026-10-03

- Integrated Overworld water with depth: shallower optical paths retain more bed visibility, while thicker columns increase opacity and progressively attenuate the surface tint with wavelength-dependent coefficients. Applied a small desaturation to the base water tint while retaining biome colors and user color controls.
- Reused the existing bottom-depth sample before normal generation to estimate vertical depth independently from viewing angle. Reduced waves/parallax in shallow water, softened small ripples, and added a modest rain response without adding texture fetches or normal samples.
- Changed above-water Overworld reflection blending to Schlick's 2% normal-incidence response with strong grazing reflections, consistently in the regular and Distant Horizons paths. Guarded near-zero parallax divisors and made the DH reflection variable available before the underwater material branch.
- Depth drives the shallow/river/deep-water distinction; this pass does not classify river/ocean biomes explicitly. Low material-quality profiles retain their existing depth-free fallback, and underwater fog retains its existing implementation. Static validation and isolated native GPU checks passed on Apple M4 for 18 style/quality/render-path combinations, plus legacy/TAA/custom-color/End branches. GPU readback verified monotone bounded attenuation and opacity, reflection endpoints, and camera-angle-invariant wave depth. Full in-game shoreline, river, ocean, and underwater checks remain pending.

- Smoothed Overworld dawn/dusk sky and sunlight blends consistently across terrain, water, entities, atmospheric passes, and Distant Horizons. Eased the near-horizon noon color ramp without changing its daytime peak or nighttime endpoint.
- Replaced abrupt solar/lunar sky-glare and volumetric-light response switches with continuous twilight blends, including safe normalization for dim light. Extended the existing shared rain smoothing with rise/fall parameters of 6/8 so lighting, cloud density/color, and atmospheric fog settle together.
- Softened strong cloud forward-scattering boosts and added a hue-preserving HDR highlight shoulder to help retain interior shading under intense light. Cloud density, sample counts, and texture fetches are unchanged.
- The shared tone map/exposure settings and the approved Nether/End palettes are unchanged. Static validation and isolated native GPU checks passed on Apple M4: transition continuity, bounded monotone blends, dim-light safety, and hue-preserving cloud highlights. Volumetric cloud functions compiled/linked at all three quality levels; The author visually tested and accepted the atmosphere changes on macOS; broader in-game/profile/version coverage remains pending.

- Refined the End palette with slightly cooler blue-violet terrain lighting and a subtle violet tint in its dark sky/far-fog color. Precomputed constants preserve the previous luminance and keep shared tone mapping unchanged.
- Black Hole/White Hole rendering, star layers, bloom settings, and other dimensions are unchanged by this pass. Static and numerical validation and isolated native OpenGL palette compilation/linking passed on Apple M4; The author visually tested and accepted the End palette on macOS; broader hardware/version coverage remains pending.

- Refined Nether ambient and atmospheric colors with a subtle luminance-preserving red/amber tint, strongest in Nether Wastes and Crimson Forest. Warped Forest, Soul Sand Valley, and Basalt Deltas receive only a small tint to retain their individual palettes; biome transitions use the existing smooth weights.
- Applied the palette to macOS and other platforms in biome and classic color modes; vanilla fog-color mode retains its original colors. Lava emission, block lighting, fog density, bloom, and shared tone mapping remain unchanged.
- Replaced the initial Nether palette's chained dynamic global initializers with precomputed per-biome constants after a macOS native OpenGL linker crash when loading the development pack. Static/numerical checks and isolated native OpenGL compilation/linking of the corrected palette passed for all three macOS color modes on Apple M4. Subsequent author screenshots show the Nether loading after the fix; extended stability and biome-transition checks remain pending.

- Refined the Overworld daytime palette with slightly warmer direct sunlight and subtly cooler ambient skylight. Luminance-preserving tints keep the existing lighting brightness and shared tone mapping; extra solar warmth fades toward sunset.
- The palette blends through the existing daylight and weather transitions, leaving nighttime and full-rain lighting unchanged. No texture samples or new settings were added; Nether and End lighting are unchanged.
- Static and numerical palette checks performed; in-game verification of daytime materials, sunrise/sunset, and weather transitions remains pending.

## [1.4.0-beta.1] - 2026-10-03

- Added **Selective Bloom**, enabled by default, and **Bloom Highlight Threshold** in Cinematics. A soft peak-channel HDR threshold favors bright sources while retaining saturated colors; additive composition preserves the sharp base image.
- Weighted bloom toward compact halos and reduced humidity bloom amplification in selective mode. Disabling Selective Bloom restores the previous extraction, blend, and humidity calculations.
- Selection uses brightness rather than material IDs. Extraction runs on existing mip-filtered samples, so tiny lights can lose broad halos; visual and GPU validation remain pending.

- Rebalanced End celestial highlights: reduced Black Hole disk and photon-ring emission, White Hole core/disk emission, corona spread, and anamorphic flare intensity to reduce bloom spill around terrain silhouettes.
- Replaced the single tiny-star grid with two sparse world-space star layers featuring varied angular sizes, brightness, and cool/warm tints; added derivative filtering for unresolved stars and a smooth polar density fade. No new texture samples or animation were added.
- End composition values are an initial artistic pass; in-game silhouette, temporal stability, and macOS checks remain pending.

- Added **Black Hole Radial Rays** and a separate **Black Hole Ray Intensity** slider (0–150%) to Event Horizon settings, addressing issue #4.
- Rays default to ON at 100%, preserving the ray-control calculation; celestial emission is rebalanced separately in this beta. OFF and 0% use the same local back-disk mask, retaining the nearby Einstein ring, front accretion disk, event horizon, photon ring, and gravitational lensing.
- White Hole rendering and its light-ray toggle remain independent.
- Static validation performed; visual verification in Minecraft, including macOS, is pending.

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

[1.4.0-beta.2]: https://github.com/benjamincalledur10-bit/Lumina_Shader_Event_Horizon/releases/tag/v1.4.0-beta.2
