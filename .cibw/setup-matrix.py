import argparse
import collections
import copy
import fnmatch
import json

parser = argparse.ArgumentParser()
parser.add_argument("--os", nargs="*")
parser.add_argument("--py", nargs="*")
opts = parser.parse_args()


def py(py, x, y_min, y_max):
    return [f"{py}{x}{y}" for y in range(y_min, y_max + 1)]


def cp3(y_min=8, y_max=13):
    return py("cp", 3, y_min, y_max)


def pp3(y_min=8, y_max=10):
    return py("pp", 3, y_min, y_max)


OS_ARCH_PY = {
    "Linux": {
        "aarch64": cp3() + pp3(),
        "x86_64": cp3() + pp3(),
    },
    "macOS": {
        "arm64": cp3(),
        "x86_64": cp3() + pp3(),
    },
    "Windows": {
        "AMD64": cp3() + pp3(),
    },
}

MPI_ABI_POSIX = [
    "mpich",
    "openmpi",
]
MPI_ABI_WINNT = [
    "impi",
    "msmpi",
]
MPI_ABI = {
    "Linux": MPI_ABI_POSIX[:],
    "macOS": MPI_ABI_POSIX[:],
    "Windows": MPI_ABI_WINNT[:],
}

GHA_RUNNER = {
    "Linux": {
        "aarch64": "ubuntu-24.04-arm",
        "x86_64": "ubuntu-24.04",
        None: "ubuntu-latest"
    },
    "macOS": {
        "arm64": "macos-15",
        "x86_64": "macos-13",
        None: "macos-latest"
    },
    "Windows": {
        "AMD64": "windows-2022",
        None: "windows-latest"
    },
}

os_arch_py = copy.deepcopy(OS_ARCH_PY)
if opts.os and not set(opts.os) & {"*", "all"}:
    select = collections.defaultdict(list)
    for entry in opts.os:
        for sep in "=+/@":
            entry = entry.replace(sep, "-")
        os, _, arch = entry.partition("-")
        assert os in OS_ARCH_PY, f"os={os!r}"
        if arch and arch not in ("*", "all"):
            assert arch in OS_ARCH_PY[os], f"os={os!r} arch={arch!r}"
            if arch not in select[os]:
                select[os].append(arch)
        else:
            for arch in OS_ARCH_PY[os]:
                if arch not in select[os]:
                    select[os].append(arch)
    os_arch_py = collections.defaultdict(dict)
    for os in select:
        for arch in select[os]:
            os_arch_py[os][arch] = OS_ARCH_PY[os][arch][:]
if opts.py and not set(opts.py) & {"*", "all"}:
    for os in os_arch_py:
        for arch in os_arch_py[os]:
            select = []
            for pat in opts.py:
                for xp in fnmatch.filter(os_arch_py[os][arch], pat):
                    if xp not in select:
                        select.append(xp)
            os_arch_py[os][arch][:] = select

matrix_build = [
    {
        "os": os,
        "arch": arch,
        "py": py,
        "mpi-abi": mpi_abi,
        "runner": GHA_RUNNER[os][arch],
    }
    for os in os_arch_py
    for arch in os_arch_py[os]
    for py in os_arch_py[os][arch]
    for mpi_abi in MPI_ABI[os]
]

matrix_merge = [
    {
        "os": os,
        "arch": arch,
        "runner": GHA_RUNNER[os][None],
    }
    for os in os_arch_py
    for arch in os_arch_py[os]
]

matrix_test = []
for build in matrix_build:
    os = build["os"]
    arch = build["arch"]
    pytag = build["py"]
    mpi_abi = build["mpi-abi"]
    runner = GHA_RUNNER[os][arch]
    if pytag.startswith("pp"):
        continue
    pyver = pytag[2:3] + "." + pytag[3:]
    mpilist = [mpi_abi]
    if (os, arch, mpi_abi) == ("Linux", "x86_64", "mpich"):
        mpilist.insert(0, "impi")
    matrix_test += [
        {
            "mpi": mpi,
            "py": pyver,
            "os": os,
            "arch": arch,
            "runner": runner,
        }
        for mpi in mpilist
    ]

print(f"matrix-build={json.dumps(matrix_build)}")
print(f"matrix-merge={json.dumps(matrix_merge)}")
print(f"matrix-test={json.dumps(matrix_test)}")
