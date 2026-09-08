#!/usr/bin/env python3
"""Plugin CLI; resolve modules from this script, never from a shell root variable."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from harness.cli import main

if __name__ == "__main__":
    sys.exit(main())
