#!/usr/bin/env python3
"""Offline report build from versioned editorial and source records."""
from pathlib import Path
import os,subprocess,sys

ROOT=Path(__file__).resolve().parent.parent
for name in ['build_profiles.py','integrate_report.py','build_inventory.py','render_references.py','build_references.py','build_figures.py']:
    subprocess.run([sys.executable,str(ROOT/'research'/name)],cwd=ROOT,check=True)
subprocess.run([os.environ.get('HARNESS_NODE','node'),str(ROOT/'research/build_report.mjs')],cwd=ROOT,check=True)
