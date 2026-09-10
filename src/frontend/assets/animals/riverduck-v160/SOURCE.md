# Riverduck v160 — original CC0 duck frames

- Asset: **Character - Spritesheet Duck**
- Author: **Ulti** (source attribution notice: **FINISAUTEMPOTENTIAE ©**)
- Author's distribution page: https://opengameart.org/content/character-spritesheet-duck
- Original archive: https://opengameart.org/sites/default/files/duck.zip
- License: **CC0 1.0 Universal**, explicitly selected on the distribution page.
- License reference: https://creativecommons.org/publicdomain/zero/1.0/
- Retrieved and visually inspected: **2026-09-08**.

These six PNG files are byte-for-byte copies of the original archive entries,
renamed only. No cropping, recoloring, pixel editing, or AI image generation was
applied. Redistribution is permitted under CC0. The credit above is retained
voluntarily for traceability.

## Frame layout

Every file is a transparent **96 × 96 PNG containing one frame**, not a multi-frame
atlas. Every pose faces right; mirror the renderer for left-facing movement.
The `swim` and `flee` filenames describe application behavior: the source calls
these animations **Walking** and **Running**. No water pixels were added.

| Runtime file | Original entry under `Duck/Sprites/` | Alpha bounds `(x, y, width, height)` |
| --- | --- | --- |
| `riverduck.png` | `Idle/Idle 001.png` | `(27, 48, 39, 48)` |
| `idle-2.png` | `Idle/Idle 002.png` | `(27, 45, 39, 51)` |
| `swim-1.png` | `Walking-Running/Walking 001.png` | `(27, 45, 39, 51)` |
| `swim-2.png` | `Walking-Running/Walking 002.png` | `(24, 45, 42, 51)` |
| `flee-1.png` | `Walking-Running/Running 001.png` | `(15, 45, 51, 51)` |
| `flee-2.png` | `Walking-Running/Running 002.png` | `(15, 45, 51, 51)` |

All alpha bounds fit the common source rectangle `(15, 45, 51, 51)`.
Use the same source rectangle and bottom-center anchor for every pose to prevent
movement or size jumps between frames. Use nearest-neighbor rendering.

Recommended loop order: idle `[riverduck.png, idle-2.png]`, moving
`[swim-1.png, swim-2.png]`, fleeing `[flee-1.png, flee-2.png]`.
Runtime animation speed is an application choice, not a claimed author setting.

## SHA-256

```text
05DEE668DC2B6EB139521ACE35A9161F1EF097C74874130A76D721F26A273C6A  riverduck.png
A4EAD16A38DB28BBE3D00C7FE151D766A718269CF661F358F2B05B1291C1B4F0  idle-2.png
336D95BAF2B7006EB5DCFDAA3373C893176EA83C8FB7931FC53AD7E935251667  swim-1.png
4EAE0CBB96705D74E8248AB564151E26841B0A46EF4A5B4BBD72DCA092A3B39A  swim-2.png
9BCC2B38B0C3E71855F9B797805EDE9FA9F371D3E7887A7BEDB875F916DF9532  flee-1.png
C2E4EBB9DDCFB7F5972E943EC79652B21D3CFCADA7247FD949A4949B790DD64E  flee-2.png
```
