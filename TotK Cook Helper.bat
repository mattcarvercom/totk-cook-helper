@echo off
rem Starts the cook helper window without a console. The first run builds the dish data and icons from the game.
cd /d "%~dp0"
if not exist cookdata.json py -3 -E build_data.py
if not exist ui\icons\index.json py -3 -E build_icons.py
start "" pyw -3 -E cook_helper.pyw
