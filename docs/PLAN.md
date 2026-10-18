# Scale 980 Garage — Plan

Personal Android app for **my 2022 Scott Scale 980 (size L, black)**, built only for the **Google Pixel 9 Pro** (portrait, ~412 dp wide, dark UI).

The look is a *Need for Speed*-style garage: the bike sits on a lit turntable in 3D. You pick a part and the camera flies to it. Each part is shown like a car upgrade card, with condition, stats, history and available upgrades.

---

## 1. Tech stack

| Layer | Choice | Why |
|---|---|---|
| Language / UI | Kotlin + Jetpack Compose (Material 3, custom "garage" theme) | Native, fast, and buildable from the command line and in Android Studio |
| 3D rendering | **SceneView** (Compose wrapper around Google **Filament**) | Real-time PBR lighting, loads `.glb` models, orbit camera, tap-to-pick parts. Lighter than Unity, and lives in the same app |
| 3D model | `.glb` (glTF) with **every part a separate, named node** (`fork`, `chain`, `brake_front`, …) | Each part can be selected, highlighted, hidden, recoloured or exploded on its own |
| Storage | One JSON file on the phone (kotlinx.serialization) + export/import backup | Simple and offline. Easy to back up to Google Drive |
| Photos | Android photo picker, copied into app storage | For issue reports and part photos |
| Build | Gradle 8.13, AGP 8.13, Kotlin 2.2, compileSdk 36, minSdk 31 | Already installed on this PC |

Rejected options: Unity (heavy, separate toolchain, hard to automate), PWA/web (you want a real phone app).

---

## 2. The 3D bike — how we get it

A black, glossy bike with thin tubes, spokes and cables is one of the **hardest objects for photo-to-3D scanning**. Scans come out as one melted mesh with broken spokes. A scan also can't be split into tappable parts, and tappable parts are the core of the app.

**Plan: build the model, and use your photos as the reference.**
1. **Model generated from real geometry.** I write a Blender Python script that builds the bike from the size-L geometry numbers (wheelbase, head angle, stack/reach, 29" wheels, 100 mm fork). Every part is a separate named object: frame tubes, fork, wheels and spokes, 10–51T cassette, chain, derailleur, MT200 calipers, 180/160 rotors, cockpit, saddle and so on. Output: `bike.glb`.
2. **Your photos make it look like your bike.** Side photos are used to line up the proportions. Close-ups give decals, colours and details (the Scott/Scale logos on the black frame, the Suntour fork graphics, Maxxis sidewalls).
3. **Optional:** you can try a scan with a phone app (Polycam / KIRI Engine / RealityScan) as an extra reference, not as the final model.

The script is repeatable. When you replace a part (say a new fork), we change a parameter and re-export, and the 3D bike matches your real bike.

**Needed:** Blender (free) installed on this PC. It isn't installed yet.

### 📸 Photos to take
Shoot in daylight or even indoor light, no harsh sun. Bike upright (on a stand or leaning on a wall, wheels straight), plain background if possible. Put a **tape measure or a known-size object** in the full-bike shots.

**Full bike (from ~3 m away, zoomed in a bit, camera at axle height, square to the bike):**
- [ ] Drive side (chain side), exactly side-on
- [ ] Non-drive side, exactly side-on
- [ ] Front, straight on
- [ ] Rear, straight on
- [ ] Top-down (from a chair or ladder), if possible
- [ ] 4 × three-quarter views (front-left, front-right, rear-left, rear-right)

**Close-ups (fill the frame):**
- [ ] Cockpit from above (bar, stem, grips, shifter, lockout remote, brake levers)
- [ ] Head tube and the logo on the front of the frame
- [ ] Every frame decal (down tube both sides, top tube, seat tube, chainstay)
- [ ] Fork: crown, legs, decals, lockout
- [ ] Crankset and chainring (both sides), pedals
- [ ] Cassette and rear derailleur
- [ ] Front and rear brake calipers and rotors
- [ ] Front and rear hubs
- [ ] Tyre sidewall (Maxxis logo) and tread
- [ ] Saddle (top and side), seatpost and seat clamp
- [ ] Anything custom or damaged (scratches, stickers, mods)

**Measurements (a tape measure is enough):**
- [ ] Wheelbase (axle to axle)
- [ ] Saddle height (BB centre to top of saddle)
- [ ] Handlebar width
- [ ] Stem length (usually printed on the stem)

---

## 3. Screens (NFS-garage style)

### 🏠 Garage (home)
- Dark studio with spotlights and a reflective floor. The bike slowly turns on a turntable.
- Drag to orbit, pinch to zoom, double-tap to reset.
- Each part glows in its **condition colour** (green OK / amber due soon / red needs attention) when "status view" is on.
- HUD at the top: odometer, bike condition score (%), number of open issues, next service due.
- **Category carousel** along the bottom, like NFS upgrade categories:
  `Frame & Fork · Cockpit · Brakes · Drivetrain · Wheels & Tyres · Contact points`
  Picking a category moves the camera to that area and shows its parts as cards.
- **Exploded view** button: parts animate apart so you can see and tap each one.

### 🔧 Part card (tap a part)
Camera zooms to the part, the rest of the bike dims, and the part gets an outline glow. A bottom sheet slides up with:
- **Header:** part name, brand/model, **tier badge** (Stock / Sport / Pro / Elite) and condition bar.
- **Stats bars, NFS-style:** e.g. brakes → Power / Modulation / Heat resistance / Weight. Shows the change when comparing an upgrade.
- **Ownership:** got it on (date), odometer then, km on part, age, price, where bought, stock or upgrade.
- **Maintenance:** what to do, interval (km and/or days) and progress bars, last service, *Log service* and *Replace* buttons.
- **About:** what it does, advantages (+) and disadvantages (−).
- **Issues:** report (text, severity, photos), open/resolved, how it was fixed.
- **History:** every install, service, inspection and repair, with cost and who did it.
- **Previous parts** in this slot (e.g. chain #1 → #2 → #3, with the km each one lasted).

### ⬆️ Upgrades (the NFS part)
- A wishlist per part: planned upgrades with price, link, and stat changes (weight saved, more power…).
- "Preview": swap the 3D part for the upgrade version if we have a model for it, or show the stat comparison.
- Running total of planned upgrade cost.

### 📜 Timeline
All events in date order (purchase, rides, services, issues, replacements), with filters and month headers.

### 🧰 Tools
- Pre-ride checklist (8 quick checks)
- Tyre pressure helper (rider weight, tubeless on/off → front/rear psi and bar)
- Torque reference for this bike's parts
- Fit and setup notes (saddle height, spacers, fork settings)

### ⚙️ Garage settings
Bike info, odometer and rides log, costs (bike + upgrades + services, cost per km), backup export/import, reset.

---

## 4. Data model (ready)

Already written in `android/app/src/main/java/dev/toni/scalebike/data/`:
- `Part`: slot (= 3D node name), category, brand/model/spec, stock flag, install date and odometer, price, shop, description, pros, cons, maintenance text, service interval (km/days), replace hint, notes, retired info
- `ServiceEvent`: install / service / inspection / repair / removed, with date, odometer, cost, who did it
- `Issue`: title, details, severity, photos, resolved date and how it was fixed
- `Ride`: date, km, note (odometer = starting km + rides)
- **Condition logic:** progress = max(km since service ÷ km interval, days ÷ day interval) → OK / due soon (≥80%) / overdue. Open issues push the status up.
- **Stock spec preloaded** for all 23 parts of the 2022 Scale 980: Suntour XCR32 RL-R 100 mm, Deore M6100 1×12 with 10–51T cassette, FC-MT511 32T, KMC X12, Shimano MT200 with RT10 180/160 rotors, Syncros 32H rims with Formula CL-51 / Shimano MT401 hubs, Maxxis Rekon Race 29×2.25, Syncros cockpit (740 mm bar), BB-MT500-PA, Belcarra saddle and more. Each comes with pros, cons and service intervals.

To add: `Upgrade` (wishlist item: part slot, name, price, link, stat deltas), part **tier** and **stats** for the NFS cards.

---

## 5. Build phases

| # | Phase | Result |
|---|---|---|
| 0 | ✅ Project setup and data layer | Gradle project, data model, stock parts, storage, backup (done) |
| 1 | 3D model | Blender script → `bike.glb` with named parts, checked against your photos |
| 2 | 3D garage scene | SceneView, lighting, turntable, orbit, tap-to-select, condition glow |
| 3 | NFS UI | Category carousel, camera fly-to, part cards with stats bars, exploded view |
| 4 | Part details | Maintenance, history, issues with photos, replace flow (reuses existing logic) |
| 5 | Upgrades and extras | Wishlist with stat comparison, timeline, tools, costs |
| 6 | Polish on the Pixel 9 Pro | Haptics, animations, performance (60–120 fps), app icon, final install |
| 7 (optional) | Later | Strava sync for automatic km, service reminder notifications, home-screen widget |

---

## 5b. Phase 2 plan: 3D garage in the app (decided with Toni, 2026-10-05)

**Toni's choices:** dark NFS garage ("really cool looking") · full v3 model, compressed · tap = highlight + name + condition · Garage becomes the home screen, the other 2D screens stay reachable · condition colours as a glow in a "status view" · turntable spins when idle · 120 fps while touching, lower when idle · test builds may be installed on the Pixel 9 Pro during Phase 2.

**Update (Toni, 2026-10-05, after the first phone test): the app must look like a game garage (Forza / GTA / NFS), not a normal app.** Decisions: NFS neon look + GTA LS Customs camera (every menu choice flies the camera to that area of the bike) · **landscape only** · no Material bottom bar; service log, workshop tools, bike settings and part details are **panels over the 3D garage** · extras: menu sounds (mutable), vibration, a Forza-style condition badge (class + number), an intro (garage lights switch on, camera sweep).

**Update (Toni, 2026-10-10): game controls + design first.** The temporary right-side menu goes away. Navigation = **modes you swipe between** (`SERVICE LOG · GARAGE · PARTS · WORKSHOP · BIKE`, Garage = home in the middle): **swipe from the left/right screen edge** (or tap the ◀ ▶ / tabs in the bottom mode bar) changes mode, the turntable turns and the panel slides in with sound + vibration. **Drag on the bike = rotate**, pinch = zoom, double-tap = reset, tap a part = camera fly-to + card, back = close card / go up a level, **hold-to-confirm** for important actions. The UI is designed first as a **clickable prototype** (not Figma: the Starter plan only allows a few Figma actions per month): `design/prototype/` → (local page). Once Toni approves it, steps 6–8 and 11 are built to match it.

| Step | What | Done when |
|---|---|---|
| 1 | ✅ Phone model: Draco `bike.glb` (2.27 MB, 23 parts) | done |
| 2 | ✅ Engine: plain Filament 1.75.1 (SceneView 4.x needs Kotlin 2.4), garage IBL from a CC0 parking-garage HDR, 3D view as home; detach crash fixed | done, runs on the Pixel |
| 3 | **Landscape + full-screen:** lock to landscape, hide the system bars (immersive), remove the Material bottom bar | App opens sideways, no app chrome |
| 4 | **Dark NFS garage scene:** indoor camera exposure, 3 spotlights (key, rim, top), soft shadows, glossy reflective floor, turntable with a neon light ring, bloom; framing for landscape | Phone screenshot looks like a game garage |
| 5 | **Intro:** garage lights switch on one by one, camera sweeps around the bike, then the menu slides in | Plays at start (skippable by tap) |
| 6 | **Game HUD:** nameplate (SCOTT SCALE 980), odometer, **condition badge** (class letter + number from the condition logic), open issues, next service | Values come from `BikeRepository` |
| 7 | **Main menu, NFS style:** slanted neon tiles (PARTS · SERVICE LOG · WORKSHOP · BIKE), game fonts bundled offline (OFL), sounds + vibration on moves | Every tile opens its panel |
| 8 | **PARTS = LS Customs:** category list on the side (Wheels & tyres, Drivetrain, Brakes, Cockpit, Frame & fork, Contact points); picking one flies the camera to that area; parts list → tap = highlight + name + condition | All 23 parts reachable from the menu and by tapping the bike |
| 9 | **Turntable + free camera:** slow spin when idle, drag = orbit, pinch = zoom, double-tap = reset; spin stops in menus | Smooth |
| 10 | **Status view:** parts glow green / amber / red (emissive + bloom) | Matches the condition logic |
| 11 | **Panels over the garage:** service log (timeline), workshop (tools), bike settings, part details, re-skinned as translucent game panels (logic reused) | Old features all reachable |
| 12 | **Performance:** 120 Hz while touching, ~60 Hz while spinning idle; fps, load time, memory on the Pixel 9 Pro | Numbers in the checklist |

<details><summary>First version of the Phase 2 steps (portrait, before the game-UI decision)</summary>

| Step | What | Done when |
|---|---|---|
| 1 | **Phone model:** export `bike.glb` with Draco compression (Blender exporter, 16-bit positions so the 0.3–0.5 mm decal layers don't flicker), copy to `app/src/main/assets/`. Part names stay the 23 slots | File ≤ ~4 MB, all 23 parts present |
| 2 | **Add Filament 1.75.1** (plain Filament + gltfio + filament-utils ModelViewer; changed from SceneView, whose 4.x versions need Kotlin 2.4) with exact pinned versions | `assembleDebug` builds, model loads |
| 3 | **Garage scene:** dark studio, 3 spotlights (key, rim, top), soft shadows, glossy reflective floor, turntable disc with a neon light ring, bloom + tone mapping + anti-aliasing | Screenshot on the phone looks like an NFS garage |
| 4 | **Turntable + camera:** slow spin when idle (stops on touch, restarts after ~5 s), drag = orbit, pinch = zoom (limits), double-tap = reset | Smooth on the phone |
| 5 | **Tap a part:** Filament picking → node → slot name → highlight the part + label with name and condition (from `Status.kt`) | Every one of the 23 parts can be tapped |
| 6 | **Status view:** button; each part glows green / amber / red (emissive tint + bloom) | Matches the condition logic |
| 7 | **Home + navigation:** Garage replaces the flat drawing as home; small HUD (odometer, condition %, open issues); timeline, tools and part details reachable | Old screens still work |
| 8 | **Performance:** 120 Hz while touching, ~60 Hz while spinning idle; measure fps, load time, memory on the Pixel 9 Pro | Numbers in the checklist |

</details>

**Risks:** SceneView may need a newer Compose BOM (check before upgrading); Draco decoding time at start-up (fallback: meshopt via gltfpack); screen-space reflections may cost fps (fallback: glossy floor without real reflections); a real outline needs an extra render pass, so the highlight starts as an emissive glow.

---

## 5c. Plan: ride km from Google Maps Timeline (Toni, 2026-10-11) — waiting for OK to build

**Why:** Toni doesn't want to log rides by hand; Google Maps Timeline already detects his bike trips correctly. Google Fit shows only steps, and Timeline has no API (it lives on the phone since 2024–25), so the route is Timeline's own export: phone Settings → Location → Location services → Timeline → **Export Timeline data** → `Timeline.json`.

**Checked on Toni's export (54 MB):** `semanticSegments[]` with `activity.topCandidate.type` / `.probability`, `activity.distanceMeters`, ISO `startTime`/`endTime` with offset. 340 `CYCLING` trips, 22 Jun – 10 Oct 2026, 631 km, all with a distance; 4 trips under 50 % probability, 1 over 30 km/h.

| Step | What |
|---|---|
| 1 | BIKE panel: hold **Import rides from Timeline** → system file picker (no storage permission) |
| 2 | Stream-parse the file (`android.util.JsonReader`, skips `rawSignals`); keep only `CYCLING` segments with probability ≥ 0.5 and speed ≤ 35 km/h |
| 3 | One `Ride` per local day: id `timeline-yyyy-MM-dd`, km = sum of that day's trips, note "Timeline · N trips". No schema change |
| 4 | Re-import = merge: a day already imported is replaced by the new total; hand-logged rides are never touched |
| 5 | **Decision (Toni): import everything** since the first Timeline day (22 Jun 2026), not only since app setup — the parts really rode those km, so service status uses them |
| 6 | Banner with the result ("+ N days · X km"); BIKE shows when the last import was |
| 7 | Privacy: only date + km are stored; no places or coordinates; the file is not copied into the app |

---

## 6. Current state of the folder

- A **2D prototype** builds and runs. It has a flat bike drawing with tappable dots, and the part detail, timeline, tools and garage screens. It was only a test, and its UI gets replaced by the 3D garage. The **data layer and logic are kept**.
- `cd android && ./gradlew assembleDebug` builds the APK. Open the `android/` folder in Android Studio.
- Folder layout: see the root `README.md`. Progress tracking: `docs/CHECKLIST.md`.

## 7. Before building, I need from you
1. The **photos and measurements** from section 2.
2. **Install Blender**: https://www.blender.org/download/
3. **Phone:** enable *Developer options → USB debugging*, then accept the "Allow USB debugging?" prompt on the phone so it shows up in `adb devices`.
4. Your OK to start Phase 1.
