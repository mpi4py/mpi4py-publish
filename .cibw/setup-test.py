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
    r"(mpi(?:20|31|40))_(mpich|openmpi|msmpi|impi)-"
    r"(?:\d+(?:\.\d+)*(?:\.dev\d*)?)-"
    r"(cp|pp)(\d)(\d+)-"
    r"(?:[_\w]+)-"
    r"(manylinux|macosx|win)_([_\w]+)"
)
pattern2 = re.compile(
    r"(?:mpi4py)-"
    r"(?:\d+(?:\.\d+)*(?:\.dev\d*)?)\+"
    r"(mpi(?:20|31|40))\.(mpich|openmpi|msmpi|impi)-"
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
    ],
    "mpi31-openmpi": [
        ("openmpi", ["3.1", "4.0", "4.1"]),
    ],
    "mpi40-mpich": [
        ("mpich", ["4.0", "4.1"]),
    ],
}
mpimap_macos = {
    "mpi31-mpich": [
        ("mpich", ["3.2", "4.1"]),
    ],
    "mpi31-openmpi": [
        ("openmpi", ["3.1", "4.1"]),
    ],
    "mpi40-mpich": [
        ("mpich", ["4.0", "4.1"]),
    ],
}
mpimap_windows = {
    "mpi20-msmpi": [
        ("msmpi", ["10.1.1"]),
    ],
    "mpi31-impi": [
        ("impi_rt", ["2021.6.0", "2021.10.0"]),
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
    for arch in ("x86_64", "AMD64"):
        if arch.lower() in archtag.lower():
            builds.append((osname, arch, mpiabi, py, (x, y)))
builds = sorted(builds, key=lambda r: (r[0].lower(), *r[1:]))


matrix = []
for entry in builds:
    osname, arch, mpiabi, py, (x, y) = entry
    if (x, y) >= (3, 12):  # TODO: update for cp312
        continue
    if (x, y) >= (3, 10) and py == "pp":  # TODO: update for pp310
        continue
    if osname == "Windows":
        if py == "pp" and (x, y) == (3, 7):
            continue  # mamba-org/setup-micromamba#133
    for mpiname, mpiversions in mpimap[osname][mpiabi]:
        for mpiversion in mpiversions:
            row = {
                "os": osname,
                "mpi": mpiname,
                "mpi-version": mpiversion,
                "py": f"{x}.{y}{pymap[py]}",
                "arch": arch,
            }
            matrix.append(row)
print(f"matrix-test-cf={json.dumps(matrix)}")


runners = {
    "Linux": [
        "ubuntu-20.04",
        "ubuntu-22.04",
    ],
    "macOS": [
        "macos-11",
        "macos-12",
        "macos-13",
    ],
    "Windows": [
        "windows-2019",
        "windows-2022",
    ],
}
matrix = []
for entry in builds:
    osname, arch, mpiabi, py, (x, y) = entry
    if (x, y) >= (3, 12):  # TODO: update for cp312
        continue
    if (x, y) >= (3, 10) and py == "pp":  # TODO: update for pp310
        continue
    std, _, mpi = mpiabi.partition("-")
    mpi = mpi.replace("impi", "intelmpi")
    mpispeclist = [mpi]
    if osname == "Linux" and mpi == "mpich":
        mpispeclist.append("intelmpi")
    pypy = "pypy-" if py == "pp" else ""
    pyspec = f"{pypy}{x}.{y}"
    for runner in runners[osname]:
        if runner == "ubuntu-22.04":
            if py == "cp" and (x, y) < (3, 7):
                continue
        if runner == "macos-13":
            if py == "cp" and (x, y) < (3, 8):
                continue
        if runner == "macos-12":
            if py == "cp" and (x, y) < (3, 7):
                continue
        if runner in "macos-11":
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
