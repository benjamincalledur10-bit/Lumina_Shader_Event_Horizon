#version 120

varying vec4 glcolor;

void main() {
    // 1. Darker night sky / sunset sky calculation
    // We add a darker blue and orange gradient
    vec3 skyColor = glcolor.rgb * vec3(0.8, 0.4, 0.2); // Intense sunset base

    gl_FragColor = vec4(skyColor, glcolor.a);
}
