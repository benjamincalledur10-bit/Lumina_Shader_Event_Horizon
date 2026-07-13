#version 120

// Receive variables from Vertex Shader
varying vec2 texcoord;
varying vec4 glcolor;
varying vec3 normal;

// The base texture of the block (from Minecraft)
uniform sampler2D texture;

// Position of the sun/moon in the sky
uniform vec3 sunPosition;

void main() {
    // 1. Get the texture color of exactly this pixel
    vec4 color = texture2D(texture, texcoord);

    // Multiply by vertex color (biome grass tint, etc.)
    color *= glcolor;

    // 2. Lighting Calculation (Simple Lambertian Lighting)
    // How much does the normal match the sun's direction? (0.0 to 1.0)
    vec3 lightDir = normalize(sunPosition);
    float diffuseLight = max(dot(normal, lightDir), 0.1); // Add 0.1 ambient light so shadows aren't pitch black

    // 3. Fake "Sunset" Orange Tint
    // We add more Red and Green, keep Blue standard
    vec3 sunsetTint = vec3(1.3, 1.0, 0.7);

    // 4. Apply everything to final pixel
    vec3 finalColor = color.rgb * diffuseLight * sunsetTint;

    gl_FragColor = vec4(finalColor, color.a);
}
