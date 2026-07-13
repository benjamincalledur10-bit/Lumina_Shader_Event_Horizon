#version 120

// Varyings are variables passed from the Vertex Shader to the Fragment Shader
varying vec2 texcoord;
varying vec4 glcolor;
varying vec3 normal;

void main() {
    // 1. Convert the 3D world position into 2D screen coordinates
    gl_Position = ftransform();

    // 2. Pass the texture coordinates of the block face
    texcoord = (gl_TextureMatrix[0] * gl_MultiTexCoord0).xy;

    // 3. Pass the inherent color of the block (e.g. grass colors based on biome)
    glcolor = gl_Color;

    // 4. Calculate the normal vectors (which way the block's face is pointing) to compute sunlight later
    normal = normalize(gl_NormalMatrix * gl_Normal);
}
