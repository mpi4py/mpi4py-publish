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
        print(f"# [{__name__}] {message}", file=sys.stderr)


def _site_prefixes():
    prefixes = []
    site = sys.modules.get("site")
    if site is not None:
        if sys.exec_prefix != sys.base_exec_prefix:
            venv_base = sys.exec_prefix
            prefixes.append(venv_base)
        if site.ENABLE_USER_SITE:
            user_base = os.path.abspath(site.USER_BASE)
            prefixes.append(user_base)
        if sys.base_exec_prefix in site.PREFIXES:
            system_base = sys.base_exec_prefix
            if os.name == "posix":
                if system_base != "/usr":
                    prefixes.append(system_base)
            else:
                prefixes.append(system_base)
    return prefixes


def _dlopen_rpath():
    rpath = []

    def add_rpath(*directory):
        path = os.path.join(*directory)
        if path not in rpath:
            rpath.append(path)

    def add_rpath_prefix(prefix):
        if os.name == "posix":
            add_rpath(prefix, "lib")
        else:
            add_rpath(prefix, "DLLs")
            add_rpath(prefix, "Library", "bin")

    for prefix in _site_prefixes():
        add_rpath_prefix(prefix)

    add_rpath("")

    if sys.platform == "darwin":
        add_rpath("/usr/local/lib")
        add_rpath("/opt/homebrew/lib")
        add_rpath("/opt/local/lib")

    return rpath


def _dlopen_libmpi(libmpi=None):  # noqa: C901
    # pylint: disable=too-many-statements
    # pylint: disable=import-outside-toplevel
    import ctypes as ct

    mode = ct.DEFAULT_MODE
    if os.name == "posix":
        mode = os.RTLD_NOW | os.RTLD_GLOBAL | os.RTLD_NODELETE

    def dlopen(name):
        _verbose_info(f"trying to dlopen {name!r}")
        lib = ct.CDLL(name, mode)
        _ = lib.MPI_Get_version
        _verbose_info(f"MPI library from {name!r}")
        if name is not None and sys.platform == "linux":
            if hasattr(lib, "I_MPI_Check_image_status"):
                if os.path.basename(name) != name:
                    dlopen_impi_libfabric(os.path.dirname(name))
        return lib

    def dlopen_impi_libfabric(libdir):
        ofi_internal = (
            os.environ.get("I_MPI_OFI_LIBRARY_INTERNAL", "").lower()
            in ("", "1", "y", "on", "yes", "true", "enable")
        )
        ofi_required = os.environ.get("I_MPI_FABRICS") != "shm"
        ofi_library_path = os.path.join(libdir, "libfabric")
        ofi_provider_path = os.path.join(ofi_library_path, "prov")
        ofi_filename = os.path.join(ofi_library_path, "libfabric.so.1")
        if ofi_internal and ofi_required and os.path.isfile(ofi_filename):
            if "FI_PROVIDER_PATH" not in os.environ:
                if os.path.isdir(ofi_provider_path):
                    os.environ["FI_PROVIDER_PATH"] = ofi_provider_path
            ct.CDLL(ofi_filename, mode)
            _verbose_info(f"OFI library from {ofi_filename!r}")

    def libmpi_names():
        if os.name == "posix":
            if sys.platform == "darwin":
                libmpi = "libmpi{0}.dylib"
            else:
                libmpi = "libmpi.so{0}"
            yield libmpi.format("")
            versions = (12, 40, 20)
            for version in versions:
                yield libmpi.format(f".{version}")
        else:
            yield "impi.dll"
            yield "msmpi.dll"

    def libmpi_paths(path):
        rpath = "@rpath" if sys.platform == "darwin" else ""
        for entry in path:
            entry = entry or rpath
            entry = os.path.expandvars(entry)
            entry = os.path.expanduser(entry)
            if entry == rpath or os.path.isdir(entry):
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
        path = _libmpi_rpath or _dlopen_rpath() or [""]
    errors = ["cannot load MPI library"]
    for filename in libmpi_paths(path):
        try:
            return dlopen(filename)
        except OSError as exc:
            errors.append(str(exc))
        except AttributeError as exc:
            errors.append(str(exc))
    raise RuntimeError("\n".join(errors))


_libmpi_rpath = []  # type: list[str]


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


def _get_mpiabi():
    version = getattr(_get_mpiabi, "version", None)
    family = getattr(_get_mpiabi, "family", None)
    if version is None:
        string = os.environ.get("MPI4PY_MPIABI") or None
        libmpi = os.environ.get("MPI4PY_LIBMPI") or None
        if string is not None:
            version, family = _get_mpiabi_from_string(string)
        else:
            version, family = _get_mpiabi_from_libmpi(libmpi)
        _get_mpiabi.version = version  # pyright: ignore
        _get_mpiabi.family = family  # pyright: ignore
    return version, family


_registry = {}  # type: dict[str, dict[str, list[tuple[int, int]]]]


def _register(module, mpiabi):
    version, family = _get_mpiabi_from_string(mpiabi, strict=True)
    versions = _registry.setdefault(module, {}).setdefault(family, [])
    versions.append(version)
    versions.sort()


def _get_mpiabi_suffix(module):
    if module not in _registry:
        return None
    version, family = _get_mpiabi()
    versions = _registry[module].get(family)
    if versions:
        vmin, vmax = versions[0], versions[-1]
        version = max(vmin, min(version, vmax))
    vmajor, vminor = version
    family_tag = f"-{family}" if family else ""
    return f".mpi{vmajor}{vminor}{family_tag}"


class _Finder:
    """MPI ABI-aware extension module finder."""

    # pylint: disable=too-few-public-methods
    @classmethod
    def find_spec(cls, fullname, path, target=None):
        """Find MPI ABI extension module spec."""
        # pylint: disable=unused-argument
        mpiabi_suffix = _get_mpiabi_suffix(fullname)
        if mpiabi_suffix is None:
            return None
        _verbose_info(f"MPI ABI extension module: {fullname!r}")
        _verbose_info(f"MPI ABI extension suffix: {mpiabi_suffix!r}")
        ext_name = fullname.rpartition(".")[2]
        extension_suffixes = importlib.machinery.EXTENSION_SUFFIXES
        spec_from_file_location = importlib.util.spec_from_file_location
        for entry in path:
            for ext_suffix in extension_suffixes:
                filename = f"{ext_name}{mpiabi_suffix}{ext_suffix}"
                location = os.path.join(entry, filename)
                if os.path.isfile(location):
                    return spec_from_file_location(fullname, location)
        warnings.warn(
            f"unsupported MPI ABI {mpiabi_suffix[1:]!r}",
            category=RuntimeWarning, stacklevel=2,
        )
        return None


def _install_finder():
    if _Finder not in sys.meta_path:
        sys.meta_path.append(_Finder)


def _set_windows_dll_path():  # noqa: C901
    impi_root = os.environ.get("I_MPI_ROOT")
    impi_library_kind = (
        os.environ.get("I_MPI_LIBRARY_KIND") or
        os.environ.get("library_kind") or
        "release"
    )
    impi_ofi_library_internal = (
        os.environ.get("I_MPI_OFI_LIBRARY_INTERNAL", "").lower()
        not in ("0", "no", "off", "false", "disable")
    )
    impi_ofi_library_path = (
        ("opt", "mpi", "libfabric", "bin"),
        ("libfabric", "bin"),
        ("bin", "libfabric"),
        ("libfabric",),
    )

    msmpi_bin = os.environ.get("MSMPI_BIN")
    if not msmpi_bin:
        msmpi_root = os.environ.get("MSMPI_ROOT")
        if msmpi_root:
            msmpi_bin = os.path.join(msmpi_root, "bin")

    dllpath = []

    def add_dllpath(*directory, dll=""):
        path = os.path.join(*directory)
        if path not in dllpath:
            filename = os.path.join(path, f"{dll}.dll")
            if os.path.isfile(filename):
                dllpath.append(path)

    def add_dllpath_impi(*rootdir):
        if impi_ofi_library_internal:
            for subdir in impi_ofi_library_path:
                add_dllpath(*rootdir, *subdir, dll="libfabric")
        add_dllpath(*rootdir, "bin", impi_library_kind, dll="impi")
        add_dllpath(*rootdir, "bin", dll="impi")

    def add_dllpath_msmpi(*bindir):
        add_dllpath(*bindir, dll="msmpi")

    for prefix in _site_prefixes():
        add_dllpath_impi(prefix, "Library")
        add_dllpath_msmpi(prefix, "Library", "bin")
    if impi_root:
        add_dllpath_impi(impi_root)
    if msmpi_bin:
        add_dllpath_msmpi(msmpi_bin)

    ospath = os.environ["PATH"].split(os.path.pathsep)
    for entry in dllpath:
        if entry not in ospath:
            ospath.append(entry)
    os.environ["PATH"] = os.path.pathsep.join(ospath)

    if os.name == "nt":
        if hasattr(os, "add_dll_directory"):
            for entry in dllpath:
                os.add_dll_directory(entry)
