"""Compatibility launcher: use the v0.7.2-style nonvirtual list."""
import sys, runpy
from pathlib import Path
if __name__=='__main__':
    sys.argv.append('--classic-list')
    runpy.run_path(str(Path(__file__).with_name('Launch.pyw')),run_name='__main__')
