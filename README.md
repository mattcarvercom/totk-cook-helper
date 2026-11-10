# TotK Cook Helper

A window for the TotK PC recomp that lists every dish your materials can make: the ingredients, hearts and effect. It
reads your material pouch live from the game's memory, so the list updates as you play. It reads the game's memory
and saves but never writes to them.

Tested with recomp release 0.3.12 (game v1.4.3) on Windows 11. No game files are included. The dish data and icons are
built on your machine from your copy of the game.

## Install

Run these in Command Prompt. Replace `C:\Games\TotK` with the folder that holds the port's `game` folder.

1. Install Python and Git if you don't have them:

   ```bat
   winget install Python.Python.3.12
   winget install Git.Git
   ```

   Open a new Command Prompt afterwards so both are on the PATH.

2. Clone the helper next to the `game` folder:

   ```bat
   cd /d C:\Games\TotK
   git clone https://github.com/shin2344234/totk-cook-helper.git cook-helper
   cd cook-helper
   ```

3. Install the Python packages:

   ```bat
   py -3 -m pip install --user pywebview backports.zstd texture2ddecoder pillow
   ```

4. Start it. The first run builds the dish data and icons from the game, which takes about two minutes:

   ```bat
   "TotK Cook Helper.bat"
   ```

5. Optional. Open the helper when the game starts and close it when the game exits:

   ```bat
   py -3 install_autostart.py
   ```

6. Optional. Stop the controller from moving Link while the helper has focus. Close the game first:

   ```bat
   curl -L -o padblock\SDL3.dll https://github.com/shin2344234/totk-cook-helper/releases/latest/download/SDL3.dll
   py -3 padblock\padblock.py install
   ```

To update, run `git pull` in the `cook-helper` folder.

## Linux (save mode)

The Linux helper reads the newest save file. It does not read game memory, block
controller input, or register a global hotkey. Leave it open while playing and it
refreshes when the game saves. It needs Python 3.12+ and pywebview with a GTK
WebKit2 backend.

System packages:

- Arch: `python-gobject`, `webkit2gtk-4.1`
- Ubuntu/Debian: `python3-gi`, `gir1.2-webkit2-4.1`

From the helper folder:

```bash
python3 -m venv --system-site-packages .venv
. .venv/bin/activate
pip install -r requirements-linux.txt
python build_data.py /path/to/TotK
python build_icons.py /path/to/TotK
./totk-cook-helper.sh --game /path/to/TotK --poll 15
```

`/path/to/TotK` is the recomp install folder, the one with `romfs/` and `profile/`.
Pass it with `--game`; without `--game`, the helper looks for `../game`.
The data and icon builds read your own game files and write `cookdata.json` and
`ui/icons/`, both gitignored. `python cook_helper_linux.py --check` prints the
save slot, material count, and dish count without opening the window.

`--poll N` sets the scan interval in seconds (default 15). The status line shows a
spinner while a save is being read, the slot it loaded, how long ago it was saved,
and the countdown to the next scan. Icons are preloaded after the first payload,
so later refreshes reuse them. The controller-only LB/RB pills are hidden.

A save refresh keeps the selected tab, search, effect and sort filters, selected
recipe and scroll position. If the selected recipe is no longer craftable, it
stays in the detail pane, dimmed, with the missing ingredients listed. Pick
another recipe or gather the ingredients again.

This mode has no controller combo and no global hotkey. Use the window's own
minimize and close buttons.

## Linux companion

The companion is a separate window built from the same game files. It reads the
newest save and shows Link's status, the full pouch, armor and upgrade
materials, the map, collectible completion, the Hyrule Compendium and the
cooking list. It is read-only: it never writes to the save or to the game.

When the companion launches TotK itself, it also reads the game's live player
actor and updates Link's map position and facing several times per second. It
reads the game's in-memory progress buffer every two seconds, so hearts,
stamina, rupees, equipment, inventory, armor, completion, compendium, cooking,
and travel medallions follow the running game instead of waiting for a save.
The selected save file still supplies the save caption, Hero's Path, and the
fallback when live memory is unavailable. If TotK was started another way, the
companion stays in save-file mode and the map marker moves when the game saves.
Use **Settings > Launch TotK** or start the companion with `--launch-game`;
this needs no sudo and no ptrace changes because the game is the companion's
child process.

Build the companion data once, and again after a game update:

```bash
python3 build_companion_data.py /path/to/TotK
```

The build reads the port's `romfs` and writes `ui/companion_data/` with icons,
map layers, display-sized map copies, terrain height samples, reveal regions,
text and the catalog. Those files come from your own copy of the game and are
gitignored. The collectible coordinates and the map region polygons are the
only pre-computed inputs, documented in `data/NOTICE.md`.

Run it from the repository root:

```bash
./totk-companion.sh --game /path/to/TotK --poll 15
./totk-companion.sh --game /path/to/TotK --launch-game
```

`--check` prints the save, heart, rupee, inventory, completion and compendium
counts without opening the window. `--poll N` sets the save scan interval in
seconds (default 15). `--launch-game` starts TotK as the companion's child so
live position and facing work. The `launch-totk` wrapper does this
automatically when it starts the companion.

The map has Surface, Sky and Depths layers. It uses the game's own marker
icons, a small overview inset, and a player layer based on Link's height
rather than the pause map's last viewed layer. Layer buttons, marker filters,
search, the reveal checkbox, and the place-label toggle are in the left pane;
zoom buttons float on the map. Villages, stables, Great Fairies, tech labs, shops, Dragon's Tears, device
dispensers, challenges, temples and landmarks are separate map layers, each with
its game marker art, including the shrine gate, lightroot bulb, player arrow,
and a per-temple icon for the six dungeons, including Hyrule Castle. Temples
sit directly below Skyview Towers in the layer list. Chasm mouths appear on
both the Surface and Depths maps. Treasure chests, Large Zonaite deposits,
cooking pots, Goddess statues, Bargainer statues, cherry trees, Lynels, Gloom
Spawn and dungeon bosses are generated at build time from the game's Banc actor
placements. The chest layer is generic: it names the chest type and position
but not the randomized contents. Malanya Spring is the fifth Great Fairy and
Forge Constructs complete the shop layer in the Depths and sky.
Marker images are trimmed to their visible bounds so small icons such as wells
use the same size on the map. The layer list is a two-column grid when the pane
is wide enough and collapses to one scrolling column when it is narrow. It runs
from fast travel and major places down to collectibles instead of sorting by
marker count. Search is limited to the selected layers and markers by default;
**Search all** expands it to every layer, marker, and place label. Results are
stacked under headers for exact and fuzzy matches, split into POI labels,
place labels, and other markers. Clicking a place label centers the map on it. Found/Missing applies to every tracked marker layer, including shrines,
towers, lightroots, and place layers with complete discovery data: villages,
stables, Great Fairies, Dragon's Tears, and device dispensers. All and Found
show found/total; Missing shows missing/total and draws only the missing
markers. A tracked category with no matching markers drops out of the layer
list. Places without full discovery data, such as temples, shops, tech labs,
and challenges, show their total and stay visible in every view. **Link**
centers without changing the zoom, and at fit zoom it only
pings the marker because the whole map is already visible. **Follow** keeps
Link centered while the game updates his live position; changing the zoom
keeps him centered, and panning, **Fit**, a manual layer change, or a marker
jump stops following. Follow stays armed through loading screens, menus, and
chasm transitions and resumes when live memory returns. Follow is only
available with live memory and the button says so when the companion is in
save-file mode. The map stays on the layer
you choose; turn on Follow if you want it to switch with Link when he fast
travels between the Surface, Sky, and Depths. The ping fades out
smoothly instead of blinking off. Hovering a marker switches the cursor to a
pointer and shows its name, layer, and state; place and fast travel names also
appear as labels when you zoom in. Named regions, lakes, mountains, forests,
ruins, and other locations from the game's LocationArea data appear as
free-floating labels above the map tiles and below markers. Region labels show
at fit zoom; zone, area, and detail labels fade in as you zoom. **Place labels**
in the left pane toggles them; **POI labels** toggles the names attached to
markers such as shrines, towers, stables, and wells. **Reveal full map**
is off by default, so the map starts with the
terrain you have revealed in the game. The fog only covers terrain; markers
remain visible over unexplored areas. The Sky layer draws the Hyrule base,
translucent clouds, then the sky islands on top so the islands stay clear.
Surface and Sky use the Skyview Tower region boundaries, and the Depths reveal
the Field Map Area around each activated Lightroot, so the shapes are regions
rather than circles. Travel
Medallions have their own toggle in the left pane, appear only on their layer,
and use the game's medallion art without a background plate. A newly placed
medallion appears as soon as live memory sees it. **Hero's Path**
reads `footprint.sav` and draws the recorded trail and death marks for the
current layer, with a point and distance summary. The trail is cyan on the
Surface, gold in the Sky, and mint in the Depths. Link's green triangle points
in the direction Link faces in the save, using `PlayerStatus.SavePosRadY`. It
gives a short sonar ping when the Map tab opens, when the map switches to
Link's layer, or when **Link** is pressed. Three thick green rings start wide
and converge on Link instead of one ring expanding outward. The map cursor shows X, Y and Z in Purah Pad
order, using the game's terrain height grids for Z. Marker details and
**Near Link** or **Results** are on the right, with game-style X/Y/Z
coordinates and a direction arrow from Link. Empty detail or Nearby panels are
hidden instead of leaving a blank box. Map controls use a small vendored
Material Symbols set so the app never fetches icons from a CDN. Every tab with
a detail pane, plus both map sidebars, has a draggable divider; its grip
collapses or expands that pane. Pane widths and collapsed state persist across
restarts.
Completion lists every tracked category and can show only missing entries.
Clicking a completion row opens that place on the map. Armor shows a Ready or
Need badge on the grid. The detail puts the item description first, then the
piece effect and a compact set panel. The set panel separates stacked piece
effects from the set bonus and shows the piece-count formula, such as Stealth Up
Lv. 3 from three Lv. 1 pieces. Upgrades list only levels still ahead of
the current rank. Upgrade materials and material details have a **Sources**
action: it lists shops with prices and stock, enemy drops with their spawn
counts, and world spawns, then can pin
those places on the map. Shops come from the actor packs' ShopParam data,
drops from the enemy DropTable and horn mapping data, and spawns from the Banc
map placements, all from your own game files.

The status page combines hearts, stamina wheels, energy cells, combat totals,
sages, special powers, equipped gear, and active armor effects, using the
game's sage portraits and ability icons. The Link header shows the save-menu
screenshot from `caption.sav` and the full `progress.sav` path. Attack includes the fused material and
weapon modifier; Defense is the sum of the three worn pieces. Active Attack Up
also shows the adjusted value. Journey shows total playtime, deaths, distance,
and Hero's Path points from the save. Key item chips show Korok Seeds, Bubbul
Gems, and Light of Blessing. A pouch summary shows each bag's used and maximum
slots plus the next Hestu price for weapons, bows, and shields. Equipment,
material, attack, defense, pouch, and completion cards jump to the matching
inventory, armor, or progress view. Armor lives in its own tab rather than as
an Inventory category; the Inventory chips still include an Armor link, and an
Inventory search that matches armor offers to continue in the Armor tab.
Inventory opens on All, and category chips show their slot cap, such as
Weapons 12/12 or Materials 137/255. Choosing an equipment category also shows
the next Korok Seed cost, and the armor page shows owned pieces against its 150
slots. Armor opens with Owned only; armor with elemental or gloom resistance
shows the matching icon in its top-left corner. The set panel shows the combined
effect of wearing all pieces, the set's defense now, at Lv 2, and at max, and
the set bonus with its measured value. Set bonuses unlock when every piece
reaches Lv 2; Lv 3 and higher add defense only and do not strengthen the bonus.
Weapons, bows, and shields show a fusion badge and the fused item in their
details, including object fusions such as Rock, which uses a game texture
instead of a plus glyph. Equipment with 3 or less durability pulses red.
Cooking starts with dishes that the current pouch can make; **All recipes**
adds the full recipe table with required ingredient slots and marks entries the
pouch cannot cook yet. The dish detail shows the recovered portion of a stamina
wheel for Stamina Recovery recipes and a level-specific amount for effects such
as Stealth Up or Attack Up. When worn armor has the same effect, it also shows
the combined level with current gear. New installs start with spoiler-free
filters: Found map markers, photographed compendium entries, found progress
entries, and the map terrain limited to revealed areas.

Each tab remembers its filters and view choices across restarts. **Reset
filters** in Settings restores the spoiler-free defaults. Settings also chooses
the save slot and refresh interval, and includes **Rebuild now** to rebuild
icons, maps, and item data from the game files without running a script by hand.
**Check save now** only re-reads the save when its file time changed.
Companion shortcuts: `/` focuses the active filter, `1` to `7` switch sections,
`r` checks the save, and Esc clears a filter or closes settings. Auto follows
the newest save.

## Cook Helper controls

| Action | Controller | Keyboard |
| --- | --- | --- |
| Show or hide the window | Hold LS + RS | Ctrl+Shift+C |
| Switch Dishes and Materials | LB / RB | Q / E |
| Move the cursor | D-pad | Arrow keys |
| Cycle the effect filter | Y | F |
| Cycle the sort order | X | S |
| Search | | `/` or Ctrl+F |
| Hide | B | Esc (clears the search first) |

The combo, hotkey and hold time can be changed under the gear button. Other options there are always on top,
minimize or fully hide, take focus when shown, start hidden and which monitor to use. Settings are saved in
`settings.json`.

The controller is read through XInput. PlayStation and Switch pads need Steam Input or another XInput layer.

## Notes

The first live read after the game starts takes 10 to 20 seconds. Until then the helper uses your newest save in
`..\game\profile\save`. It needs at least one save on disk.

The controller block replaces the game's `SDL3.dll` with a wrapper and renames the real one to `SDL3_orig.dll`. While
the helper window has focus, the wrapper reports no input to the game. The auto-start watcher puts it back after a
port update replaces `SDL3.dll`. To remove it, close the game and run `py -3 padblock\padblock.py uninstall`.

To remove auto-start, run `py -3 install_autostart.py remove`.

Run `py -3 build_data.py` and `py -3 build_icons.py` again only if the game's romfs changes.

## Virus scans

Scanned on 6 November 2026.

| File | VirusTotal | Windows Defender |
| --- | --- | --- |
| Source, [v1.0.0.zip](https://github.com/shin2344234/totk-cook-helper/archive/refs/tags/v1.0.0.zip) | [No detections](https://www.virustotal.com/gui/file/841b81b16123105e28253b13b4c635c0ba11e045f8d6ab89579aaa4dc684ea8b) | No threats |
| [SDL3.dll](https://github.com/shin2344234/totk-cook-helper/releases/download/v1.0.0/SDL3.dll) from the release | [1 of 71](https://www.virustotal.com/gui/file/c8c1e6227635240bd2ac916dc8bf89525a4061dc236cd269e73df40588bb0bd1) | No threats |

The one detection is Cynet's machine-learning score. A DLL that takes the place of another and forwards its functions
to the renamed original matches what Cynet's model looks for, and that is exactly how the controller block works.
Every other engine reports it clean. The source is `padblock\padblock.c`, and `py -3 padblock\padblock.py build`
compiles it yourself if you'd rather not use the download.

SHA-256 of `SDL3.dll`: `c8c1e6227635240bd2ac916dc8bf89525a4061dc236cd269e73df40588bb0bd1`

## Limits

Hearts and durations are estimates. Critical cooks, Monster Extract and effect levels are not modelled. A port update
that changes the game's memory layout can break the live read. The helper then falls back to the save file.

The companion is read-only and covers status, inventory, armor, map, collectibles, the compendium and cooking. It does
not include the Adventure Log, Autobuild blueprints or live item actions; those need data or game hooks that the save
alone does not provide.

## Credits

The cooking rules and duration formula follow
[KingFooZQ/Totk-Cooking-Simulator](https://github.com/KingFooZQ/Totk-Cooking-Simulator) (MIT). The save layout follows
[marcrobledo/savegame-editors](https://github.com/marcrobledo/savegame-editors). The font is Alegreya Sans (SIL Open
Font License, `ui\fonts\OFL.txt`).

MIT license.
