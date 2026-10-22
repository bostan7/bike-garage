# design/

Design sources for the game UI. Nothing here is shipped as-is; the scripts produce files the app or a reviewer uses.

| Folder | What | Run |
|---|---|---|
| `prototype/` | The clickable landscape prototype of the garage UI (three.js + the real Draco bike model + the app's part list). It was approved before the Compose UI was built, and the Compose UI follows it. | `python design/prototype/make_prototype.py OUT_DIR` → `OUT_DIR/garage-prototype.html` (open it in a browser; needs `draco_decoder.js` from three@0.147.0 next to it) |
| `sounds/` | Synthesizes the UI sounds (whoosh, tick, confirm, hold, light-on) as small WAV files with the Python standard library only. No downloaded audio. | `python design/sounds/make_sounds.py` → `android/app/src/main/res/raw/*.wav` |
