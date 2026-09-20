# Lumina Shader: Event Horizon

<p align="center">
  A cinematic Minecraft: Java Edition shader pack built around advanced
  lighting, atmospheric depth, and a complete cosmic overhaul of the End.
</p>

<p align="center">
  <a href="https://github.com/benjamincalledur10-bit/Lumina_Shader_Event_Horizon/releases/latest"><img alt="Latest GitHub release" src="https://img.shields.io/github/v/release/benjamincalledur10-bit/Lumina_Shader_Event_Horizon?style=for-the-badge"></a>
  <a href="https://github.com/benjamincalledur10-bit/Lumina_Shader_Event_Horizon/releases/latest"><img alt="GitHub downloads" src="https://img.shields.io/github/downloads/benjamincalledur10-bit/Lumina_Shader_Event_Horizon/total?style=for-the-badge&logo=github&label=GitHub&cacheSeconds=172800"></a>
  <a href="https://modrinth.com/shader/lumina-shader-event-horizon"><img alt="Modrinth downloads" src="https://img.shields.io/modrinth/dt/9gxVXUDr?style=for-the-badge&logo=modrinth&label=Modrinth&cacheSeconds=172800"></a>
  <a href="https://www.curseforge.com/minecraft/shaders/lumina-shaders-event-horizon"><img alt="CurseForge downloads" src="https://img.shields.io/curseforge/dt/1481177?style=for-the-badge&logo=curseforge&label=CurseForge&cacheSeconds=172800"></a>
</p>

Download counters are refreshed automatically every 48 hours.

## Download

Use one of the official distribution pages:

- [GitHub Releases](https://github.com/benjamincalledur10-bit/Lumina_Shader_Event_Horizon/releases/latest)
- [Modrinth](https://modrinth.com/shader/lumina-shader-event-horizon)
- [CurseForge](https://www.curseforge.com/minecraft/shaders/lumina-shaders-event-horizon)

The development version is **v1.3.9**, targeting Minecraft **1.8 through 26.3**.
The latest published stable release remains **v1.3.81** until v1.3.9 is released.
Keep downloaded `.zip` files compressed when installing them.

## Highlights

- **Event Horizon End overhaul:** a world-space black hole with an accretion
  disk, gravitational lensing, photon ring, and dedicated End lighting.
- **White Hole counterpart:** a luminous opposite pole with optional cinematic
  anamorphic light rays.
- **Volumetric atmosphere:** multi-octave clouds, powder scattering, fog,
  auroras, rainbows, stars, and dimension-specific effects.
- **Advanced lighting:** volumetric light shafts, colored lighting, shadows,
  ambient occlusion, reflections, and PBR material support.
- **Cinematic post-processing:** bloom, temporal anti-aliasing, depth of field,
  color grading, vignette, and lens effects.
- **Scalable profiles:** presets ranging from Potato to Ultra, with additional
  controls for users who want to tune individual effects.
- **Extended rendering support:** dedicated shader programs for Distant
  Horizons terrain and water.

## Compatibility

| Component | Support |
| --- | --- |
| Game | Minecraft: Java Edition 1.8 through 26.3 |
| Shader loaders | Iris for modern versions; OptiFine for supported legacy versions |
| Rendering profiles | Potato, Very Low, Low, Medium, High, Very High, Ultra |

[Iris](https://www.irisshaders.dev/) is recommended for modern Minecraft
versions, including 26.3. Install a loader build matching your Minecraft version;
the shader pack does not run in vanilla Minecraft without a shader loader.
The same pack contains legacy and modern rendering paths, selected automatically.
Individual effects depend on loader and hardware capabilities.

The 1.3.9 compatibility changes have static validation; in-game verification across
the full version range is still pending. Performance depends on resolution,
render distance, selected profile, resource packs, and GPU.

## Installation

1. Install [Iris](https://www.irisshaders.dev/) or a compatible OptiFine
   version.
2. Download the latest stable ZIP from an official source above. The upcoming
   development package is named `Lumina_Event_Horizon_v1.3.9.zip`.
3. Open Minecraft and go to **Options > Video Settings > Shader Packs**.
4. Open the shader-pack folder and place the downloaded ZIP inside it. Do not
   extract the archive.
5. Return to Minecraft, select **Lumina Event Horizon**, and apply the settings.
6. Start with the High or Medium profile, then adjust quality for your hardware.

The default shader-pack directory is usually:

```text
~/.minecraft/shaderpacks
```

## Cinematic autofocus

Open **Shader Settings > Cinematics > Focus & Depth of Field**, set **Blur Mode**
to **Cinematic Autofocus**, and leave **Depth of Field Focus** on **Automatic**.
The center focus plane and foreground stay sharp while the background blurs.
Adjust **Autofocus Blur Strength** and **Autofocus Quality** to taste.
The effect is off by default. Motion blur has been removed.
Visual verification in Minecraft is still pending.

## Configuration tips

- Reduce cloud quality, shadow distance, reflections, and light-shaft quality
  first when targeting higher frame rates.
- Use Very High or Ultra for screenshots only if your GPU has enough headroom.
- If a resource pack provides PBR textures, select the matching material mode
  in the shader settings.
- Reset the shader profile after upgrading if old per-version settings produce
  unexpected visuals.

## Development

- `main` contains the current stable, published state.
- `luminahorizondev` is used for development and validation before a release.
- The canonical source is `Lumina_Event_Horizon_v1.3.7_Real_Extracted/`; its
  historical directory name does not indicate the current pack version.
- Run `python3 scripts/validate_canonical.py` before packaging or pushing.
- Every release is documented in [CHANGELOG.md](CHANGELOG.md).
- Bugs and reproducible visual issues can be reported through
  [GitHub Issues](https://github.com/benjamincalledur10-bit/Lumina_Shader_Event_Horizon/issues).

When reporting a problem, include the Minecraft version, shader loader and
version, GPU, graphics-driver version, active shader profile, and screenshots or
logs when available.

## Credits

- **Main developer:** Benjiaa
- Lumina Event Horizon is based on
  [Complementary Reimagined](https://www.complementary.dev/shaders/)
  by EminGT. Special thanks to EminGT and the Complementary shader community.

## Community and support

- [Discord community](https://discord.gg/JK6rTQ9T)
- [Support development on Ko-fi](https://ko-fi.com/lumina_dev/goal?g=0)

## License

Lumina Shader: Event Horizon is a Modified Pack distributed under the
[Complementary License Agreement 1.6](License.txt). The unchanged license is
also included inside every downloadable shader ZIP, as required by the original
pack's terms. Review it before redistributing, including the shader in a
modpack, or creating another modified pack.
