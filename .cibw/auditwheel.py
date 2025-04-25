#!/usr/bin/env python
import sys

from auditwheel.main import main

if "repair" in sys.argv:
    sys.argv.append("--only-plat")
    for name in ("mpi",):
        sys.argv.append("--exclude")
        sys.argv.append(f"lib{name}.so.*")

sys.exit(main())
