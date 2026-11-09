# GLP-VQ experiment plan

## Reason for pivot

Repeated changes to block priority, stale age, and occlusion scoring produced little visible reduction in background remnants. The limiting factor is representational: an irregular cel boundary still requires an expensive 8×8 record. Ranking the same records differently cannot make enough boundary data fit.

The unrestricted 4×4 patch experiment updated many more regions but was too expensive for the ARM7 because every patch carried and unpacked its own palette and index data.

## Proposed representation

Train a reusable episode-level codebook of 256 RGB332 patterns, each 4×4 pixels:

- Codebook storage: 256 × 16 bytes = 4096 bytes per episode.
- A quadrant update references one pattern with a one-byte index.
- An 8×8 record contains a four-bit quadrant mask and 1–4 codebook indices.
- Record size: 3–6 bytes, including mode and mask.
- Decoder operation: copy 16 known bytes per quadrant; no palette reconstruction or clustering on GBA.

Nearest-codebook matching is performed entirely by the desktop encoder. The GBA keeps the 4 KiB codebook in EWRAM.

## Expected advantages

- Character boundaries can update at 4×4 granularity.
- Faces and irregular linework receive more spatial detail.
- Flat colour patterns recur frequently and become very cheap.
- Decoder cost is substantially lower than the rejected dynamic 4×4 mode.
- Background restoration and foreground arrival use the same representation.
- Existing 8×8 solid, palette, raw, and motion modes remain as fallbacks.

## Development gates

1. Train codebooks from both the Flash-style and cel-animation samples.
2. Produce desktop-decoded comparison frames and objective error statistics.
3. Measure the percentage of quadrants that meet acceptable VQ error.
4. ~~Reject the experiment if it does not materially improve cel frames at the same byte budget.~~ Passed: stale changed patches fell from 43.60% to 16.63%.
5. Add GLV2 codebook storage and a hybrid GBA decoder mode.
6. Benchmark the GBA implementation before producing another 64 MiB ROM.

This avoids repeating ROM iterations for allocation heuristics that cannot overcome the current representation limit.
