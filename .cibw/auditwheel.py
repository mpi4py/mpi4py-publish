#!/usr/bin/env python
import sys

from auditwheel.main import main
from auditwheel.policy import load_policies

libmpi = []
for name in ("mpi", "open-pal", "open-rte"):
    for version in (1, 12, 20, 40):
        libmpi.append(f"lib{name}.so.{version}")

for policy in load_policies():
    policy["lib_whitelist"].extend(libmpi)

if __name__ == "__main__":
    sys.exit(main())
