"""Make the src-layout modules available to unittest discovery from the repository root."""
import sys
from pathlib import Path
src = str(Path(__file__).resolve().parent.parent / 'src')
if src not in sys.path:
    sys.path.insert(0, src)
