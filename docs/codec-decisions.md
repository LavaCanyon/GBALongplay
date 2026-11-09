# Codec optimization decisions

## Retained

- 10 fps, 240×160 RGB332 output
- Four-11-minute / 44-minute capacity profile
- Complete two-colour keyframes at detected cuts
- Gradual 24-frame rate-debt repayment
- 4-pixel-step motion vectors within ±8 pixels
- Solid, two-colour, four-colour, raw, and motion-copy 8×8 modes
- Sparse packet-header decoding support
- Audio-master timestamps and four-second ADPCM buffers

## Experimental, disabled by default

### Variable-frame-rate holds

Safe and space-efficient, but the supplied sample omitted only 55 of 409 source frames and produced little visible improvement. Disabled by a negative default threshold.

### 4×4 quadrant patches

At unrestricted use, the encoder updated roughly 207 regions per coded frame but exceeded the practical ARM7 workload and starved background audio preparation. Capping the mode at 48 records restored stability but looked very similar to the simpler codec. The decoder retains support for format experiments, while the encoder default limit is zero.

## Practical conclusion

For the current 64 MiB, 44-minute target, the conservative 8×8 codec is the best verified quality/performance tradeoff. Further substantial gains likely require a redesigned codec—such as motion residuals, hierarchical 16×16/8×8 blocks, vector codebooks, or a transform codec—rather than more incremental record types.
