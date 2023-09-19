# mpi4py-publish

This repository builds and publishes [mpi4py](https://github.com/mpi4py/mpi4py)
wheels able to run in a variety of operating systems (*Linux*, *macOS*,
*Windows*), processor architectures (*AMD64*, *ARM64*, *PPC64*), MPI
implementations (*MPICH*, *Open MPI*, *Intel MPI*, *HPE Cray MPI*, *MVAPICH*,
*Microsoft MPI*), and Python implementations (*CPython*, *PyPy*).

mpi4py wheels are uploaded to the [Anaconda.org](https://anaconda.org/mpi4py)
package server. These wheels can be installed with `pip` specifying the
alternative index URL:

```
python -m pip install -i https://pypi.anaconda.org/mpi4py/simple mpi4py
```

These wheels can be installed (with `pip`) in [conda](https://docs.conda.io)
environments and they should work out of the box, for any MPI package provided
by [conda-forge](https://conda-forge.org/), and without any special tweak to
environment variables. Otherwise, these wheels can be installed in standard
Python virtual environments and use an externally-provided MPI runtime coming
from the system package manager, sysadmin-maintained builds accessible via
module files, or customized user builds, as per the following requirements:

* Linux (`x86_64`, `aarch64`, `ppc64le`):

  - Requires MPICH and any ABI-compatible derivatives like Intel MPI,
    HPE Cray MPI, and MVAPICH.

  - Requires Open MPI and any ABI-compatible derivative.

  - May need setting the `LD_LIBRARY_PATH` environment variable such that the
    dynamic linker is able to find at runtime the MPI shared library file
    (`libmpi.so.??`).

* macOS (`x86_64`, `arm64`):

  - Requires MPICH or Open MPI installed (either manually or via a package
    manager) in the standard prefix `/usr/local`.

  - Requires MPICH or Open MPI installed via
    [Homebrew](https://brew.sh/) in the default prefix `/opt/homebrew`.

  - Requires MPICH or Open MPI installed via
    [MacPorts](https://www.macports.org/) in the default prefix `/opt/local`.

* Windows (`AMD64`):

  - Requires Intel MPI for Windows or Microsoft MPI.

  - May need setting the `I_MPI_ROOT` or `MSMPI_BIN` environment variable such
    that the MPI dynamic link library (DLL) file (`impi.dll` or `msmpi.dll`)
    can be found at runtime.
