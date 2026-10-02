# Scale 980 Garage

A personal Android app for my **2022 Scott Scale 980 (size L, black)**, built for the **Google Pixel 9 Pro**.
It shows the bike in 3D in a *Need for Speed*-style garage. For every part it tracks when I got it, when it needs service, its pros and cons, its history and any issues.

## Folder structure

```
3. Bike App/
├── README.md              ← you are here
├── CLAUDE.md              ← rules & commands Claude reads every session
├── docs/
│   ├── PLAN.md            ← the full plan (what we're building and how)
│   ├── CHECKLIST.md       ← progress tracker: done / to do / blocked  ⭐ update after every session
│   └── BIKE-SPECS.md      ← stock spec sheet + my own measurements
├── photos/                ← bike photos for building the 3D model (local only, not in git)
│   ├── full-bike/         ← side, front, rear, top, ¾ views
│   └── closeups/          ← one folder per area (cockpit, fork, drivetrain, brakes, …)
├── 3d/
│   ├── blender/           ← Blender Python scripts that generate the bike model
│   ├── models/            ← exported models (bike.glb) that the app loads
│   └── reference/         ← scan attempts, blueprints, geometry images
└── android/               ← Android Studio project (Kotlin + Jetpack Compose)
    └── app/src/main/java/dev/toni/scalebike/
        ├── data/          ← data model, stock parts, storage, condition logic (kept)
        └── ui/            ← screens (current 2D prototype, to be replaced by 3D garage)
```

## Build & run

Open the `android/` folder in Android Studio, **or** from a terminal:

```bash
cd android && ./gradlew assembleDebug
```

To install on the connected phone (USB debugging on):

```bash
cd android && ./gradlew installDebug
```

## Status

See **[docs/CHECKLIST.md](docs/CHECKLIST.md)**.
