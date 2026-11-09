# 4×4 VQ desktop experiment results

Two independent 256-entry RGB332 codebooks were trained from 80,000 sampled 4×4 patches. Each codebook occupies 4096 bytes.

## Nearest-codebook reconstruction

| Changed-patch result | Flash-style sample | Cel-animation sample |
|---|---:|---:|
| Mean RGB RMSE | 28.5 | 22.6 |
| Within 8 RGB levels | 20.3% | 23.0% |
| Within 16 RGB levels | 34.4% | 38.6% |
| Within 24 RGB levels | 45.5% | 52.6% |
| Within 32 RGB levels | 56.5% | 68.7% |

Exact matches alone cover about 17.9% of changed Flash patches and 20.5% of changed cel patches. Nearest matching therefore provides substantially more useful coverage than a dictionary limited to exact patterns.

## Same-budget temporal simulation

A persistent-frame simulation used 4×4 VQ updates, grouped into 8×8 records, at the cel baseline's 658,594-byte video target.

| Metric | Conservative codec | VQ simulation |
|---|---:|---:|
| Changed source patches held from prior reconstruction | 43.60% | 16.63% |
| Video bytes | 658,594 | 575,006 including 4 KiB codebook |

The VQ simulation reduced unchanged/stale changed patches by roughly 62% while remaining 83,588 bytes below the existing payload. Full VQ previews are softer than the conservative codec but substantially more spatially coherent. The unused budget can fund fallback raw/local-palette records for faces and important outlines.

## Decision

The experiment passed both the desktop and GBA runtime gates. v34 produced near-perfect motion with some softness; edge-weighted training and sharper fallback selection in v35 gave a subtle but confirmed outline improvement and better overall quality.

The implemented hybrid strategy is:

1. Keep existing 8×8 solid, palette, raw, and motion records.
2. Add a cheap 4×4 codebook-index record.
3. Use VQ for broad coherent updates and background/foreground replacement.
4. Spend the remaining rate budget on sharp fallback records selected by edge importance.
5. Store the 4 KiB episode codebook in GLV and cache it in EWRAM.
6. ~~Benchmark the GBA decoder before creating another full ROM.~~ v34 measures 86.5 ms worst-case including Matrix reads, with a typical/latest packet at 22.6 ms.
