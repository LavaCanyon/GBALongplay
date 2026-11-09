# GLF1 animated backgrounds

GLF1 stores a timed sequence of GLI1 full-screen RGB332 frames. Identical frames are deduplicated. Every frame independently chooses raw, row-RLE, or solid GLI1 encoding.

The converter normalizes GIF disposal/transparency through Pillow, scales to 240×160, samples at a configurable 1–10 fps, and optionally limits loop duration. GIF timing is converted to 60 Hz GBA VBlank durations.

Planned consumers are global/per-episode menu backgrounds, startup splashes, pre-play screens, and description backgrounds. Static GLI1 remains valid everywhere GLF1 is accepted.

The first runtime implementation will decode complete frames into the existing EWRAM image buffer, copy to VRAM, then composite menu/description text directly in VRAM so dynamic UI pixels never contaminate the next animation frame.
