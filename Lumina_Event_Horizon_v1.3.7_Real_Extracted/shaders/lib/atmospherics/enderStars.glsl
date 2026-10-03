float GetEnderStarNoise(vec2 pos) {
    return fract(sin(dot(pos, vec2(12.9898, 4.1414))) * 43758.54953);
}

float Eperlin(vec2 inCoord){
    vec2 i = floor(inCoord);
    vec2 j = fract(inCoord);
    vec2 coord = smoothstep(0.0, 1.0, j);

    float a = GetEnderStarNoise(i);
    float b = GetEnderStarNoise(i + vec2(1.0, 0.0));
    float c = GetEnderStarNoise(i + vec2(0.0, 1.0));
    float d = GetEnderStarNoise(i + vec2(1.0, 1.0));

    return mix(mix(a, b, coord.x), mix(c, d, coord.x), coord.y);
}

float EfbmCloud(vec2 inCoord){
    float value = 0.0;
    float scale = 0.5;
    for (int i = 0; i < 4; i++){
        value += Eperlin(inCoord) * scale;
        inCoord *= 2.0;
        scale *= 0.5;
    }
    return value;
}

// Two sparse angular layers give small distant stars and rare larger accents.
// Hash cells in world space; no time animation or additional texture samples.
vec3 GetEndStarLayer(vec2 skyUV, vec2 cells, float seed, float density,
                     float brightness, float angularFootprint) {
    vec2 grid = skyUV * cells;
    vec2 cell = floor(grid);
    cell.x = mod(cell.x, cells.x); // Same seed on either side of the yaw seam.
    float population = GetEnderStarNoise(cell + seed);
    float variation = GetEnderStarNoise(cell + seed + vec2(17.0, 43.0));
    float radius = mix(0.08, 0.20, variation * variation);
    float distanceToStar = length(fract(grid) - 0.5);
    float aa = max(0.015, angularFootprint * cells.y / 3.14159265);
    float shape = 1.0 - smoothstep(max(0.0, radius - aa), radius + aa, distanceToStar);
    // Keep unresolved stars from becoming bright oversized dots.
    shape *= min(1.0, radius * radius / (aa * aa));
    float presence = step(1.0 - density, population);
    vec3 tint = mix(vec3(0.65, 0.80, 1.0), vec3(1.0, 0.88, 0.72), variation);
    return tint * shape * presence * brightness * mix(0.25, 1.0, variation * variation);
}

vec3 GetEnderStars(vec3 viewPos, float VdotU) {
    vec3 wpos = normalize(mat3(gbufferModelViewInverse) * viewPos);

    // Equirectangular mapping for uniform sky
    float yaw = atan(wpos.z, wpos.x);
    float pitch = asin(clamp(wpos.y, -1.0, 1.0));
    vec2 uv = vec2(yaw, pitch);

    vec2 skyUV = vec2(yaw / 6.28318530 + 0.5, pitch / 3.14159265 + 0.5);
    float angularFootprint = length(fwidth(wpos));
    vec3 enderStars = GetEndStarLayer(skyUV, vec2(720.0, 360.0), 7.0, 0.025, 0.65, angularFootprint);
    enderStars += GetEndStarLayer(skyUV, vec2(240.0, 120.0), 91.0, 0.012, 1.30, angularFootprint);
    // Reduce equirectangular crowding near the poles without a hard cutoff.
    enderStars *= smoothstep(0.02, 0.18, cos(pitch));

    // End Nebula
    float time = syncedTime * 0.005;
    float neb1 = EfbmCloud(uv * 8.0 + vec2(time, time * 0.5));
    float neb2 = EfbmCloud(uv * 12.0 - vec2(time * 0.8, time * 0.2));
    
    float mask = smoothstep(0.45, 0.75, neb1);
    vec3 nebColor1 = vec3(0.2, 0.05, 0.4); // Deep purple
    vec3 nebColor2 = vec3(0.05, 0.2, 0.3); // Teal/Cyan
    vec3 nebColor3 = vec3(0.5, 0.1, 0.3); // Magenta accents
    
    vec3 nebula = mix(nebColor1, nebColor2, neb2) * mask;
    nebula += nebColor3 * smoothstep(0.6, 0.9, neb1 * neb2) * 0.8;
    
    return enderStars + nebula * 0.3;
}