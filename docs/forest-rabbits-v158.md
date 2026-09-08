# Forest rabbit packs — v158

Historical v158 implementation record. v167 adds six runtime fur palettes and
retains the later **+1 carrot per rabbit / zero per mouse** reward policy.
See `forest-pets-rabbits-v167.md` for current behavior and verification.

## Included behavior

Both requested packs are real source sprite sheets, not generated replacements.
Successfully loaded packs alternate on rabbit encounters (mouse encounters stay
unchanged). Bunbun uses idle, upward/forward/front/back jumps, rear-leg kick,
sleep, and dig/emerge. Last tick uses all 219 non-empty cells: eight-direction
poses and hops, resting/breathing poses, head-lowering, looking around, upright
bobbing, ear flicks, and head-tilt/groom-like actions.

Movement runs only for travel actions, using the direction drawn in the source.
Diagonal movement is normalized. Resting/digging/kicking never slide along the
ground, blocked travel pauses, and source jump displacement is not duplicated by
an extra bounce or body deformation. Reduced-motion mode holds the first frame.
The finite sequence fits within the encounter's extended maximum 45 seconds;
catching or a scene change can interrupt it normally. Hover/click attack, +5
carrot reward, pet catches, and event deduplication retain their existing paths.

## Install licensed art locally

From the repository root in PowerShell:

```powershell
.\scripts\import_forest_rabbits.ps1 -Download
```

This uses the creators' public free-download flow. It does not log in, pay, supply
an email, or use saved browser cookies. It stops if file selection changes.
Alternatively download the two ZIPs manually from the official pages and run:

```powershell
.\scripts\import_forest_rabbits.ps1 -BunbunZip 'path\Bunbun.zip' -LastTickZip 'path\Bunny.zip'
```

Only the exact named PNG from each archive is extracted to a fixed destination;
PNG signature and dimensions are checked. No archive scripts are executed.
Original PNGs, ZIPs, and analysis exports are not checked into Git because the
licenses prohibit standalone redistribution. Developers/deployment maintainers
must install these assets independently and include them only with the game.
Without the optional files the existing credited LPC rabbit is the safe fallback.

Sources and full attribution are in
`src/frontend/assets/animals/ATTRIBUTION.md`. Always recheck creator terms before
reusing the art outside this game.

## Source mapping and validation

`ForestAnimals.rabbitAssets` records the 4-column Bunbun and 11-column Last tick
layouts. `rabbitVariants`, `rabbitAction`, and `rabbitPose` are shared by Phaser
and the motion-review page. `frameRect` supports both layouts without touching
the existing cow/LPC APIs. Runtime timings and descriptive Last tick labels are
our own; its ASEPRITE is one canvas without animation tags, not 374 timed frames.

- Bunbun: 8 actions, 18 rabbit cells; skip empty cells and carrot-only cells 19/23.
- Last tick: 46 groups (14 static poses + 32 animated groups), 219 occupied cells.
- New unit tests cover exact coverage, bounds, direction, timings, reduced
  motion, all-action sequencing, movement/standstill, texture fallback, hit-area
  resizing, rewards, and pet catches without requiring restricted source PNGs.
- In-game review: `/forest?bunnies=v158`.
- Side-by-side motion review: `/static/forest-rabbit-review-v158.html`.
- HTML/service worker versions change together so installed apps load the new
  behavior. Optional media failures never prevent the core app from installing.

## Verification (2026-09-08)

- Full forest Node suite: 182 passed; Python forest suite: 56 passed.
- Official download installer verified in both local-ZIP and public-download
  modes; the installed PNGs match the source dimensions and unchanged bytes.
- Live local server health: OK. Browser loaded the new script versions with no
  warning/error logs. Both original sheets render in the review page; selecting
  digging/ear-flick actions and pause/resume work. A Bunbun encounter and the
  existing +5 reward were observed in the game. Exhaustive actions, both species
  and click/pet attack paths are additionally verified by the integration tests.
