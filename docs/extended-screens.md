# Extended screen system

## Feature toggles

Each project can independently enable or disable:

- zero to three startup splash screens;
- one pre-play screen per episode;
- one description page per episode.

## Startup splash screens

Each splash has:

- full-screen 240×160 image;
- duration in frames/seconds;
- advance mode: timed, wait for button, or timed and skippable;
- optional fade in/out;
- independent enabled toggle.

Startup order is Splash 1 → Splash 2 → Splash 3 → episode menu. A disabled entry is omitted.

## Pre-play episode screen

Shown after choosing an episode and before audio/video initialization. Each episode independently selects:

- disabled;
- timed;
- wait for A/Start;
- timed with A/Start skip.

Select returns to the menu without starting playback. The image is unrestricted, allowing control instructions, warnings, episode artwork, or branding.

## Description page

Select on a highlighted menu entry opens its description. The page consists of:

- custom 240×160 background image;
- converter-rendered title and wrapped body text;
- configurable text rectangle, font, alignment, colour, and optional panel;
- A to continue to the pre-play screen/playback;
- B or Select to return to the episode menu;
- independent enabled toggle per episode.

## Storage representation

Full-screen RGB332 requires 38,400 bytes raw. Images are compiled to `GLI1` using whichever is smaller:

- raw RGB332;
- row-aware RLE8;
- solid/gradient description when applicable.

Global splash metadata is stored in an extended theme block. Per-episode directory reserved fields point to a `GLE1` extras record containing description and pre-play assets.

Worst case for three splashes plus four pre-play and four description backgrounds is 422,400 raw bytes before text and metadata. This is feasible but exceeds the previous completed album's 42,608-byte margin. The converter must therefore subtract the exact compiled UI asset size before assigning episode video budgets. A future default reserve of approximately 1 MiB is appropriate for image-heavy themes.

## Compatibility

Albums without extended-screen flags retain current behavior. The existing menu, playback controls, overlays, and video codec remain unchanged.
