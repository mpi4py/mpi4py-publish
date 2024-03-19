#!/usr/bin/env python
import sys

from auditwheel import policy
from auditwheel.main import main

libmpi = []
for name in ("mpi", "open-pal", "open-rte"):
    for version in (1, 12, 20, 40):
        libmpi.append(f"lib{name}.so.{version}")

if hasattr(policy, "WheelPolicies"):

    super_init = policy.WheelPolicies.__init__

    def init(self, *args, **kwargs):
        super_init(self, *args, **kwargs)
        for entry in self.policies:
            entry["lib_whitelist"].extend(libmpi)

    policy.WheelPolicies.__init__ = init

else:

    for entry in policy.load_policies():
        entry["lib_whitelist"].extend(libmpi)

if __name__ == "__main__":
    sys.exit(main())
