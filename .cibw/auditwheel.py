#!/usr/bin/env python
import sys
from auditwheel.main import main

for name in ("mpi", "open-pal", "open-rte"):
    sys.argv.append("--exclude")
    sys.argv.append(f"lib{name}.so.*")

if __name__ == "__main__":
    sys.exit(main())
