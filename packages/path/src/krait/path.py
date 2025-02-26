import json
import mimetypes
import os
import shutil
import typing
from contextlib import contextmanager
from fnmatch import fnmatch
from pathlib import Path

import yaml

PathLike = typing.Union[str, Path]

# Add YAML mimetype
mimetypes.add_type("text/yaml", ".yaml")
mimetypes.add_type("text/yaml", ".yml")

_REG_HANDLER = {
    "application/json": json.loads,
    "text/yaml": yaml.safe_load,
}


def load_any(
    path: PathLike,
    mimetype: str = None,
    load_raw_text=True,
    load_raw_binary=False,
):
    """
    Load the content of a file based on its MIME type.

    Parameters
    ----------
    path : PathLike
        The path to the file to be loaded.
    mimetype : str, optional
        The MIME type of the file. If not provided, it will be guessed based on the file extension.
    load_raw_text : bool, default=True
        Whether to load the file as raw text if the MIME type is not recognized.
    load_raw_binary : bool, default=False
        Whether to load the file as raw binary if the MIME type is not recognized.

    Returns
    -------
    object
        The content of the file. The type of the returned object depends on the MIME type:
        - JSON: dict or list
        - YAML: dict or list
        - Raw text: str
        - Raw binary: bytes

    Raises
    ------
    ValueError
        If the file type is unsupported and neither `load_raw_text` nor `load_raw_binary` is True.
    """
    if mimetype is None:
        mimetype, _ = mimetypes.guess_type(path)
    if mimetype == "application/json":
        return json.loads(Path(path).read_text())
    if mimetype == "text/yaml":
        return yaml.safe_load(Path(path).read_text())
    if load_raw_text:
        return path.read_text()
    if load_raw_binary:
        return path.read_bytes()
    raise ValueError(f"Unsupported file type: {mimetype}")


class PathHelper:
    @staticmethod
    def resolve_outfile(path: PathLike, filename: str = "") -> Path:
        """
        Resolve the output file path based on the given path and filename.

        Parameters
        ----------
        path : PathLike
            The base path which can be a file or directory.
        filename : str, optional
            The filename to append if the base path is a directory, by default "".

        Returns
        -------
        Path
            The resolved output file path.

        Notes
        -----
        - If the given path is an existing file, it will be returned as is.
        - If the given path has a known file extension, it will be returned as is.
        - If the given path is an existing directory, the filename will be appended to it.
        - If the given path does not exist and has no extension, the filename will be appended to it.
        - The parent directories of the resolved path will be created if they do not exist.
        """
        res = Path(path)
        while True:
            if res.is_file():
                # if path is a existing file
                break
            mimetype, _ = mimetypes.guess_type(res)
            if mimetype:
                # if path is a file with extension
                break

            if res.is_dir():
                # if path is a existing directory or not path with extension
                res = res / filename
                break
            elif res.suffix:
                # if path is a not existing file with extension
                break

            res = res / filename
            break

        res.parent.mkdir(parents=True, exist_ok=True)

        return res

    @classmethod
    def fnmatch_iter(cls, target: str, patterns: typing.List[str]):
        """
        Check if a target string matches any pattern in a list of patterns.

        Parameters
        ----------
        target : str
            The target string to be matched against the patterns.
        patterns : list of str
            A list of patterns to match the target string against. Patterns starting with '!'
            are treated as exclusion patterns.

        Returns
        -------
        bool
            True if the target string matches any of the patterns, False if it matches any
            exclusion pattern, or if no patterns are provided.
        """
        exclusions = True
        for pattern in patterns:
            if pattern.startswith("!"):
                if fnmatch(target, pattern[1:]):
                    return False
                continue
            elif fnmatch(target, pattern):
                return True
            exclusions = False
        return exclusions

    @classmethod
    def remove_items(
        cls,
        from_path: PathLike,
        items: typing.List[str],
    ):
        """
        Remove specified items from a given directory path.

        Parameters
        ----------
        from_path : PathLike
            The directory path from which items will be removed.
        items : list of str
            A list of item names (files or directories) to be removed.

        Notes
        -----
        This method will remove both files and directories that match the names
        specified in the `items` list. If an item is a directory, it will be
        removed recursively. Any exceptions raised during the removal process
        will be caught and ignored.
        """
        for item in Path(from_path).iterdir():
            if not cls.fnmatch_iter(item.name, items):
                continue
            try:
                if item.is_dir():
                    shutil.rmtree(item.as_posix())
                    continue
                item.unlink()
            except Exception:
                pass

    @classmethod
    def move_items(
        cls,
        from_path: PathLike,
        to_path: PathLike,
        items: typing.List[str],
    ):
        """
        Move specified items from one directory to another.

        Parameters
        ----------
        from_path : PathLike
            The source directory path from which items will be moved.
        to_path : PathLike
            The destination directory path to which items will be moved.
        items : list of str
            A list of item names (patterns) to be moved.

        Returns
        -------
        None
        """
        for item in Path(from_path).iterdir():
            if not cls.fnmatch_iter(item.name, items):
                continue

            shutil.move(
                item.as_posix(),
                Path(to_path, item.name).as_posix(),
            )

    @staticmethod
    def relative_path(
        to_path: PathLike,
        from_path: PathLike,
    ):
        """
        Generate a relative path from `from_path` to `to_path`.

        Parameters
        ----------
        to_path : PathLike
            The target path to which the relative path is calculated.
        from_path : PathLike
            The base path from which the relative path is calculated.

        Returns
        -------
        str
            The relative path from `from_path` to `to_path` in POSIX format.

        Examples
        --------
        >>> relative_path('/home/user/docs', '/home/user')
        './docs'
        """
        return "./" + Path(os.path.relpath(str(to_path), str(from_path))).as_posix()


@contextmanager
def change_cwd(new_path: PathLike):
    """
    Context manager for changing the current working directory to the given path.

    Parameters
    ----------
    new_path : PathLike
        The path to change the current working directory to.

    Notes
    -----
    The current working directory is restored to its original value after the context is exited.
    """
    cwd: str = Path.cwd().resolve().absolute().as_posix()
    try:
        os.chdir(Path(new_path).as_posix())
        yield
    finally:
        os.chdir(cwd)
