#version 120

varying vec4 glcolor;

void main() {
    // 1. Convert the 3D world position into 2D screen coordinates
    gl_Position = ftransform();

    // 2. Pass the base color of the sky
    glcolor = gl_Color;
}
