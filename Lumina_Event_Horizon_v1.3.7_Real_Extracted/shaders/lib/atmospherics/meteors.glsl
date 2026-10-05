#ifndef INCLUDE_LUMINA_METEORS
#define INCLUDE_LUMINA_METEORS

vec3 LuminaMeteorSeed(float slot, int lane) {
    vec3 p = fract(vec3(slot + float(worldDay) * 73.0 + float(lane) * 137.0) * vec3(0.1031, 0.1030, 0.0973));
    p += dot(p, p.yxz + 33.33);
    return fract((p.xxy + p.yzz) * p.zyx);
}
float LuminaMeteorNightWindow() {
    float nightHeight = -sin(timeAngle * 6.28318530718);
    return smoothstep(0.70, 0.97, nightHeight) * (1.0 - sunVisibility) * invRainFactor * invRainFactor;
}
vec3 GetLuminaMeteors(vec3 viewDirection) {
    #if SHOOTING_STARS == 0
        return vec3(0.0);
    #endif
    float visibility = LuminaMeteorNightWindow();
    if (visibility <= 0.001) return vec3(0.0);
    // Directions (not camera positions) keep events fixed in the world sky.
    vec3 ray = normalize(mat3(gbufferModelViewInverse) * viewDirection);
    visibility *= smoothstep(0.02, 0.16, ray.y);
    if (visibility <= 0.001) return vec3(0.0);
    vec3 result = vec3(0.0);
    // Two distant shooting-star lanes and one rarer atmospheric fireball lane.
    for (int lane = 0; lane < 3; lane++) {
        bool fireball = lane == 2;
        float interval = lane == 0 ? 13.0 : (lane == 1 ? 19.0 : 67.0);
        float slot = floor(frameTimeCounter / interval);
        vec3 seed = LuminaMeteorSeed(slot, lane);
        if (seed.x > (fireball ? 0.24 : 0.55)) continue;
        float duration = fireball ? mix(1.6, 2.4, seed.y) : mix(0.55, 0.90, seed.y);
        float delay = 1.0 + seed.z * (interval - duration - 2.0);
        float age = frameTimeCounter - slot * interval - delay;
        if (age <= 0.0 || age >= duration) continue;
        float progress = age / duration;
        float envelope = smoothstep(0.0, 0.12, progress) * (1.0 - smoothstep(0.72, 1.0, progress));
        float azimuth = seed.y * 6.28318530718;
        float elevation = mix(0.35, 0.80, seed.z);
        float horizontal = sqrt(1.0 - elevation * elevation);
        vec3 start = vec3(cos(azimuth) * horizontal, elevation, sin(azimuth) * horizontal);
        vec3 right = vec3(-sin(azimuth), 0.0, cos(azimuth));
        vec3 up = normalize(vec3(0.0, 1.0, 0.0) - start * start.y);
        vec3 travel = normalize(right * (seed.z < 0.5 ? -0.8 : 0.8) - up * 0.6);
        float forward = dot(ray, start);
        if (forward <= 0.0) continue;
        float along = atan(dot(ray, travel), forward);
        float crossTrack = asin(clamp(dot(ray, cross(start, travel)), -1.0, 1.0));
        float headAngle = progress * (fireball ? 0.24 : 0.32);
        float behind = headAngle - along;
        float width = fireball ? 0.0018 : 0.00055;
        // Screen-space footprint prevents subpixel streaks from flickering.
        float footprint = max(length(vec2(dFdx(crossTrack), dFdy(crossTrack))), 0.00002);
        float filtered = sqrt(width * width + footprint * footprint);
        float crossFalloff = exp(-pow(crossTrack / filtered, 2.0)) * width / filtered;
        float tailLength = fireball ? 0.11 : 0.065;
        float tail = exp(-max(behind, 0.0) / (tailLength * 0.35));
        tail *= smoothstep(-width, width, behind) * (1.0 - smoothstep(tailLength * 0.75, tailLength, behind));
        float head = exp(-pow(behind / (filtered * 2.0), 2.0)) * crossFalloff;
        float greenEntry = smoothstep(0.10, 0.35, progress) * (1.0 - smoothstep(0.78, 0.98, progress));
        vec3 tint = fireball ? mix(vec3(1.0, 0.70, 0.38), vec3(0.30, 1.0, 0.48), greenEntry)
                            : vec3(0.65, 0.78, 1.0);
        float brightness = fireball ? 5.0 : 1.6;
        result += (tint * (tail * crossFalloff + head * 0.7) + vec3(head * 0.35)) * brightness * envelope;
    }
    return result * visibility * pow(1.0 - maxBlindnessDarkness, 2.0);
}
#endif
