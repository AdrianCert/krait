# krait-package

This package provides utilities for querying files within a specified location and retrieving package information based on the caller's context or relaying to other infos.

## Features

- **Convert Path to Qualified Name**: Convert a filesystem path to a Python package name.
- **Check Editable Package**: Determine if a package is in editable (development) mode.
- **Extract Package Origin**: Extract the origin of a package distribution.
- **Explore Package Location**: Yield paths to Python files within a package distribution.
- **Explore .pth Files**: Yield package locations specified in .pth files.
- **Extract Editable Package Files**: Retrieve Python file paths from editable package distributions.
- **Map Files to Packages**: Create a mapping of file paths to package names.
- **Retrieve Package Information**: Get package information based on the caller's context.
