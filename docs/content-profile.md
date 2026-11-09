# Target content profile: Western animation

The primary target is Western television animation rather than anime. Subtitle-specific preservation is not a default priority.

## Optimization priorities

1. Stable high-contrast outlines and flat colour regions
2. Tweened character motion and mouth/eye animation
3. Camera pans and moving backgrounds
4. Immediate recovery at hard cuts
5. Dark scenes, gradients, transparency, and effects
6. Audio quality and synchronization
7. General text readability where inexpensive

## Test material

The current sample is a strong Flash-style baseline covering dialogue, movement, cuts, pans, dark areas, gradients, and effects. It should remain a regression test.

A second sample should eventually use non-Flash Western animation—traditional/cel-like linework, textured backgrounds, or more irregular frame-to-frame drawing—to prevent the codec from overfitting clean vector shapes and reusable tweened regions.

## Codec implications

- Favor solid fills and compact local palettes.
- Motion search should support tweened translation and camera pans.
- Scene keyframes remain important.
- Palette work should prioritize gradients and dark colour separation.
- Small-block modes are optional and CPU-bounded, not driven by subtitle preservation.
- Future major experiments should focus on hierarchical motion, motion residuals, and scene-adaptive palettes.
