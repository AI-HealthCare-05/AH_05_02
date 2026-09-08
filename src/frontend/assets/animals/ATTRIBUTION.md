# Forest animal assets

Downloaded 2026-09-07 from the original publicly licensed sources. PNG and MP3 bytes are unchanged; local filenames are renamed. Frame selection and display scaling happen only at runtime. No generated animal art, background removal, or grass platform is used.

## Cow sprites

- Title: **LPC style farm animals**
- Creator: **Daniel Eddeland (daneeklu)**, commissioned by tebruno99.
- Source: <https://opengameart.org/content/lpc-style-farm-animals>
- Selected license: **Creative Commons Attribution 3.0 Unported (CC BY 3.0)**, offered by the creator as an alternative to GPL 2.0.
- License: <https://creativecommons.org/licenses/by/3.0/>
- Legal text: <https://creativecommons.org/licenses/by/3.0/legalcode>
- `lpc-cow-eat.png`: <https://opengameart.org/sites/default/files/cow_eat.png>
- `lpc-cow-walk.png`: <https://opengameart.org/sites/default/files/cow_walk.png>
- Required credit: Daniel Eddeland, with a link to the source submission. The author does not endorse this project.

Both sheets are 512 × 512, using 128 × 128 cells, four columns and four direction rows: up, left, down, right. The eating sheet provides a genuine head-lowering/muzzle animation while the legs stay planted; play forward and then backward for a finite touch reaction.

## Rabbit sprites

- Title: **Reorganised LPC rabbit**, based on **Bunny Rabbit LPC style for PixelFarm**.
- Original art: **Stephen Challener (Redshrike)**, commissioned by **Tebruno99** for **PixelFarm**.
- Reorganisation: **Evert** (the uploader states no additional credit is needed for the reorganisation; credited here nonetheless).
- Source: <https://opengameart.org/content/reorganised-lpc-rabbit>
- Original source: <https://opengameart.org/content/bunny-rabbit-lpc-style-for-pixelfarm>
- PixelFarm: <https://bitbucket.org/tebruno99/pixelfarm>
- Selected license: **Creative Commons Attribution 3.0 Unported (CC BY 3.0)**, one of the offered alternative licenses.
- License: <https://creativecommons.org/licenses/by/3.0/>
- Legal text: <https://creativecommons.org/licenses/by/3.0/legalcode>
- `lpc-rabbit.png`: <https://opengameart.org/sites/default/files/rabbit_2.png>
- Credit: Stephen Challener (Redshrike), commissioned by Tebruno99 for PixelFarm, hosted by OpenGameArt.org; sheet reorganised by Evert. No endorsement is implied.

The sheet is 288 × 576, with 72 × 72 cells and four columns. Rows 0–3 are hopping in up, left, down, right order. Rows 4–7 are grazing in the same order. The source already offsets the body during its hop, so no artificial body stretch is applied.

## Cow sound

- Title: **Cow Moos #6**, sound number 2386.
- Creator: **Joseph SARDIN – BigSoundBank.com**.
- Source and explicit license: <https://bigsoundbank.com/cow-moos-6-s2386.html>
- License: **CC0 1.0 Universal / public-domain dedication**.
- License explanation: <https://bigsoundbank.com/licenses.html>
- CC0: <https://creativecommons.org/publicdomain/zero/1.0/>
- `cow-moo-joseph-sardin-cc0.mp3`: <https://bigsoundbank.com/UPLOAD/mp3/2386.mp3>
- A recorded real cow, not a synthesized beep or a spoken imitation. Attribution is optional under CC0 and is retained here voluntarily.

The sound plays only after a user interaction and respects the caller's sound-enabled preference. No autoplay or account/payment was required to obtain any asset.

## Optional Bunbun / Last tick packs (2026-09-08)

- **Bunbun**, by **Evildumpling**: <https://evildumpling.itch.io/bunbun>.
  Creator's free-use license permits commercial and non-commercial games and
  editing, but prohibits redistribution/resale of the assets or their parts as
  standalone assets. Credit is optional; retained here voluntarily.
- **32x32 Pixel Bunnies – Animated NPC**, by **Last tick**:
  <https://last-tick.itch.io/32x32-pixel-bunnies-animated-npc>.
  Creator's free-use terms permit commercial/non-commercial projects and
  modifications, but prohibit redistribution/resale or repackaging as standalone
  assets. Credit is optional; retained here voluntarily.

These are custom creator licenses, **not CC0 or LPC licenses**. The original PNGs
and ZIPs are deliberately excluded from public Git. Obtain them from the creators
using `scripts/import_forest_rabbits.ps1`; see `docs/forest-rabbits-v158.md`.
Do not publish the original sheets, archives, or an asset-download gallery.
Distribution is only as part of the game under the respective creator's terms.

Local game files are byte-identical PNGs: `licensed-rabbits/bunbun.png` (128×256)
and `licensed-rabbits/last-tick.png` (352×1088). Both use 32×32 runtime cells.
Bunbun contains 18 rabbit poses in eight advertised actions; ancillary carrot
tiles 19 and 23 are not rabbit frames. Last tick contains 219 populated cells;
the game's 46 groups include 14 static directional/rest poses and 32 animated
groups. Names and timing are application-authored visual interpretations, not
official animation tags. Each pack has one original colorway. Palette swatches
and the numbered index guide are not additional skins or gameplay sheets.
