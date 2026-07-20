/////////////////////////////////////
// Lumina Shader - Event Horizon //
/////////////////////////////////////

// Lumina renders its own volumetric cloud system, so the vanilla cloud mesh
// is always suppressed in both shader stages.

#ifdef FRAGMENT_SHADER
void main() {
    discard;
}
#endif

#ifdef VERTEX_SHADER
void main() {
    gl_Position = vec4(-1.0);
}
#endif
