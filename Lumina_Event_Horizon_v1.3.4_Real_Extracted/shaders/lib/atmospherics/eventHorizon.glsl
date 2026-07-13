vec3 GetLensedDir(vec3 nViewPos, vec3 upVec, vec3 eastVec) {
    vec3 bhPosWorld = normalize(vec3(-1.0, 0.25, -1.5)); 
    float bhSize = 0.12;

    vec3 worldDir = mat3(gbufferModelViewInverse) * nViewPos;
    float cosTheta = dot(worldDir, bhPosWorld);
    
    if (cosTheta < 0.2) return worldDir;
    
    float angle = acos(clamp(cosTheta, -1.0, 1.0));
    
    // Only lens the background near the black hole
    if (angle > bhSize * 4.0) return worldDir;
    
    float deflection = (bhSize * bhSize * 1.2) / max(angle, 0.001);
    
    // Fade out deflection so it doesn't streak the whole sky
    deflection *= 1.0 - smoothstep(bhSize, bhSize * 4.0, angle);

    if (angle < bhSize * 0.95) {
        return vec3(0.0);
    }

    vec3 tangent = normalize(worldDir - bhPosWorld * cosTheta);
    vec3 lensedDir = normalize(worldDir - tangent * deflection);

    return lensedDir;
}

// Evaluate the accretion disk color and density at a given local space radius and uv
vec4 getDisk(float R, vec2 disk_uv, float R_in, float R_out) {
    if (R < R_in || R > R_out) return vec4(0.0);
    
    float time = syncedTime * 0.1;
    // Use smoother UV scaling to avoid exposing texture pixels
    vec2 n1_uv = disk_uv * 0.8 - vec2(time, 0.0);
    vec2 n2_uv = disk_uv * 1.6 + vec2(time * 0.6, 0.0);
    vec2 n3_uv = disk_uv * 2.4 - vec2(time * 0.3, 0.0);
    
    // Smooth bilinear sampling by relying on hardware filtering
    float noise1 = texture2DLod(noisetex, n1_uv, 0.0).r;
    float noise2 = texture2DLod(noisetex, n2_uv, 0.0).g;
    float noise3 = texture2DLod(noisetex, n3_uv, 0.0).b;
    
    // Combine for a smooth, cloudy plasma look without harsh holes
    float detail = noise1 * 0.5 + noise2 * 0.3 + noise3 * 0.2;
    
    // Base volumetric shape: smooth fade from inner edge to outer edge for 3D depth/volume
    float density = (1.0 - smoothstep(R_in, R_out, R)) * smoothstep(R_in - 0.2, R_in + 0.2, R);
    
    // Soft noise modulation for dust lanes and volume (avoids pixelated 'huecos')
    density *= (0.4 + detail * 1.5);
    
    float doppler = smoothstep(-R_out, R_out, disk_uv.x); // Right side approaching -> blueshift
    vec3 colCore = vec3(1.0, 0.95, 0.85) * 5.0; // Brighter core
    vec3 colDust = vec3(0.9, 0.4, 0.05) * 2.0; // Richer orange
    
    vec3 color = mix(colDust, colCore, 1.0 - smoothstep(R_in, R_in + 1.0, R));
    
    // Enhance color with noise for texture
    color *= (0.7 + detail * 0.5);
    color *= (0.6 + doppler * 0.8);
    
    return vec4(color, clamp(density, 0.0, 1.0));
}

vec4 GetBlackHole(vec3 nViewPos, vec3 upVec, vec3 eastVec, float dither) {
    // FIXED: Use a constant WORLD space direction so the black hole is fixed in the sky.
    // Minecraft End spawn usually faces -X. So we place it at (-1.0, 0.25, -1.5) (Further right).
    vec3 bhPosWorld = normalize(vec3(-1.0, 0.25, -1.5)); 
    float bhSize = 0.12; // Gargantua scale
    
    vec3 worldDir = mat3(gbufferModelViewInverse) * nViewPos;
    
    // Check if we are looking towards the black hole to prevent mirroring behind the camera
    float cosTheta = dot(worldDir, bhPosWorld);
    // Let the radial rays cover almost the entire sky, just cut it off slightly behind the player to avoid singularities
    if (cosTheta < -0.99) return vec4(0.0); 
    
    // Local orthonormal basis for the black hole in WORLD space
    vec3 bhX = normalize(cross(bhPosWorld, vec3(0, 1, 0))); 
    vec3 bhY = normalize(cross(bhX, bhPosWorld)); 
    
    // Proper spherical projection to prevent infinite stretching (laser beams)
    float angle = acos(clamp(cosTheta, -1.0, 1.0));
    vec3 localDir = vec3(dot(worldDir, bhX), dot(worldDir, bhY), cosTheta);
    
    vec2 uv = vec2(0.0);
    if (angle >= 0.0001) uv = normalize(localDir.xy) * (angle / bhSize);
    float r = length(uv);
    
    vec4 finalCol = vec4(0.0);
    
    // Disk inner and outer radii (in EH units)
    float R_in = 1.02; // Touches the event horizon perfectly!
    float R_out = 5.0;
    float tilt = 0.1; // Tilt of the accretion disk
    
    // ---------------------------------------------------------
    // 1. Event Horizon (Perfect Sphere)
    // ---------------------------------------------------------
    if (r <= 1.0) {
        finalCol = vec4(0.0, 0.0, 0.0, 1.0);
    } else {
        // ---------------------------------------------------------
        // 2. Einstein Ring (Lensed back-disk passing over/under)
        // ---------------------------------------------------------
        // Map screen radius r directly to disk radius R_back to guarantee a clean ring
        // The disk appears between r=1.0 and r=1.35
        float R_back = mix(R_out, R_in, smoothstep(1.0, 1.35, r));
        
        vec2 uv_back = normalize(uv) * R_back;
        vec4 backDisk = getDisk(R_back, uv_back, R_in, R_out);
        
        // The back disk is lensed over the poles. Fade it at the equator to avoid clipping the front disk.
        float poleMask = smoothstep(0.0, 0.5, abs(uv.y) / r);
        backDisk.a *= poleMask;
        
        // Constrain the Einstein ring tightly around the black hole instead of spanning the map
        backDisk.a *= 1.0 - smoothstep(1.25, 1.5, r);
        
        finalCol.rgb = backDisk.rgb * backDisk.a;
        finalCol.a = backDisk.a;
    }
    
    // ---------------------------------------------------------
    // 3. Front Accretion Disk
    // ---------------------------------------------------------
    // The front disk covers the black hole and slightly bows due to gravity.
    vec2 uv_front = uv * (1.0 + 0.05 / max(r, 0.5));
    float R_front = sqrt(uv_front.x * uv_front.x + pow2(uv_front.y / tilt));
    
    // If we are inside the EH, only draw the front half of the disk to cover the sphere
    bool isVisible = true;
    if (r <= 1.0 && uv.y > 0.0) isVisible = false; // The top half of the ellipse is behind the sphere
    
    if (isVisible) {
        vec4 frontDisk = getDisk(R_front, uv_front, R_in, R_out);
        finalCol.rgb = mix(finalCol.rgb, frontDisk.rgb, frontDisk.a);
        finalCol.a = max(finalCol.a, frontDisk.a);
    }
    
    // Photon ring glow
    float photonRing = (1.0 - smoothstep(1.0, 1.06, r)) * smoothstep(0.96, 1.0, r);
    finalCol.rgb += vec3(1.0, 0.8, 0.6) * photonRing * 1.5 * (1.0 - finalCol.a);
    finalCol.a = max(finalCol.a, photonRing);

    return finalCol;
}

// ---------------------------------------------------------
// WHITE HOLE IMPLEMENTATION (Opposite Pole)
// ---------------------------------------------------------
vec4 getWhiteDisk(float R, vec2 disk_uv, float R_in, float R_out) {
    if (R < R_in || R > R_out) return vec4(0.0);
    
    // Reverse time so matter looks like it's being expelled
    float time = -syncedTime * 0.2; 
    
    vec2 n1_uv = disk_uv * 0.8 - vec2(time, 0.0);
    vec2 n2_uv = disk_uv * 1.6 + vec2(time * 0.6, 0.0);
    vec2 n3_uv = disk_uv * 2.4 - vec2(time * 0.3, 0.0);
    
    float noise1 = texture2DLod(noisetex, n1_uv, 0.0).r;
    float noise2 = texture2DLod(noisetex, n2_uv, 0.0).g;
    float noise3 = texture2DLod(noisetex, n3_uv, 0.0).b;
    
    float detail = noise1 * 0.5 + noise2 * 0.3 + noise3 * 0.2;
    
    float density = (1.0 - smoothstep(R_in, R_out, R)) * smoothstep(R_in - 0.2, R_in + 0.2, R);
    density *= (0.4 + detail * 1.5);
    
    float doppler = smoothstep(-R_out, R_out, disk_uv.x);
    
    // Blinding blue-white energy colors
    vec3 colCore = vec3(0.9, 0.95, 1.0) * 8.0; 
    vec3 colDust = vec3(0.2, 0.6, 1.0) * 3.0; 
    
    vec3 color = mix(colDust, colCore, 1.0 - smoothstep(R_in, R_in + 1.0, R));
    
    color *= (0.7 + detail * 0.5);
    color *= (0.6 + doppler * 0.8);
    
    return vec4(color, clamp(density, 0.0, 1.0));
}

vec4 GetWhiteHole(vec3 nViewPos, vec3 upVec, vec3 eastVec, float dither) {
    // Placed exactly opposite the black hole
    vec3 bhPosWorld = -normalize(vec3(-1.0, 0.25, -1.5)); 
    float bhSize = 0.12; 
    
    vec3 worldDir = mat3(gbufferModelViewInverse) * nViewPos;
    
    float cosTheta = dot(worldDir, bhPosWorld);
    // Only render the white hole if we look at the opposite pole (don't cover the black hole)
    if (cosTheta < -0.8) return vec4(0.0); 
    
    vec3 bhX = normalize(cross(bhPosWorld, vec3(0, 1, 0))); 
    vec3 bhY = normalize(cross(bhX, bhPosWorld)); 
    
    float angle = acos(clamp(cosTheta, -1.0, 1.0));
    vec3 localDir = vec3(dot(worldDir, bhX), dot(worldDir, bhY), cosTheta);
    
    vec2 uv = vec2(0.0);
    if (angle >= 0.0001) uv = normalize(localDir.xy) * (angle / bhSize);
    float r = length(uv);
    
    vec4 finalCol = vec4(0.0);
    
    float R_in = 1.02; 
    float R_out = 5.0;
    float tilt = 0.1; 
    
    // 1. Bright White Sphere Core
    if (r <= 1.0) {
        float glow = 1.0 - smoothstep(0.0, 1.0, r);
        finalCol = vec4(vec3(1.0, 0.95, 1.0) * (5.0 + glow * 5.0), 1.0);
    } else {
        // 2. Einstein Ring (Lensed back-disk)
        float R_back = mix(R_out, R_in, smoothstep(1.0, 1.35, r));
        
        vec2 uv_back = normalize(uv) * R_back;
        vec4 backDisk = getWhiteDisk(R_back, uv_back, R_in, R_out);
        
        // No massive radial streaks for the white hole, just the ring itself
        backDisk.a *= 1.0 - smoothstep(1.1, 1.5, r);
        
        float poleMask = smoothstep(0.0, 0.5, abs(uv.y) / r);
        backDisk.a *= poleMask;
        
        finalCol.rgb = backDisk.rgb * backDisk.a;
        finalCol.a = backDisk.a;
    }
    
    // 3. Front Expulsion Disk
    vec2 uv_front = uv * (1.0 + 0.05 / max(r, 0.5));
    float R_front = sqrt(uv_front.x * uv_front.x + pow2(uv_front.y / tilt));
    
    bool isVisible = true;
    if (r <= 1.0 && uv.y > 0.0) isVisible = false;
    
    if (isVisible) {
        vec4 frontDisk = getWhiteDisk(R_front, uv_front, R_in, R_out);
        finalCol.rgb = mix(finalCol.rgb, frontDisk.rgb, frontDisk.a);
        finalCol.a = max(finalCol.a, frontDisk.a);
    }
    
    // 4. Outer Glow (Corona of expelled energy)
    if (r > 1.0) {
        float outerGlow = 1.0 - smoothstep(1.0, 3.5, r);
        finalCol.rgb += vec3(0.5, 0.8, 1.0) * outerGlow * 1.5;
        finalCol.a = max(finalCol.a, outerGlow * 0.5);
    }
    
    return finalCol;
}
