<p align="center">
  <img src="assets/HabiticaBoard.png" width="80" alt="Habitica Progress Board icon">
</p>

<h1 align="center">Habitica Progress Board</h1>

<p align="center">Your Habitica tasks, always within reach.</p>
<p align="center">
  <a href="https://github.com/rey-Lii/habitica-progress-board/releases/latest"><img src="https://img.shields.io/github/v/release/rey-Lii/habitica-progress-board?color=9B8DBB&label=release" alt="Latest release"></a>
  <img src="https://img.shields.io/badge/Windows-10%20%2F%2011-8CAFC6" alt="Windows 10 and 11">
</p>
<p align="center">
  <a href="https://github.com/rey-Lii/habitica-progress-board/releases/download/v0.7.5/HabiticaProgressBoard-v0.7.5-Windows-x64-Setup.exe"><strong>Download for Windows (.exe)</strong></a>
  &nbsp;·&nbsp;
  <a href="https://github.com/rey-Lii/habitica-progress-board/releases">All releases</a>
</p>

![Habitica Progress Board — To-Dos, Dailies and Habits](docs/images/hero.png)

A compact desktop companion for [Habitica](https://habitica.com/). Track your progress, complete tasks and score habits without switching to your browser. Local feedback is immediate while changes synchronize with Habitica in the background.

## Features

- **To-Dos:** Overall progress tracking and interactive checklists.
- **Dailies:** Today's scheduled tasks and completion percentage.
- **Habits:** Repeatable positive and negative scoring.
- **Instant feedback:** Responsive local updates with background synchronization and rate-limit handling.
- **Desktop-friendly:** Resizable, movable, optionally always on top, with adjustable background opacity, smooth scrolling and searchable lists.

## Installation

For Windows 10/11 (x64). The packaged builds include Python and Qt; no separate runtime installation is required.

| Download | How to use |
| --- | --- |
| [Windows installer](https://github.com/rey-Lii/habitica-progress-board/releases/download/v0.7.5/HabiticaProgressBoard-v0.7.5-Windows-x64-Setup.exe) | Run Setup and optionally create a desktop shortcut. |
| [Portable ZIP](https://github.com/rey-Lii/habitica-progress-board/releases/download/v0.7.5/HabiticaProgressBoard-v0.7.5-Windows-x64-portable.zip) | Extract the entire archive and open `HabiticaProgressBoard.exe`. |
| [SHA256 checksums](https://github.com/rey-Lii/habitica-progress-board/releases/download/v0.7.5/SHA256SUMS.txt) | Verify download integrity. |

The installer is currently unsigned. Windows may display a publisher warning. This is an early release.

## Connect to Habitica

1. Open [Habitica API settings](https://habitica.com/user/settings/api).
2. Launch the widget and open Settings (`···`).
3. Enter your User ID and API Token, then select **Connect**.
4. Optionally remember your token on this device.

Keep your API token private. Never include it in screenshots or bug reports.

## How it works

To-Do progress counts parent tasks completed since tracking began, relative to those completions plus currently open To-Dos. Checklist progress is separate. Reset starts a new local tracking period without modifying Habitica tasks. Daily progress counts Dailies due on the current Habitica day. Habits have no percentage.

<details>
<summary>Synchronization, progress and privacy details</summary>

- Habitica exposes a limited history of completed To-Dos; external completions missed while offline may not be recovered. This is not an all-time account statistic.
- Local task state updates immediately; queued writes are processed sequentially. Only confirmed completions are persisted. Regular refreshes occur every 120 seconds outside cooldown periods.
- On HTTP 429 the widget honors the available Retry-After value, then refreshes. Failed or uncertain scoring writes are not automatically replayed. Verify server state before repeating an unconfirmed action.
- Pending actions are stored in memory, not in a durable offline queue. Allow synchronization to finish before closing the widget.
- Preferences and tracking data are stored under `%LOCALAPPDATA%\HabiticaProgressBoard\settings.json`. Remembered tokens use Windows DPAPI. The widget communicates directly with the Habitica API.
- The pearl-inspired translucent interface does not implement native Windows Acrylic blur.

</details>

<details>
<summary>Run from source and build for Windows</summary>

Requires Python 3.10+ and PySide6-Essentials. Download or clone the repository and run from its root:

```powershell
py -m pip install -r requirements.txt
py .\src\Launch.pyw
```

Disconnected demo:

```powershell
py .\src\Launch.pyw --demo
```

Do not enter real credentials in the demo. `src/LaunchClassic.pyw` provides a compatibility mode for the task list.

Run tests:

```powershell
py -m unittest discover -v
```

Windows packaging uses PyInstaller and Inno Setup. See [build instructions](docs/BUILD.md) and the [Windows build workflow](.github/workflows/build-windows.yml).

</details>

## Feedback

[Report an issue or suggest a feature](https://github.com/rey-Lii/habitica-progress-board/issues). Please include the version, Windows version and steps to reproduce, without private tasks or credentials.

---

An independent, unofficial companion app. Not affiliated with or endorsed by Habitica. Built with Python, Qt 6 and the [Habitica REST API](https://apidoc.habitica.com/).
