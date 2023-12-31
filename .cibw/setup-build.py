import argparse
import collections
import copy
import json

parser = argparse.ArgumentParser()
parser.add_argument("--os", nargs="*")
parser.add_argument("--py", nargs="*")
opts = parser.parse_args()


def py(py, x, y_min, y_max):
    return [f"{py}{x}{y}" for y in range(y_min, y_max + 1)]


def cp3(y_min=6, y_max=12):
    return py("cp", 3, y_min, y_max)


def pp3(y_min=7, y_max=10):
    return py("pp", 3, y_min, y_max)


OS_ARCH_PY = {
    "Linux": {
        "x86_64": cp3() + pp3(),
        "aarch64": cp3() + pp3(),
        "ppc64le": cp3(),
    },
    "macOS": {
        "x86_64": cp3() + pp3(),
        "arm64": cp3(8, 12),
    },
    "Windows": {
        "AMD64": cp3() + pp3(),
    },
}

MPI_ABI_POSIX = [
    f"mpi{std}-{mpi}"
    for std in (31, 40)
    for mpi in ("mpich", "openmpi")
    if (std, mpi) != (40, "openmpi")
]
MPI_ABI_WINNT = [
    f"mpi{std}-{mpi}"
    for std, mpi in (
        (20, "msmpi"),
        (31, "impi"),
    )
]
MPI_ABI = {
    "Linux": MPI_ABI_POSIX[:],
    "macOS": MPI_ABI_POSIX[:],
    "Windows": MPI_ABI_WINNT[:],
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
            os_arch_py[os][arch][:] = opts.py

matrix_build = [
    {"os": os, "arch": arch, "py": py, "mpi-abi": mpi_abi}
    for os in os_arch_py
    for arch in os_arch_py[os]
    for py in os_arch_py[os][arch]
    for mpi_abi in MPI_ABI[os]
]
matrix_merge = [
    {"os": os, "arch": arch}
    for os in os_arch_py
    for arch in os_arch_py[os]
]
os_arch_list = [
    "{os}-{arch}".format(**row)
    for row in matrix_merge
]

print(f"matrix-build={json.dumps(matrix_build)}")
print(f"matrix-merge={json.dumps(matrix_merge)}")
print(f"os-arch-list={json.dumps(os_arch_list)}")
