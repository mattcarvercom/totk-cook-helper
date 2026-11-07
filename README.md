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

## Controls

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

## Limits

Hearts and durations are estimates. Critical cooks, Monster Extract and effect levels are not modelled. A port update
that changes the game's memory layout can break the live read. The helper then falls back to the save file.

## Credits

The cooking rules and duration formula follow
[KingFooZQ/Totk-Cooking-Simulator](https://github.com/KingFooZQ/Totk-Cooking-Simulator) (MIT). The save layout follows
[marcrobledo/savegame-editors](https://github.com/marcrobledo/savegame-editors). The font is Alegreya Sans (SIL Open
Font License, `ui\fonts\OFL.txt`).

MIT license.
