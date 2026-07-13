# Changelog

All notable changes to Lumina Event Horizon are documented in this file.

## [Unreleased]

Add new changes here while developing the next version, then rename this
section to the release version and date when publishing.

## [1.3.5] - 2026-07-13

### Added

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

[Unreleased]: https://github.com/benjamincalledur10-bit/Lumina_Shader_Event_Horizon/compare/v1.3.5...HEAD
[1.3.5]: https://github.com/benjamincalledur10-bit/Lumina_Shader_Event_Horizon/releases/tag/v1.3.5
