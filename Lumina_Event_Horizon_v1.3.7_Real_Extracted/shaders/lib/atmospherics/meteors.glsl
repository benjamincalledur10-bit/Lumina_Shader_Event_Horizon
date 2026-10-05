#ifndef INCLUDE_LUMINA_METEORS
#define INCLUDE_LUMINA_METEORS

vec3 LuminaSkyEventSeed(vec2 cell, float slot, bool fireball) {
    vec3 p = fract(vec3(dot(cell, vec2(17.0, 53.0)) + slot * 11.0
                     + float(worldDay) * 73.0 + (fireball ? 137.0 : 0.0))
                     * vec3(0.1031, 0.1030, 0.0973));
    p += dot(p, p.yxz + 33.33);
    return fract((p.xxy + p.yzz) * p.zyx);
}
float LuminaMeteorNightWindow() {
    float nightHeight = -sin(timeAngle * 6.28318530718);
    return smoothstep(0.70, 0.97, nightHeight) * (1.0 - sunVisibility) * invRainFactor * invRainFactor;
}
// Each ray visits one sky cell per event type. Frequency never increases work.
// Paths stay inside their cell, avoiding seams and neighbouring-cell searches.
vec3 LuminaSkyEvent(vec2 skyCoord, float footprint, bool fireball, float frequency) {
    float scale = fireball ? 3.0 : 6.0;
    vec2 cell = floor(skyCoord * scale);
    float interval = fireball ? 67.0 : 20.0;
    float slot = floor(frameTimeCounter / interval);
    vec3 seed = LuminaSkyEventSeed(cell, slot, fireball);
    float probability = min(frequency * (fireball ? 0.008 : 0.01), 1.0);
    if (seed.x >= probability) return vec3(0.0);
    float duration = fireball ? mix(1.6, 2.4, seed.y) : mix(0.55, 0.90, seed.y);
    float delay = 1.0 + seed.z * (interval - duration - 2.0);
    float age = frameTimeCounter - slot * interval - delay;
    if (age <= 0.0 || age >= duration) return vec3(0.0);
    float progress = age / duration;
    float envelope = smoothstep(0.0, 0.12, progress) * (1.0 - smoothstep(0.72, 1.0, progress));
    vec2 center = (cell + 0.5 + (seed.xy - 0.5) * 0.16) / scale;
    vec2 rawDirection = seed.yz * 2.0 - 1.0;
    rawDirection += center * 0.6;
    vec2 direction = rawDirection * inversesqrt(max(dot(rawDirection, rawDirection), 0.0001));
    if (dot(direction, direction) < 0.1) direction = vec2(0.6, 0.8);
    vec2 headPosition = center + direction * ((progress - 0.5) * 0.32 / scale);
    vec2 delta = skyCoord - headPosition;
    float behind = -dot(delta, direction);
    float crossTrack = dot(delta, vec2(-direction.y, direction.x));
    float width = fireball ? 0.0009 : 0.00027;
    float filtered = sqrt(width * width + footprint * footprint);
    float crossRatio = crossTrack / filtered;
    float crossFalloff = exp(-crossRatio * crossRatio) * width / filtered;
    float tailLength = (fireball ? 0.22 : 0.16) / scale;
    float tail = exp(-max(behind, 0.0) / (tailLength * 0.35));
    tail *= smoothstep(-width, width, behind) * (1.0 - smoothstep(tailLength * 0.75, tailLength, behind));
    float headRatio = behind / (filtered * 2.0);
    float head = exp(-headRatio * headRatio) * crossFalloff;
    float greenEntry = smoothstep(0.10, 0.35, progress) * (1.0 - smoothstep(0.78, 0.98, progress));
    vec3 tint = fireball ? mix(vec3(1.0, 0.70, 0.38), vec3(0.30, 1.0, 0.48), greenEntry)
                        : vec3(0.65, 0.78, 1.0);
    float brightness = fireball ? 5.0 : 1.6;
    return (tint * (tail * crossFalloff + head * 0.7) + vec3(head * 0.35)) * brightness * envelope;
}
vec3 GetLuminaMeteors(vec3 viewDirection) {
    #if SHOOTING_STARS == 0 && METEORS == 0
        return vec3(0.0);
    #endif
    float visibility = LuminaMeteorNightWindow();
    if (visibility <= 0.001) return vec3(0.0);
    vec3 ray = normalize(mat3(gbufferModelViewInverse) * viewDirection);
    vec2 skyCoord = ray.xz / max(1.0 + ray.y, 0.0001);
    // Derivatives precede spatially divergent cell/event branches.
    float footprint = max(max(length(dFdx(skyCoord)), length(dFdy(skyCoord))), 0.00001);
    visibility *= smoothstep(0.02, 0.16, ray.y);
    if (visibility <= 0.001) return vec3(0.0);
    vec3 result = vec3(0.0);
    #if SHOOTING_STARS > 0
        result += LuminaSkyEvent(skyCoord, footprint, false, float(SHOOTING_STARS));
    #endif
    #if METEORS > 0
        result += LuminaSkyEvent(skyCoord, footprint, true, float(METEORS));
    #endif
    float darkness = 1.0 - maxBlindnessDarkness;
    return result * visibility * darkness * darkness;
}
#endif
