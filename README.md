# mpi4py-publish

This repository builds and publishes [mpi4py](https://github.com/mpi4py/mpi4py)
Python wheels able to run in a variety of

- operating systems: *Linux*, *macOS*, *Windows*;
- processor architectures: *AMD64*, *ARM64*, *PPC64*;
- MPI implementations: *MPICH*, *Open MPI*, *MVAPICH*,
  *Intel MPI*, *HPE Cray MPICH*, *Microsoft MPI*;
- Python implementations: *CPython*, *PyPy*.

mpi4py wheels are uploaded to the [Anaconda.org](https://anaconda.org/mpi4py)
package server. These wheels can be installed with `pip` specifying the
alternative index URL:

```
python -m pip install -i https://pypi.anaconda.org/mpi4py/simple mpi4py
```

mpi4py wheels can be installed (with `pip`) in [conda](https://docs.conda.io)
environments and they should work out of the box, for any MPI package provided
by [conda-forge](https://conda-forge.org/), and without any special tweak to
environment variables. Otherwise, these wheels can be installed in standard
Python virtual environments and use an externally-provided MPI runtime coming
from the system package manager, sysadmin-maintained builds accessible via
module files, or customized user builds.


## Linux (`x86_64`, `aarch64`, `ppc64le`):

The Linux wheels require

- [MPICH](https://mpich.org)
  and any other ABI-compatible derivative like
  [MVAPICH](https://mvapich.cse.ohio-state.edu/),
  [Intel MPI](https://software.intel.com/intel-mpi-library),
  [HPE Cray MPICH](https://cpe.ext.hpe.com/docs/mpt/mpich/).

- [Open MPI](https://open-mpi.org)
  and any other ABI-compatible derivative.

Users may need to set the `LD_LIBRARY_PATH` environment variable such that the
dynamic linker is able to find at runtime the MPI shared library file
(`libmpi.so.??`).

### Debian/Ubuntu

On Debian/Ubuntu systems, Open MPI is the default MPI implementation and most
of the MPI-based applications and libraries provided by the distribution depend
on Open MPI. Nonetheless, MPICH is also available to users for installation.
However, due to legacy reasons, the ABI is slightly broken: the MPI shared
library file is named `libmpich.so.12` instead of `libmpi.so.12` as required by
the [MPICH ABI Compatibility Initiative](https://www.mpich.org/abi/).

Users without `sudo` access can workaround this issue creating a symbolic link
anywhere in their home directory and appending to `LD_LIBRARY_PATH`.

```sh
mkdir -p ~/.local/lib
multiarch=$(arch | sed s/^ppc/powerpc/)-linux-gnu
ln -s /usr/lib/$multiarch/libmpich.so.12 ~/.local/lib/libmpi.so.12
export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:~/.local/lib
```

A system-wide fix for all users requires `sudo` access:

```sh
multiarch=$(arch | sed s/^ppc/powerpc/)-linux-gnu
sudo ln -sr /usr/lib/$multiarch/libmpi{ch,}.so.12
```

### Fedora/RHEL

On Fedora/RHEL systems, both MPICH and Open MPI are available for installation.
There is no default or preferred MPI implementation. Instead, users must select
their favorite MPI implementation by loading the proper MPI module.

```sh
module load mpi/mpich-$(arch)    # for MPICH
module load mpi/openmpi-$(arch)  # for Open MPI
```

After loading the requested MPI module, the `LD_LIBRARY_PATH` environment
variable should be properly setup.

## HPE Cray

Users must load the `cray-mpich-abi` module. For further details, refer to
[`man intro_mpi`](https://cpe.ext.hpe.com/docs/mpt/mpich/intro_mpi.html#using-mpich-abi-compatibility).


## macOS (`x86_64`, `arm64`):

The macOS wheels require

- MPICH or Open MPI installed (either manually or via a package manager)
  in the standard prefix `/usr/local`.

- MPICH or Open MPI installed via
  [Homebrew](https://brew.sh/) in the default prefix `/opt/homebrew`.

- MPICH or Open MPI installed via
  [MacPorts](https://www.macports.org/) in the default prefix `/opt/local`.


## Windows (`AMD64`):

The Windows wheels require

- [Intel MPI](https://software.intel.com/intel-mpi-library).

- [Microsoft MPI](https://learn.microsoft.com/message-passing-interface/microsoft-mpi).

User may need to set the `I_MPI_ROOT` or `MSMPI_BIN` environment variables such
that the MPI dynamic link library (DLL) file (`impi.dll` or `msmpi.dll`) can be
found at runtime.
