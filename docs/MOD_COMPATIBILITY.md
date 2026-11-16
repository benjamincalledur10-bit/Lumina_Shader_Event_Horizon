# Rendering-mod compatibility review

Reviewed 2026-11-16. This is not an exhaustive modpack certification. A mod with no
special Lumina integration is not automatically incompatible; rendering backends,
individual effects and exact Minecraft/mod versions need separate treatment.

| Mod / feature | Status with Lumina's Iris route | Evidence / scope |
|---|---|---|
| Voxy | Experimental implementation; Minecraft runtime unverified | See [VOXY.md](VOXY.md). Windows/Linux OpenGL 4.6; Voxy patch API 1 / VOXY macro 3 reference. |
| Distant Horizons | Existing dedicated Lumina terrain/water/depth paths | Present in the repository. Do not combine active DH and Voxy rendering in this experimental integration. No claim of every mod-version combination being tested. |
| VulkanMod (base renderer) | Incompatible with the normal Iris/OpenGL route | Its [FAQ](https://github.com/xCollateral/VulkanMod/wiki/) says shader support is not available through that route; its [compatibility list](https://github.com/xCollateral/VulkanMod/wiki/Incompatible-mods) lists Iris/Sodium. That list is dated 2024, so it is not a fresh test of every current build. Third-party Vulkan shader translators are a separate, untested integration. |
| Canvas | Renderer conflict with Iris/Sodium | [Iris guide](https://github.com/IrisShaders/Iris/blob/26.1/docs/guide.md). Supporting Canvas's rendering/shader format is not a small Lumina patch. |
| Colored Lights by Gegy | Incompatible with the Sodium/Iris stack as documented by Iris | [Iris incompatibilities](https://github.com/IrisShaders/Iris/blob/26.1/docs/usage/incompatible-mods.md). This is about that specific mod, not every colored-lighting mod or Lumina's own colored lighting. |
| Immersive Portals | Partial / unverified for Lumina, not blanket-incompatible | The [mod author](https://qouteall.fun/immptl/wiki/Miscellaneous) warns of shader limitations and recommends disabling TAA/AA in affected cases. [Iris documents](https://github.com/IrisShaders/Iris/blob/26.1/docs/usage/incompatible-mods.md) an underwater-mirror/transparency limitation. No dedicated Lumina portal test has been run. |
| Nvidium | Can coexist, but its accelerated rendering is unavailable while Iris shaders are active | Its [Iris check](https://github.com/MCRcortex/nvidium/blob/dev/src/main/java/me/cortex/nvidium/sodiumCompat/IrisCheck.java) gates the renderer on whether an Iris shader pack is in use. Do not describe that as Lumina-specific support or a Lumina crash. |
| Botania custom shader effects | Specific effects have documented Iris conflicts; not the whole mod | [Iris incompatibilities](https://github.com/IrisShaders/Iris/blob/26.1/docs/usage/incompatible-mods.md). A shader-pack-only fix cannot universally replace another mod's custom render programs. |
| Bobby / Farsight / ordinary gameplay mods | Not classified as incompatible | No evidence in this review justifies a blanket failure claim. They are not certified by this change; test the actual modpack. |

Possible next investigation: Immersive Portals with a minimal version-matched
Iris setup. Investigate an actual reproducible visual failure before adding a
compatibility switch. VulkanMod and Canvas need renderer-side solutions rather
than a shader-pack flag.
