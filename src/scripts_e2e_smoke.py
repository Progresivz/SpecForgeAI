"""Run the same end-to-end validation through pytest.

Usage: python scripts_e2e_smoke.py
"""
import subprocess
import sys

raise SystemExit(subprocess.call([sys.executable, "-m", "pytest", "-q", "tests/test_e2e_system.py"]))
