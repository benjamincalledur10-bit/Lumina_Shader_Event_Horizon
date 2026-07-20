# Changelog

All notable changes to Lumina Event Horizon are documented in this file.

## [Unreleased]

### Fixed

- Prevented undefined zero-vector normalization in opaque shadow and light-shaft colors.
- Composited both Reimagined cloud layers when the nearer layer is translucent.
- Added a stable End light-direction fallback at the exact world origin.
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

[Unreleased]: https://github.com/benjamincalledur10-bit/Lumina_Shader_Event_Horizon/compare/v1.3.6...HEAD
[1.3.6]: https://github.com/benjamincalledur10-bit/Lumina_Shader_Event_Horizon/compare/v1.3.5...v1.3.6
[1.3.5]: https://github.com/benjamincalledur10-bit/Lumina_Shader_Event_Horizon/releases/tag/v1.3.5
