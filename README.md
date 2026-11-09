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
cooking list. It is read-only: it never writes to the save or to the game, and
it does not read game memory. The map marker moves when the game writes a save.

Build the companion data once, and again after a game update:

```bash
python3 build_companion_data.py /path/to/TotK
```

The build reads the port's `romfs` and writes `ui/companion_data/` with icons,
map layers, text and the catalog. Those files come from your own copy of the
game and are gitignored. The collectible coordinates are the only pre-computed
input, documented in `data/NOTICE.md`.

Run it from the repository root:

```bash
./totk-companion.sh --game /path/to/TotK --poll 15
```

`--check` prints the save, heart, rupee, inventory, completion and compendium
counts without opening the window. `--poll N` sets the save scan interval in
seconds (default 15).

The map has Surface, Sky and Depths layers. It uses the game's own marker
icons, a small overview inset, and a player layer based on Link's height
rather than the pause map's last viewed layer. Layer and marker filters are in
the left pane. Click a marker for its name, position and distance from Link,
or use **Near Link** on the right to see the closest collectibles first. Show
all or hide all marker categories from the left pane.
Completion lists every tracked category and can show only missing entries.
The armor page shows every set, the owned level, and the materials needed for
the next upgrade. Upgrade materials and material details have a **Sources**
action: it lists shops with prices and stock, enemy drops with their spawn
counts, and world spawns, then can pin those places on the map. Shops come from
the actor packs' ShopParam data, drops from the enemy DropTable and horn mapping
data, and spawns from the Banc map placements, all from your own game files.

Each tab remembers its filters and view choices across restarts. Companion
shortcuts: `/` focuses the active filter, `1` to `7` switch sections, `r`
refreshes, and Esc clears a filter or closes settings. The save slot is chosen
in Settings; Auto follows the newest save.

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
