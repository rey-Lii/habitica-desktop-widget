# Habitica Progress Board

An unofficial compact Windows desktop widget for Habitica To-Dos, Dailies and Habits. Python + Qt 6. Not affiliated with Habitica.

**Version 0.7.5 — Instant Response / Classic Font**

## Start

1. Extract the entire ZIP into a normal folder. Do not open from inside the ZIP.
2. Install Python 3.10+ and `py -m pip install PySide6-Essentials` if not already installed. Use the same interpreter to launch.
3. Close the previous version, then double-click `Launch.pyw`. Or run `py .\Launch.pyw` in PowerShell from the extracted folder. The launcher shows startup errors.
4. Existing Windows DPAPI credentials are reused if available. Otherwise open Settings and connect. Never share your API token.

## What's new in 0.7.5

- Restores the exact v0.7.2 font initialization, weight and stylesheet. Previously saved Rounded preferences are ignored; no new fonts required.
- On HTTP 429, honors Habitica's Retry-After header (120 seconds plus a safety second if absent or invalid). Requests are blocked until the cooldown ends, and the client automatically refreshes the server state. The timer does not retry scoring writes. Unconfirmed intents are cleared on errors as in v0.7.4; verify server state before manually repeating them.
- Normal automatic refresh interval increased from 60 to 120 seconds. Instant local response, viewport virtualization and the previous layout are unchanged.

## Instant response behavior

- To-Do completion, Daily toggles and checklist changes appear locally immediately. Overall progress is projected from a confirmed server snapshot plus pending actions. The permanent tracking record contains confirmed completions only.
- Habit scores are queued individually; the footer shows pending changes. No Habit progress bar or invented score counter. Up to 24 pending actions may be queued while the server catches up. Writes run in FIFO order, one network worker at a time. The original API state checks and partial confirmation are retained.
- If a network write fails or confirmation differs, the widget discards unconfirmed intents, restores the last confirmed snapshot, and requires a successful fresh read before accepting more actions. Some attempted writes may have succeeded server-side; never assume the rollback reversed server scoring. No automatic write retries. The close button waits for pending actions; forcibly terminating the process may lose unsent actions. This is not an offline durable queue.
- The footer reports pending sync. Acknowledgments that do not change the visible state avoid rebuilding the list. Periodic refreshes remain enabled and use the same serialized worker.
- Keeps the v0.7.3 pearl palette, icon, viewport virtualization, smooth wheel scrolling, layout and resize behavior.

## Features

- Three sliding tabs: **To-Dos / Dailies / Habits**. No separate Projects category. Every active To-Do is visible in one searchable, scrollable list. Checklist To-Dos retain individual progress bars and expandable subtasks; ordinary To-Dos remain compact checkable rows. Parent To-Do completion with a checklist still requires all children checked and explicit confirmation.
- Pinned overall To-Do progress bar: confirmed completed parent To-Dos (plus temporary pending completions in the on-screen preview) divided by the sum of confirmed completed and currently open To-Dos. A tracking period begins on the first successful sync (or Reset). New To-Dos increase the denominator. Reopened To-Dos return to the open list. Deleted or unconfirmed missing tasks are not counted as completed. Checklist completion is shown separately and does not itself count as a parent completion. Reset starts a new local tracking period without changing any Habitica tasks.
- To-Do tracking persists locally per account, independent of search filters. The app requests the recent completed To-Dos at every refresh to recognize external completions of previously tracked open tasks. Habitica's API only supplies the most recent 30 completed To-Dos, so external completions missed while offline may remain unconfirmed; this is not an all-time account completion statistic.
- Dailies: show due, not scheduled, and unknown schedule groups based on Habitica's `isDue` field. A separate progress bar counts only Dailies marked due by the server, using their `completed` status. Check or uncheck a Daily to sync its score; expandable Daily checklists are supported. Habitica controls its day boundary and recurring schedule. No forced cron or schedule modification.
- Habits: positive/negative buttons according to the server's permitted directions. No progress bar.
- Retains the Compact Pearl appearance, resize grip, drag-to-move header, pin, compact mode, icon and opacity controls. Auto-refresh every 120 seconds outside cooldown. No true native Acrylic blur.

## Tests and limitations

Run `py -m unittest discover -v`. 71 tests passed, including five new rate-limit tests. Two real Qt smoke tests were skipped because PySide6 is unavailable. Python syntax compilation passed. The geometry tests include 84 rows, 10,000-row bounds, anchor preservation and 500 deterministic random geometry cases. These are not measured frame rates or live Habitica tests. Windows Qt rendering, real widget virtualization, resizing, keyboard interactions and actual responsiveness still require testing on a Qt-enabled machine. Run `py .\Launch.pyw --demo` for a disconnected demo or use the classic launcher if needed. No bundled EXE. No true native Acrylic blur.

## Security

Settings and local tracking data are saved under `%LOCALAPPDATA%/HabiticaProgressBoard/settings.json`; remembered tokens use Windows DPAPI encryption. No user data or credentials are included in the source archive. Do not publish your settings. No license has been selected. The app avoids automatic retries of scoring writes; refresh after failures. Pending intents live in memory only.

Official API: https://apidoc.habitica.com/

API rate-limit guidance: https://github.com/HabitRPG/habitica/wiki/API-Usage-Guidelines
