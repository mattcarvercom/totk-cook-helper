# TotK Cook Helper

A small window that sits beside the TotK PC recomp port (built and tested against release 0.3.12, game v1.4.3) and
lists every dish your current materials can make, with what to put in the pot, the hearts it restores and its effect.
It looks like the game's inventory menu and uses the game's own item and dish icons.

It ships no game files. The dish data and the icons are built on your machine from your own copy of the game.

## Install

1. Put this folder next to the port's `game` folder, so the layout is `<port>\game\romfs` and `<port>\cook-helper`.
2. Install Python 3.10 or later from python.org, with the `py` launcher. Windows 11 already has the WebView2 runtime
   the window needs.
3. Install the packages:

   ```bat
   py -3 -m pip install --user pywebview backports.zstd texture2ddecoder pillow
   ```

4. Run `TotK Cook Helper.bat`. The first run reads the game's romfs to build `cookdata.json` (a few seconds) and the
   icons (about two minutes), then opens the window.
5. Optional: `py -3 install_autostart.py` adds a Startup-folder shortcut, so the helper opens whenever the game
   starts and closes when it exits. `py -3 install_autostart.py remove` takes it out again.
6. Optional: to stop the controller from also moving Link while you browse the helper, download `SDL3.dll` from the
   latest release into the `padblock` folder, close the game and run `py -3 padblock\padblock.py install`. The
   section "Controller while the helper is in front" explains what it does.

## Use

Start it with `TotK Cook Helper.bat`. While the game runs, the helper reads your material pouch from the game's
memory twice a second, so the list changes as you pick things up, cook or sell, without waiting for a save. The status
line says "Live from the game" when this is working.

The first read after the game starts takes 10 to 20 seconds, because the helper searches the game's memory for the
pouch; the status line says "finding the pouch in the game" meanwhile. Until then, and whenever the game isn't running
or the search fails, the helper falls back to the newest `progress.sav` under `..\game\profile\save` and reloads it
within two seconds of each save. On the title screen, before a save is loaded, the search finds nothing and tries
again every 30 seconds. It needs one save on disk to know the size of the pouch.

## The window

Dishes and Materials are two tabs, switched with LB and RB, Q and E, or a click. The cursor moves with the arrow keys
or the D-pad, and the pane on the right shows the selected item. Click an ingredient in a dish to jump to it under
Materials, or a dish under "Used in" to jump back. Type `/` or Ctrl+F to filter by name, effect or ingredient. Esc
clears the filter, then closes settings, then hides the window.

On the Dishes tab a row of effect buttons narrows the list to one effect (Cold Resistance, Speed Up, No effect and so
on, each with how many dishes have it). Click the active one or All to show everything again. Sort orders the dishes
by hearts (hearty dishes first), effect time, name or effect. Press F or the controller's Y to step through the
effects and S or X to step through the sort orders. The helper remembers both.

Drag the top bar to move the window and any edge to resize it. It remembers its place on screen.

## Show and hide

Hold both sticks (LS + RS) for 0.3 s on the controller, or press Ctrl+Shift+C, to hide the window or bring it back.
If the game is covering the window, the same press brings it to the front instead of hiding it. The gear button opens the settings, where you can change both:

- Controller combo: record a new one by holding the buttons, or pick them from a list. The Guide button works and
  never reaches the game. Other buttons still reach the game, so clicking both sticks makes Link crouch for a moment.
- Hold time: tap, 0.3 s, 0.6 s or 1 s.
- Keyboard hotkey: click the key cap and press the new combination.
- When hidden: Minimize keeps the window in Alt-Tab and the taskbar, so Alt-Tab also brings it back. Hide fully
  removes it from both until the combo or hotkey shows it again.
- Take focus when shown: on by default. The window takes the focus when the combo or hotkey shows it, so the pad
  moves the helper's cursor and the game ignores it until the helper hides again. Turn it off to keep playing while
  the window is up.
- Always on top, which keeps it over the game in borderless fullscreen.
- Monitor: click a screen to move the window there. With a second monitor, leave the game on one and the helper on
  the other and switch with Alt-Tab.
- Start hidden: opens minimized when the game starts, ready for the combo.
- Navigate with the pad: while the helper has focus, the D-pad moves the cursor, LB and RB switch tabs, Y and X
  change the effect filter and the sort, and B hides it.

The controller is read through XInput, so Xbox pads work directly. PlayStation and Switch pads need Steam Input or
another XInput layer. Settings live in `settings.json` next to the script.

Starting the helper a second time shows the window that is already open.

## Controller while the helper is in front

While the helper window has the focus, the game ignores the controller, so moving through the helper with the pad
doesn't also move Link. The game goes back to reading it as soon as its own window is in front again. The keyboard
needs nothing extra, because the game already ignores it while another window is in front.

The game draws its own window and uses SDL only to read the pad, so SDL keeps passing the pad through when the game
loses focus. `padblock\SDL3.dll` is a small replacement for the game's `SDL3.dll`. The real one is renamed
`SDL3_orig.dll`, and the replacement forwards every SDL function to it unchanged except the three the game reads the
pad with. While the window in front is titled "TotK Cook Helper", those report no buttons, centred sticks and no gyro
motion.

Install it once with the game closed, as step 6 under Install describes. After that the auto-start watcher puts it
back whenever the game is closed, including after a port update brings back a plain `SDL3.dll`. If an update brings an SDL with functions the replacement doesn't forward, the watcher leaves the
new DLL alone and writes a line to `autostart_watch.log`. Then run `py -3 padblock\padblock.py build` (it needs clang,
lld-link and the Windows SDK) and close the game once. To take it out, close the game and run
`py -3 padblock\padblock.py uninstall`. That removes `SDL3_orig.dll`, and the watcher only puts the replacement back
where it finds that file.

## Auto-start

`install_autostart.py` puts the shortcut `TotK Cook Helper watcher` in the Windows Startup folder (`shell:startup`),
which runs `autostart_watch.pyw` at sign-in. The watcher checks every 3 seconds whether `totk.exe` is running and
opens the helper when the game starts, however the game was launched. Close the helper by hand and it stays closed
until the next game start. `autostart_watch.log` lists each start.

The helper closes itself within about two seconds of the game exiting, including a helper you opened yourself. If you
open it while the game isn't running, it closes only after the game has started and exited.

## How it works

`build_data.py` reads the game's own files out of `..\game\romfs\romfs.bin`: the recipe table
(`Cooking/CookingTable`), the ingredient tags (`RSDB/Tag`), each ingredient's hearts, effect and duration (its actor
pack's `CureParam`) and the English names (`Mals/USen`). It writes `cookdata.json`.

`build_icons.py` decodes the item textures under `UI/Tex/Icon` (ASTC, Tegra block-linear) and writes them to
`ui\icons` as 128 px WebP files, with `ui\icons\index.json` mapping each actor to its icon. It takes about two minutes
and needs `py -3 -m pip install --user texture2ddecoder pillow`. A handful of materials have no icon in the game and
fall back to a drawn symbol. The icons come from your copy of the game, so don't share the `ui\icons` folder.

Run both scripts again only if the romfs changes, which a port update does not do.

`livemem.py` does the live read. It looks through the game's writable memory for the two arrays the save stores as
`Pouch.Material.Content.Name` and `Pouch.Material.Content.StockNum`. Each sits behind a small descriptor that holds the
array length twice, and the names are 64-byte strings that each point at their own text. It accepts a name array only
if its entries are known materials, and a count array only if it is -1 exactly where a name is empty. It only reads;
it never writes to the game. The layout was worked out against the PC port as of November 2026 and may need another
look if a port update changes how it lays out memory.

`cook_core.py` reads the material pouch from the save and tries each recipe with the ingredients you own. The game
takes the first recipe in table order whose ingredient slots are each filled by a different kind of ingredient, so
the helper checks that the pot it suggests really ends in that dish and not Dubious Food or another recipe higher in
the table. Each dish is shown once, with the pot that gives the strongest effect and then the most hearts, filled to
five ingredients from your stock. `py -3 cook_core.py` prints the same list in a console.

The matching rules and the duration formula follow
[KingFooZQ/Totk-Cooking-Simulator](https://github.com/KingFooZQ/Totk-Cooking-Simulator) (MIT). The save layout
follows [marcrobledo/savegame-editors](https://github.com/marcrobledo/savegame-editors). The interface font is
Alegreya Sans (SIL Open Font License, `ui\fonts\OFL.txt`).

## Limits

Hearts and durations are estimates. Critical cooks, Monster Extract and effect levels (the number of arrows) are not
modelled. Only the material pouch is read; it never writes to the save or to the game's memory.
