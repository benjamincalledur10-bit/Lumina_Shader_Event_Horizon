float waterCaustics(vec3 worldPos, vec3 sunVec) {
	vec3 projectedPos = worldPos - (sunVec/max(sunVec.y, 0.001)*worldPos.y);
	vec2 pos = projectedPos.xz;

	float heightSum = 0.0;
	float movement = frameTimeCounter*0.035 * WATER_WAVE_SPEED;

	float radiance = 2.39996;
	mat2 rotationMatrix  = mat2(vec2(cos(radiance),  -sin(radiance)),  vec2(sin(radiance),  cos(radiance)));
	
	vec2 wave_size[3] = vec2[](
		vec2(48.,12.),
		vec2(12.,48.),
		vec2(32.,32.)
	);

	float WavesLarge = max(texture2D(noisetex, pos / 600.0 ).b,0.1);

	for (int i = 0; i < 3; i++){
		pos = rotationMatrix * pos;
		heightSum += pow(abs(abs(texture2D(noisetex, pos / wave_size[i] + WavesLarge*0.5 + movement).b * 2.0 - 1.0) * 2.0 - 1.0), 2.0) ;
	}

	float FinalCaustics = exp((1.0 + 5.0 * pow(WavesLarge,0.5)) * (heightSum / 3.0 - 0.5));
	return FinalCaustics;
}

// SEUS-style Gerstner Waves
vec4 getGerstnerWave(vec2 dir, float steepness, float wavelength, vec2 p, float t) {
    float k = 2.0 * 3.14159265 / wavelength;
    float c = sqrt(9.8 / k);
    vec2 d = normalize(dir);
    float f = k * (dot(d, p) - c * t);
    float a = steepness / k;
    
    float cosf = cos(f);
    float sinf = sin(f);
    
    return vec4(
        d.x * (a * cosf),
        a * sinf,
        d.y * (a * cosf),
        1.0
    );
}

float getWaterHeightmap(vec2 posxz) {
    float t = frameTimeCounter * WATER_WAVE_SPEED * 1.5;
    vec3 p = vec3(posxz.x, 0.0, posxz.y);
    
    p += getGerstnerWave(vec2(1.0, 0.5), 0.2, 10.0, posxz, t).xyz;
    p += getGerstnerWave(vec2(0.7, -0.6), 0.15, 6.0, posxz, t).xyz;
    p += getGerstnerWave(vec2(-0.5, 0.8), 0.1, 3.5, posxz, t).xyz;
    p += getGerstnerWave(vec2(-0.8, -0.2), 0.05, 1.5, posxz, t).xyz;
    p += getGerstnerWave(vec2(0.2, 0.9), 0.02, 0.8, posxz, t).xyz;
    
    return p.y * WATER_WAVE_STRENGTH * 0.4;
}

vec3 getWaveNormal(vec3 posxz, bool isLOD) {
    float t = frameTimeCounter * WATER_WAVE_SPEED * 1.5;
    vec2 pos = posxz.xz;
    vec3 n = vec3(0.0, 1.0, 0.0);
    
    // 5-octave Gerstner waves for sharp, detailed normal mapping
    vec4 waves[5] = vec4[](
        vec4(1.0, 0.5, 0.2, 10.0),
        vec4(0.7, -0.6, 0.15, 6.0),
        vec4(-0.5, 0.8, 0.1, 3.5),
        vec4(-0.8, -0.2, 0.05, 1.5),
        vec4(0.2, 0.9, 0.02, 0.8)
    );

    for(int i = 0; i < 5; i++) {
        vec2 d = normalize(waves[i].xy);
        float steepness = waves[i].z;
        float wavelength = waves[i].w;
        
        float k = 2.0 * 3.14159265 / wavelength;
        float c = sqrt(9.8 / k);
        float f = k * (dot(d, pos) - c * t);
        float a = steepness / k;
        
        float wa = k * a;
        float cosf = cos(f);
        float sinf = sin(f);
        
        n.x -= d.x * wa * cosf;
        n.z -= d.y * wa * cosf;
        n.y -= steepness * wa * sinf;
    }

    n.xz *= WATER_WAVE_STRENGTH * 1.5;
    return normalize(n);
}