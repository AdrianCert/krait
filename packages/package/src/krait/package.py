"""
Utilities for working with Python package distributions.

Include functions to map file paths to package names, check if a package is in editable mode,
and extract package origins. It also defines the `PackageInfo` class for querying package
information and resources.
"""

import inspect
import os
import sys
import typing
from pathlib import Path

import importlib_metadata
from krait.signal import signal


def path2qualname(path) -> typing.Optional[str]:
    """
    Convert a filesystem path to a Python package name.

    Parameters
    ----------
    path: str or Path
        The filesystem path to convert.

    Returns
    -------
    str or None
        The corresponding Python package name if the path is within a site-package directory,
        otherwise None.

    Notes
    -----
    This function resolves the given path and checks if it is within any of the directories
    listed in `sys.path`. If it is, the function returns the relative path from the site-package
    directory, with directory separators replaced by dots. If the path is not within any
    site-package directory, the function returns None.
    """
    path = Path(path).resolve()
    res = None
    for loc in sys.path:
        candidate = Path(loc)
        if candidate in path.parents:
            if res:
                if len(res.parents) < len(candidate.parents):
                    res = candidate
            else:
                res = candidate

    if res:
        return os.path.splitext(  # noqa: PTH122
            os.path.relpath(
                path,
                res,
            )
        )[0].replace(os.sep, ".")

    return None


def is_editable(dist):
    """
    Check if a distribution is in editable (development) mode.

    Parameters
    ----------
    dist : Distribution
        The distribution object to check.

    Returns
    -------
    bool
        True if the distribution is in editable mode, False otherwise.

    Notes
    -----
    The function checks if the distribution is in editable mode by inspecting the `origin` attribute.
    """
    dir_info = getattr(dist.origin, "dir_info", None)
    return getattr(dir_info, "editable", False)


def extract_package_origin(dist):
    """
    Extract the origin of a package distribution.

    Parameters
    ----------
    dist : Distribution
        The distribution object to extract the origin from.

    Returns
    -------
    Path or None
        The origin of the package distribution.
    """
    try:
        url: str = dist.origin.url

        if url.startswith("file:"):
            url = url[5:].strip("/").strip("\\")
        location = Path(url).resolve()
        return location
    except AttributeError:
        return None


def explore_package_location(path: Path):
    """
    Explore the location of a package distribution.

    Parameters
    ----------
    path : Path
        The path to the package distribution.

    Yields
    ------
    Path
        Paths to Python files within the package distribution.
    """
    # search for all python files in the distribution
    # maybe we should also search for .pyc files?
    # or others kind of files?
    # for now, we will only search for .py files
    yield from path.glob("**/*.py")


def explore_pth_file(*files: typing.Iterable[Path]):
    r"""
    Explore the locations specified in .pth files and yield package locations.

    Parameters
    ----------
    *files : typing.Iterable[Path]
        One or more .pth files to be explored.

    Yields
    ------
    Path
        Paths to the package locations extracted from the .pth files.

    Notes
    -----
    This function reads each .pth file, extracts the paths specified in the file,
    and yields the package locations. Lines starting with "import " or "import\t"
    are ignored.

    See Also
    --------
    https://docs.python.org/3/library/site.html
        Documentation on .pth files and their usage.

    """
    for file in files:
        # extract the locations of the distribution from the .pth file
        # and explore the distribution directory
        if not file.exists():
            continue
        for content in Path(file).read_text().splitlines():
            # maybe there is a need to handle as well the case where the content is import statement
            # but for now, we will ignore it since this is a dangerous operation to execute arbitrary code
            # consider if there is a demand for this feature to properly research all implications
            if content.startswith("import ") or content.startswith("import\t"):
                continue
            location = Path(content).resolve()
            yield from explore_package_location(location)


def extract_editable_package_files(
    dist: importlib_metadata.Distribution, pth_files: typing.List[Path] = None
):
    """
    Extract the file paths of all Python files in an editable (development mode) package distribution.

    Parameters
    ----------
    dist : Distribution
        The distribution object representing the package.

    Yields
    ------
    Path
        Paths to Python files within the package distribution.

    Notes
    -----
    - The function first checks if the distribution is in editable mode by using the `is_editable` function.
    - If the distribution is in editable mode, it searches for all Python files within the distribution directory.
    - The function handles `.pth` files to locate the distribution directory and explore it for Python files.
    - If no `.pth` files are found, it falls back to extracting the origin of the package distribution.
    - This approach assumes that Python files may be located either in the root directory or within a `src` directory.
    """
    if not is_editable(dist):
        return

    _pth_loaded = False
    _pth_files = pth_files or (f.locate() for f in dist.files if f.suffix == ".pth")
    for file in explore_pth_file(*_pth_files):
        yield file
        _pth_loaded = True

    if _pth_loaded:
        return

    location = extract_package_origin(dist)
    if location:
        # depending on how the distribution is built, the python files can be in the root or src directory
        # we will search for all python files in the distribution and map them to the package name
        # this is a very naive approach, but it should work for most cases
        yield from explore_package_location(location)
        return


def files4package(only_names=False, include_editable=False):
    """
    Retrieve a mapping of file paths to package names.

    Parameters
    ----------
    only_names : bool, optional
        If True, only the file names will be included in the result.
        Otherwise, the full file paths will be included. Default is False.
    include_editable : bool, optional
        If True, include files from editable packages. Default is False.

    Returns
    -------
    dict
        A dictionary where the keys are file paths (or names) and the values are package names.
    """

    def _filter(file: importlib_metadata.PackagePath, context: dict = {}):
        if file.suffix == ".pth":
            if "pth" in context:
                context["pth"].append(file.locate())
            return False
        return ".dist-info" not in str(file)

    res = {}
    for dist in importlib_metadata.distributions():
        ref = dist.name if only_names else dist
        context = {"pth": []} if include_editable else {}
        res.update(
            {
                file.locate(): ref
                for file in dist.files
                if _filter(file, context=context)
            }
        )

        if not include_editable:
            continue

        res.update(
            {
                file: ref
                for file in extract_editable_package_files(
                    dist, pth_files=context["pth"]
                )
            }
        )

    return res


class PackageInfo:
    """
    Provide package information and various utilities related to the package.

    Parameters
    ----------
    name : str
        The name of the package.

    """

    def __init__(self, name):
        self.name = name
        self.dist = importlib_metadata.distribution(self.name)

    @signal
    def map_file2package():
        """Map for file paths to package names."""
        return files4package(only_names=True, include_editable=True)

    @classmethod
    def from_filepath(cls, file_path):
        """
        Create an instance of the class based on a file path.

        Parameters
        ----------
        cls : type
            The class itself.
        file_path : str or Path
            The file path to map to a package.

        Returns
        -------
        cls or None
            An instance of the class if the file path is mapped to a package, otherwise None.
        """
        package = cls.map_file2package.get(Path(file_path).resolve(), None)
        if not package:
            return None
        return cls(package)

    @classmethod
    def from_caller(cls, relative_frame=1):
        """
        Create an instance of the class based on the caller's file location.

        Parameters
        ----------
        cls : type
            The class itself.
        relative_frame : int, optional
            The stack frame index to inspect. Default is 1, which refers to the caller's frame.

        Returns
        -------
        cls or None
            An instance of the class if the caller's file is mapped to a package, otherwise None.
        """
        try:
            return cls.from_filepath(inspect.stack()[relative_frame].filename)
        except Exception:
            return None

    @signal
    def editable(self):
        """
        Check if the distribution is editable.

        Returns
        -------
        bool
            True if the distribution is editable, False otherwise.
        """
        return is_editable(self.dist)

    @property
    def version(self):
        """
        Get the version of the package.

        Returns
        -------
        str
            The version of the package as a string.
        """
        return self.dist.version

    @property
    def dist_name(self):
        """
        Get the distribution name.

        Returns
        -------
        str
            The name of the distribution.
        """
        return self.dist.name

    @signal
    def location(self) -> Path:
        """
        Return the location of the distribution file.

        Returns
        -------
        Path
            The path to the distribution file.
        """
        return self.dist.locate_file("")

    @property
    def resource(self):
        """
        Get the path to the resources directory.

        If the package is editable, the path is derived from the package origin.
        Otherwise, the path is derived from the package location.

        Returns
        -------
        pathlib.Path
            The path to the resources directory.
        """
        if self.editable:
            return extract_package_origin(self.dist) / "resources"
        return self.location.parent / "resources"

    def resolve_resource(self, uri: str, not_found_ok=False):
        """
        Resolve a resource URI to a file path.

        Parameters
        ----------
        uri : str
            The resource URI to resolve. Should start with "res://".
        not_found_ok : bool, optional
            If True, return None instead of raising an exception when the resource is not found (default is False).

        Returns
        -------
        pathlib.Path or None
            The resolved file path if the resource is found, otherwise None if `not_found_ok` is True.

        Raises
        ------
        FileNotFoundError
            If the resource is not found and `not_found_ok` is False.
        """
        if uri.startswith("res://"):
            filename = uri[6:]
        candidate = self.resource / filename
        if candidate.exists():
            return candidate
        if not_found_ok:
            return None
        raise FileNotFoundError(f"Resource not found: {uri}")

    def query_files(self, file_path):
        """
        Query files in the specified location that match the given file path pattern.

        Parameters
        ----------
        file_path : str
            The file path pattern to search for within the location.

        Yields
        ------
        pathlib.Path
            Paths of files that match the given file path pattern.
        """
        yield from self.location.glob(f"**/*{file_path}")


def this(relative_frame=1):
    """
    Retrieve package information from the caller's context.

    Parameters
    ----------
    relative_frame : int, optional
        The number of frames to go back in the stack to find the caller's context.
        Default is 1.

    Returns
    -------
    PackageInfo
        An instance of `PackageInfo` containing information about the package
        from the caller's context.
    """
    return PackageInfo.from_caller(relative_frame=relative_frame + 1)
