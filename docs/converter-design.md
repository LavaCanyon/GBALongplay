# Portable offline converter design

## First platform

Linux desktop first, with architecture kept portable to Windows and macOS.

## Distribution model

The end user should not install Python, FFmpeg, scikit-learn, devkitARM, or a GBA compiler.

The portable package contains:

- desktop converter executable and GUI;
- bundled FFmpeg/FFprobe;
- VQ training and GLV encoder runtime;
- precompiled GBA bootstrap and EWRAM player runtime templates;
- ROM packer and header fixer;
- built-in menu themes and fonts;
- offline help.

The GBA player is compiled by the project maintainer. The converter inserts a generated GLA1 album and theme into precompiled ROM templates, so end users do not need an ARM toolchain.

## Workflow

1. Add one to four local video files.
2. Edit titles and reorder episodes.
3. Choose total cartridge size/runtime profile.
4. Select or customize a menu theme.
5. Pick thumbnail frames or import thumbnail art.
6. Preview the 240×160 menu and action overlays.
7. Run VQ training and episode encoding locally.
8. Review size, quality estimates, and warnings.
9. Build a `.gba` ROM entirely offline.
10. Optionally save the project and reusable theme.

## Theme system

Friendly controls cover common customization:

- template/layout;
- background image or flat/gradient colour;
- logo image and placement;
- title font, size, and colours;
- selected/unselected row colours;
- thumbnail position, size, border, and background;
- menu margins and spacing;
- help/footer text;
- overlay position, foreground, background, and border;
- action-message duration;
- brightness/contrast default levels.

An advanced JSON editor exposes the complete theme. Themes can be exported as a folder or a `.glptheme` bundle.

## Runtime theme asset

A `GLT1` block is stored in the album before episode media. Proposed contents:

- version and CRC;
- 240×160 RGB332 background bitmap or compact solid/gradient description;
- optional logo bitmap with transparent index;
- 1-bit font glyph atlas and character metrics;
- layout coordinates;
- UI colours;
- thumbnail-frame bitmap or nine-slice parameters;
- overlay panel bitmap/colours;
- string table for action messages.

The player keeps menu behavior fixed and data-driven. This prevents arbitrary themes from breaking playback or requiring a newly compiled runtime.

## Live preview

The editor renders the exact GBA RGB332 image at native 240×160 and at integer zoom levels. Preview modes:

- episode menu;
- selected and unselected rows;
- each thumbnail;
- Paused/Resuming;
- Rewinding/Forwarding;
- Chapter number;
- Buttons Locked/Unlocked;
- Brightness/Contrast messages;
- colour-adjustment simulation.

## Initial implementation sequence

1. Freeze `GLT1` theme schema.
2. Refactor the hard-coded C menu/OSD renderer to consume `GLT1`.
3. Add a command-line theme compiler and PNG-to-RGB332 conversion.
4. Add built-in Majesco-like, minimal, and image-heavy templates.
5. Build a Linux GUI around the existing encoder and packer.
6. ~~Replace build-time ARM compilation with checksummed precompiled runtime templates.~~
7. Add native low-spec desktop styling and file dialogs.
8. Package as an offline AppImage/portable folder.
