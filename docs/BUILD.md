# Development and Windows packaging

From the repository root, using Python 3.10 or later:

```powershell
py -m pip install -r requirements.txt
py .\src\Launch.pyw --demo
py -m unittest discover -v
```

For the classic task-list renderer: `py .\src\LaunchClassic.pyw`.

To build locally on Windows x64, install Inno Setup 6 in its default location and make sure `python` resolves to a suitable x64 Python interpreter. Run from the root:

```powershell
.\scripts\build-windows.ps1
```

The script creates a build virtual environment, installs dependencies, runs tests, packages the Qt application with PyInstaller, checks that the disconnected packaged demo remains running, builds the installer with Inno Setup, and writes the portable ZIP, Setup EXE and SHA256 checksums under `release/`.

Alternatively, open GitHub Actions → Build Windows packages → Run workflow. Pull requests and pushes to main that change build inputs also trigger the workflow. Download the artifact from a successful run. Test the installer and portable executable before attaching new builds to a GitHub Release. Builds are unsigned.

## Repository layout

- `src/`: application, launchers and core modules
- `tests/`: automated tests; root-level unittest discovery is supported
- `assets/`: application icons
- `docs/`: documentation and screenshots
- `scripts/`: PyInstaller build script and Inno Setup installer configuration
- `.github/workflows/`: automated Windows build

Account settings remain outside the repository under `%LOCALAPPDATA%/HabiticaProgressBoard/`. Do not commit real account configuration or API credentials.

This reorganization changes source-tree paths, not the application version or existing v0.7.5 Release assets. A new Windows build should be verified after merging.
