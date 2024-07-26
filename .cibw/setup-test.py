import glob
import json
import os
import re
import sys

try:
    wheelhouse = sys.argv[1]
except IndexError:
    for pth in ("wheelhouse", "dist", "."):
        if os.path.isdir(pth):
            wheelhouse = pth
            break

pattern1 = re.compile(
    r"(?:mpi4py)_"
    r"(mpi(?:20|31|40|41))_(mpich|openmpi|msmpi|impi)-"
    r"(?:\d+(?:\.\d+)*(?:\.dev\d*)?)-"
    r"(cp|pp)(\d)(\d+)-"
    r"(?:[_\w]+)-"
    r"(manylinux|macosx|win)_([_\w]+)"
)
pattern2 = re.compile(
    r"(?:mpi4py)-"
    r"(?:\d+(?:\.\d+)*(?:\.dev\d*)?)\+"
    r"(mpi(?:20|31|40|41))\.(mpich|openmpi|msmpi|impi)-"
    r"(cp|pp)(\d)(\d+)-"
    r"(?:[_\w]+)-"
    r"(manylinux|macosx|win)_([_\w]+)"
)

osmap = {
    "manylinux": "Linux",
    "macosx": "macOS",
    "win": "Windows",
}
mpimap_linux = {
    "mpi31-mpich": [
        ("mpich", ["3.2", "3.3", "3.4", "4.0", "4.1"]),
        ("impi_rt", ["2021.10.0", "2021.13.0"]),
    ],
    "mpi31-openmpi": [
        ("openmpi", ["3.1", "4.0", "4.1", "5.0"]),
    ],
    "mpi40-mpich": [
        ("mpich", ["4.0", "4.1"]),
    ],
    "mpi41-mpich": [
        ("mpich", ["4.2"]),
    ],
}
mpimap_macos = {
    "mpi31-mpich": [
        ("mpich", ["3.2", "4.1"]),
    ],
    "mpi31-openmpi": [
        ("openmpi", ["3.1", "4.1", "5.0"]),
    ],
    "mpi40-mpich": [
        ("mpich", ["4.0", "4.1"]),
    ],
    "mpi41-mpich": [
        ("mpich", ["4.2"]),
    ],
}
mpimap_windows = {
    "mpi20-msmpi": [
        ("msmpi", ["10.1.1"]),
    ],
    "mpi31-impi": [
        ("impi_rt", ["2021.10.0", "2021.13.0"]),
    ],
}
mpimap = {
    "Linux": mpimap_linux,
    "macOS": mpimap_macos,
    "Windows": mpimap_windows,
}
pymap = {
    "cp": "",
    "pp": " pypy",
}

builds = []
for whl in sorted(glob.glob(os.path.join(wheelhouse, "*.whl"))):
    for pattern in (pattern1, pattern2):
        match = pattern.match(os.path.basename(whl))
        if match is not None:
            break
    assert match is not None
    std, mpi, py, x, y, ostag, archtag = match.groups()
    osname, mpiabi, x, y = osmap[ostag], f"{std}-{mpi}", int(x), int(y)
    for arch in ("x86_64", "AMD64", "arm64"):
        if arch.lower() in archtag.lower():
            builds.append((osname, arch, mpiabi, py, (x, y)))
builds = sorted(builds, key=lambda r: (r[0].lower(), *r[1:]))


runners = {
    "Linux-x86_64": "ubuntu-22.04",
    "macOS-arm64": "macos-14",
    "macOS-x86_64": "macos-13",
    "Windows-AMD64": "windows-2022",
}
matrix = []
for entry in builds:
    osname, arch, mpiabi, py, (x, y) = entry
    if (x, y) >= (3, 10) and py == "pp":  # TODO: update for pp310
        continue
    if osname == "Windows":
        if py == "pp" and (x, y) == (3, 7):
            continue  # mamba-org/setup-micromamba#133
    runner = runners[f"{osname}-{arch}"]
    for mpiname, mpiversions in mpimap[osname][mpiabi]:
        for mpiversion in mpiversions:
            if f"{osname}-{arch}" == "macOS-arm64":
                if f"{mpiname}-{mpiversion}" == "mpich-3.2":
                    continue
                if f"{mpiname}-{mpiversion}" == "openmpi-3.1":
                    continue
            if (py == "cp" and (x, y) == (3, 6)
                    and f"{mpiname}-{mpiversion}" == "openmpi-5.0"):
                continue  # python=3.6 openmpi=5.0 cannot be solved
            row = {
                "runner": runner,
                "mpi": mpiname,
                "mpi-version": mpiversion,
                "py": f"{x}.{y}{pymap[py]}",
                "arch": arch,
            }
            matrix.append(row)
print(f"matrix-test-cf={json.dumps(matrix)}")


runners = {
    "Linux-x86_64": [
        "ubuntu-20.04",
        "ubuntu-22.04",
    ],
    "macOS-arm64": [
        "macos-14",
    ],
    "macOS-x86_64": [
        "macos-13",
    ],
    "Windows-AMD64": [
        "windows-2019",
        "windows-2022",
    ],
}
matrix = []
for entry in builds:
    osname, arch, mpiabi, py, (x, y) = entry
    if (x, y) >= (3, 10) and py == "pp":  # TODO: update for pp310
        continue
    std, _, mpi = mpiabi.partition("-")
    mpispeclist = [mpi]
    if osname == "Linux" and mpi == "mpich":
        mpispeclist.append("impi")
    pypy = "pypy" if py == "pp" else ""
    pyspec = f"{pypy}{x}.{y}"
    for runner in runners[f"{osname}-{arch}"]:
        if runner == "ubuntu-22.04":
            if py == "cp" and (x, y) < (3, 7):
                continue
        if runner == "macos-14":
            if py == "cp" and (x, y) < (3, 10):
                continue
        if runner == "macos-13":
            if py == "cp" and (x, y) < (3, 8):
                continue
        if runner == "macos-12":
            if py == "cp" and (x, y) < (3, 7):
                continue
        for mpispec in mpispeclist:
            row = {
                "runner": runner,
                "mpi": mpispec,
                "py": pyspec,
                "arch": arch,
            }
            if row not in matrix:
                matrix.append(row)
print(f"matrix-test-gh={json.dumps(matrix)}")
