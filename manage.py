#!/usr/bin/env python3
import sys
if sys.version_info < (3, 11):
    sys.exit("Python 3.11+ is required. Try python3.11 or a newer interpreter.")
from manager.cli import main
if __name__ == "__main__":
    raise SystemExit(main())
