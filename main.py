"""Entry point: starts the program. Contains no logic."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.app import main
if __name__ == "__main__":
    raise SystemExit(main())
    