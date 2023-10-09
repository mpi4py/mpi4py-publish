#!/usr/bin/env python
import os
import sys

import delocate.cmd.delocate_wheel as mod
from delocate.delocating import delocate_wheel, filter_system_libs

libmpi = []
for name in ("mpi", "pmpi", "open-pal", "open-rte"):
    for version in (1, 12, 20, 40):
        libmpi.append(f"lib{name}.{version}.dylib")
libmpi = set(libmpi)


def filter_libs(filename):
    if not filter_system_libs(filename):
        return False
    if os.path.basename(filename) in libmpi:
        return False
    return True


def delocate_wheel_patched(*args, **kwargs):
    kwargs["copy_filt_func"] = filter_libs
    return delocate_wheel(*args, **kwargs)


mod.delocate_wheel = delocate_wheel_patched

dyldname = "DYLD_FALLBACK_LIBRARY_PATH"
dyldpath = os.environ.get(dyldname, "").split(":")
dyldpath.append("/usr/local/lib")
dyldpath.append("/opt/homebrew/lib")
dyldpath.append("/opt/local/lib")
os.environ[dyldname] = ":".join(dyldpath)

ZIP_TIMESTAMP_MIN = 315532800  # 1980-01-01 00:00:00 UTC
timestamp = os.environ.get("SOURCE_DATE_EPOCH")
if timestamp is not None:
    import delocate.tools
    time = delocate.tools.time
    timestamp = max(int(timestamp), ZIP_TIMESTAMP_MIN)
    time_patch = type(time)("time")
    time_patch.__dict__.update(time.__dict__)
    time_patch.localtime = lambda _=None: time.localtime(timestamp)
    delocate.tools.time = time_patch

if __name__ == "__main__":
    sys.exit(mod.main())
