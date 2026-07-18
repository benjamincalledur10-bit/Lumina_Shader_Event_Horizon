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

vec3 GetEnderStars(vec3 viewPos, float VdotU) {
    vec3 wpos = normalize(mat3(gbufferModelViewInverse) * viewPos);

    // Equirectangular mapping for uniform sky
    float yaw = atan(wpos.z, wpos.x);
    float pitch = asin(wpos.y);
    vec2 uv = vec2(yaw, pitch);

    // Stars
    // Stars
    float starFactor = 6000.0;
    vec2 starUV = floor(uv * starFactor) / starFactor;

    float star = 1.0;
    star *= GetEnderStarNoise(starUV);
    star *= GetEnderStarNoise(starUV + 0.1);
    star *= GetEnderStarNoise(starUV + 0.23);
    star = max(star - 0.9, 0.0);
    star *= star * 1.0;

    vec3 starColor = mix(vec3(0.6, 0.8, 1.0), vec3(1.0, 0.8, 0.9), GetEnderStarNoise(starUV + 0.5));
    vec3 enderStars = star * starColor * 30.0;

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