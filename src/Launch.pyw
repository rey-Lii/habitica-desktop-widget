"""Diagnostic launcher for the desktop widget; run from an extracted folder."""
import os
import runpy
import sys
from pathlib import Path
import traceback

if __name__ == '__main__':
    folder = Path(__file__).resolve().parent
    sys.path.insert(0, str(folder))
    try:
        runpy.run_path(str(folder / 'HabiticaProgressBoard.pyw'), run_name='__main__')
    except Exception:
        message = traceback.format_exc()
        if os.name == 'nt':
            import ctypes
            ctypes.windll.user32.MessageBoxW(None, message, 'Habitica Board — Startup error', 0x10)
        else:
            print(message, file=sys.stderr)
        raise SystemExit(1)
