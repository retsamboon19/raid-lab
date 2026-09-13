# Raid Lab

Build and compare NIKKE squads using your roster, equipment, burst rotations, and modeled boss mechanics. Runs on your PC and opens in your usual browser.

## Start here — no coding needed

**[Download Raid Lab](https://github.com/retsamboon19/raid-lab/archive/refs/heads/main.zip)**

1. Download the ZIP. On GitHub, **Code → Download ZIP** does the same thing.
2. Right-click the ZIP and choose **Extract All**. Keep the extracted folder somewhere convenient.
3. Open that folder and double-click **Set up Raid Lab.bat**.

Setup downloads its own verified dependencies, creates a desktop shortcut, and opens Raid Lab. **No Python, Git, terminal, administrator access, or offline NIKKE installation is needed.** First setup needs internet. Windows 10/11 on a 64-bit Intel or AMD PC is supported.

Next time, use the **Raid Lab** desktop shortcut or double-click **Start Raid Lab.bat**. If you move the folder, run setup again to update the shortcut.

## Bring in your roster

Choose **Load my account**, select your browser, and sign in to BlaBlaLink. Once your game account and roster appear, use **Import signed-in account** in Raid Lab. No extension or bookmark is required. You can also import a roster JSON or try the demo roster.

## Features

- Disjoint squads, simulated damage, and burst rotation comparisons.
- Supported boss parts, summon clearing, elemental barriers, interruptions, cover, and survival.
- Completed results retained when you cancel a search.
- **History** grouped by mode, boss, and all squads in each run.
- CPU by default. Optional GPU exploration is available in builds containing its additional runtime.

**Estimates are not guaranteed game scores or clears.** Targeting, collision geometry, incoming damage, and some boss/skill behavior remain approximate. Read the model notes inside the app before interpreting a pass as an in-game guarantee.

## Your data stays yours

Roster files and history stay in `tools/raid-lab/private`. Browser sign-in profiles stay under `%LOCALAPPDATA%/RaidLab`. The app does not upload your roster to this repository. Private data, credentials, logs, and development captures are excluded from Git.

To update, extract a fresh copy, copy your old `tools/raid-lab/private` folder into the new copy, then run setup. Keep the old copy until your history appears. Browser sign-in profiles remain on the same PC.

## Troubleshooting

- **ZIP window still open:** extract the entire archive first; do not run setup inside the ZIP.
- **Setup cannot download:** check your connection or proxy and run setup again. Downloads are checked against pinned SHA-256 hashes.
- **An error appears:** keep the message and [open an issue](https://github.com/retsamboon19/raid-lab/issues). Remove account identifiers and private roster data before sharing logs.
- **No shortcut:** double-click `Start Raid Lab.bat` directly.
- **Windows blocks the script:** use a copy from this repository and follow your PC's software policies. Do not disable antivirus or system security settings.

## Development

App: `tools/raid-lab`. Vendored engine: `tools/nikke-team-builder`. All runtime paths are relative. `launch.ps1 -PrepareOnly` prepares dependencies without launching a browser or making a shortcut.

See [third-party notices](THIRD_PARTY_NOTICES.md). NIKKE and its characters belong to their respective rights holders. This is an unofficial fan tool.
