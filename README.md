py -m http.server 8000 in the folder and enter http://localhost:8000/mars\_mission\_control.html to the browser

Famous locations (FAMOUS LOCATIONS 3D button, or TRAVEL on a site) open `locations3d.html`: real NASA MOLA terrain from `3d map/sites/*.js`.
To add or change a location, edit the list in `3d map/fetch_sites.py` and run `py "3d map/fetch_sites.py"`. The script also writes `3d map/water.js`, the Mars Odyssey soil-water map.

## Mission planning in the 3D game

While walking (`locations3d.html`):

- **B** sets a **base camp** where you stand. The HUD then shows how far it is and whether your O₂ still covers the walk back with a 50% reserve. The walk back follows the fastest walkable route over the real MOLA terrain, around slopes of 32° or more, and is drawn dashed on the minimap (**GO / TURN BACK / NO RETURN**). This is the walk-back limit Apollo crews planned by. Dust storms triple O₂ use, so a storm can turn GO into TURN BACK. Standing at base refills O₂ and battery.
- **P** (or **Mission Plan** in the pause menu) opens the mission plan:
  - radiation dose here and for the whole mission
  - today's real radio delay to Earth, with a solar conjunction warning
  - this site's dust season, from real storms seen from orbit between 1999 and 2015
  - every location ranked as a first human base against NASA's landing limits (latitude within ±50°, below +2 km). Water is the real soil H₂O measured by Mars Odyssey's gamma-ray spectrometer
- The **EARTH** pill in the top bar shows the current one-way light delay.

## Download and play from GitHub

1. **Get the files**
   - Easiest: open https://github.com/Saidjalolkhon/NASA-Space-Apps-Challenge-2026-SATashkent, click the green **Code** button, then **Download ZIP**, and unzip it anywhere.
   - Or with git: `git clone https://github.com/Saidjalolkhon/NASA-Space-Apps-Challenge-2026-SATashkent.git`
2. **Install Python 3** if you don't have it (https://www.python.org/downloads/). On Windows, tick *Add Python to PATH* during setup. Python is only used to serve the files locally. Browsers block pages opened straight from disk from loading the terrain and 3D models.
3. **Start a local server** in the unzipped folder (the one containing `mars_mission_control.html`):
   - Windows: open the folder, type `cmd` in the address bar, press Enter, then run `py -m http.server 8000`
   - macOS / Linux: `cd` into the folder in a terminal and run `python3 -m http.server 8000`
4. **Open** http://localhost:8000/mars_mission_control.html in Chrome, Edge or Firefox. Click **OUTLAND** or **FAMOUS LOCATIONS 3D** to walk on Mars. To go straight into the 3D game, open http://localhost:8000/locations3d.html
5. Keep the terminal window open while you play. Press `Ctrl+C` in it to stop.

You need an internet connection: Three.js and the fonts load from public CDNs.

**Controls:** WASD / arrows move · Shift sprint · Space jump · mouse look (click to capture) · E environment scan · L locations · B base camp · P mission plan · F flashlight · M minimap zoom · Esc pause. Touch screens get a joystick and a jump button.

**Troubleshooting**
- *Blank page or "NO TERRAIN DATA"*: you opened the file directly. Use the `http://localhost:8000/...` address from step 4.
- *Changes don't show up after an update*: the browser is using its cached copy. Press `Ctrl+Shift+R` (macOS: `Cmd+Shift+R`) on the page, or open DevTools (F12), tick *Network → Disable cache*, and reload.
- *Port 8000 in use*: use another port, for example `py -m http.server 8080`, and change the address to match.
- *Slow or choppy*: close other tabs, and use a browser with hardware acceleration turned on.
