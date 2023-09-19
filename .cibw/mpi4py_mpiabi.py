# Author:  Lisandro Dalcin
# Contact: dalcinl@gmail.com
"""Support for MPI ABI."""
import importlib.machinery
import importlib.util
import os
import re
import sys
import warnings


def _verbose_info(message, verbosity=1):
    if sys.flags.verbose >= verbosity:
        print(f"# [{__spec__.parent}] {message}", file=sys.stderr)


_rpath_libmpi = []
if sys.platform == "darwin":
    _rpath_libmpi.extend([
        "@rpath",
        "/usr/local/lib",
        "/opt/homebrew/lib",
        "/opt/local/lib",
    ])


def _dlopen_libmpi(libmpi=None):  # noqa: C901
    # pylint: disable=import-outside-toplevel
    import ctypes as ct

    mode = ct.DEFAULT_MODE
    if os.name == "posix":
        mode = os.RTLD_NOW | os.RTLD_GLOBAL

    def dlopen(name):
        _verbose_info(f"trying to dlopen {name!r}")
        lib = ct.CDLL(name, mode)
        _ = lib.MPI_Get_version
        _verbose_info(f"MPI library from {name!r}")
        return lib

    def libmpi_names():
        if os.name == "posix":
            if sys.platform == "darwin":
                libmpi = "libmpi{0}.dylib"
            else:
                libmpi = "libmpi.so{0}"
            yield libmpi.format("")
            versions = (12, 80, 40, 20)
            for version in versions:
                yield libmpi.format(f".{version}")
        else:
            yield "impi.dll"
            yield "msmpi.dll"

    def libmpi_paths(path):
        for entry in path:
            entry = os.path.expandvars(entry)
            entry = os.path.expanduser(entry)
            if os.path.isdir(entry) or entry == "@rpath":
                for name in libmpi_names():
                    yield os.path.join(entry, name)
            else:
                yield entry

    if os.name == "posix":
        try:
            return dlopen(None)
        except (OSError, AttributeError):
            pass
    if libmpi is not None:
        path = libmpi.split(os.pathsep)
    else:
        path = _rpath_libmpi or None
    if path is not None:
        libmpi_iterable = libmpi_paths(path)
    else:
        libmpi_iterable = libmpi_names()
    errors = ["cannot load MPI library"]
    for filename in libmpi_iterable:
        try:
            return dlopen(filename)
        except OSError as exc:
            errors.append(str(exc))
        except AttributeError as exc:
            errors.append(str(exc))
    raise RuntimeError("\n".join(errors))


def _get_mpiabi_from_libmpi(libmpi=None):
    # pylint: disable=import-outside-toplevel
    import ctypes as ct
    lib = _dlopen_libmpi(libmpi)
    lib.MPI_Get_version.restype = ct.c_int
    lib.MPI_Get_version.argtypes = [ct.POINTER(ct.c_int)] * 2
    vmajor, vminor = ct.c_int(0), ct.c_int(0)
    ierr = lib.MPI_Get_version(ct.byref(vmajor), ct.byref(vminor))
    if ierr:  # pragma: no cover
        message = f"MPI_Get_version [ierr={ierr}]"
        raise RuntimeError(message)
    vmajor, vminor = vmajor.value, vminor.value
    if os.name == "posix":
        openmpi = hasattr(lib, "ompi_mpi_comm_self")
        family = "openmpi" if openmpi else "mpich"
    else:
        msmpi = hasattr(lib, "MSMPI_Get_version")
        family = "msmpi" if msmpi else "impi"
    return (vmajor, vminor), family


_pattern = re.compile(
    r"""
    \.? (
    (mpi)? (\W|_)* (
    (?P<vmajor>\d+) \.?
    (?P<vminor>\d)
    ) )? (\W|_)*
    (?P<family>\w+)?
    """,
    re.VERBOSE | re.IGNORECASE,
)
_pattern_strict = re.compile(
    r"mpi(?P<vmajor>\d+)(?P<vminor>\d)(-(?P<family>\w+))?",
    re.VERBOSE | re.IGNORECASE,
)


def _get_mpiabi_from_string(string, strict=False):
    pattern = _pattern_strict if strict else _pattern
    match = pattern.match(string)
    if match is None:
        message = f"invalid MPI ABI string {string!r}"
        raise RuntimeError(message)
    vmajor = match.group("vmajor") or "4"
    vminor = match.group("vminor") or "0"
    family = match.group("family") or ""
    return (int(vmajor), int(vminor)), family.lower() or None


_registry = {}


def _register(mpiabi):
    version, family = _get_mpiabi_from_string(mpiabi, strict=True)
    versions = _registry.setdefault(family, [])
    versions.append(version)
    versions.sort()


def _getenv(name):
    value = os.environ.get(name)
    if value and value.startswith("$"):
        if value.startswith("${") and value.endswith("}"):
            return _getenv(value[2:-1])
        if value[:5].lower() == "$env:":
            return _getenv(value[5:])
        return _getenv(value[1:])
    return value


def _get_mpiabi():
    string = _getenv("MPI4PY_MPIABI") or None
    libmpi = _getenv("MPI4PY_LIBMPI") or None
    if string is not None:
        version, family = _get_mpiabi_from_string(string)
    else:
        version, family = _get_mpiabi_from_libmpi(libmpi)
    versions = _registry.get(family)
    if versions:
        vmin, vmax = versions[0], versions[-1]
        version = max(vmin, min(version, vmax))
    return version, family


def _get_mpiabi_string():
    version, family = _get_mpiabi()
    vmajor, vminor = version
    suffix = f"-{family}" if family else ""
    return f"mpi{vmajor}{vminor}{suffix}"


class _Finder:
    """MPI ABI-aware extension module finder."""

    # pylint: disable=too-few-public-methods
    @classmethod
    def find_spec(cls, fullname, path, target=None):
        """Find MPI ABI extension module spec."""
        # pylint: disable=unused-argument
        pkgname, _, modname = fullname.rpartition(".")
        if pkgname == __spec__.parent and modname in {"MPI"}:
            mpiabi_string = _get_mpiabi_string()
            mpiabi_suffix = f".{mpiabi_string}"
            _verbose_info(f"MPI ABI extension suffix: {mpiabi_suffix!r}")
            extension_suffixes = importlib.machinery.EXTENSION_SUFFIXES
            spec_from_file_location = importlib.util.spec_from_file_location
            for entry in path:
                for extension_suffix in extension_suffixes:
                    filename = f"{modname}{mpiabi_suffix}{extension_suffix}"
                    location = os.path.join(entry, filename)
                    if os.path.isfile(location):
                        return spec_from_file_location(fullname, location)
            warnings.warn(
                f"unsupported MPI ABI {mpiabi_string!r}",
                category=RuntimeWarning, stacklevel=2,
            )
        return None


def _install_finder():
    if _Finder not in sys.meta_path:
        sys.meta_path.append(_Finder)
