import os
import sys
from pathlib import Path

import tomlkit
from packaging.version import InvalidVersion, Version

PREFIX_PACKAGES_BUNDLE = os.environ.get("PREFIX_PACKAGES_BUNDLE", "krait-")


def get_tag_name():
    if len(sys.argv) >= 2:  # noqa: PLR2004
        return sys.argv[1]
    return os.getenv("GITHUB_REF", "").split("/")[-1]


def parse_tag(tag_value):
    if "-" not in tag_value:
        sys.exit(
            f"Invalid tag format: {tag_value}. Expected <package-name>-<package-version>"
        )

    package_name, package_version = tag_value.rsplit("-", 1)

    try:
        return package_name, Version(package_version)
    except InvalidVersion:
        sys.exit(f"Invalid version format: {package_version}.")


def parse_pyproject(package_name):
    pyproject_file = Path(f"packages/{package_name}/pyproject.toml")

    if not pyproject_file.exists():
        sys.exit(f"pyproject.toml not found for package {package_name}")

    toml_content = tomlkit.parse(pyproject_file.read_text())

    try:
        package_version: str = toml_content["project"]["version"]
        package_name: str = toml_content["project"]["name"]
        if not package_name.startswith(PREFIX_PACKAGES_BUNDLE):
            sys.exit(
                f"Invalid package name. {package_name}. Expected to start with {PREFIX_PACKAGES_BUNDLE}"
            )

        return package_name.split(PREFIX_PACKAGES_BUNDLE)[1], Version(package_version)
    except KeyError:
        sys.exit(f"Invalid version format in toml: {package_version}.")
    except InvalidVersion:
        sys.exit("Error reading version/name from pyproject.toml")


def main():
    tag_name = get_tag_name()
    if not tag_name:
        sys.exit("No tag provided either GITHUB_REF or argument")

    pkg_name_tag, pkg_version_tag = parse_tag(tag_name)
    pkg_name_src, pkg_version_src = parse_pyproject(pkg_name_tag)

    print("Comparing founded values (tag/pyproject)")
    print(f"\tPackage name: {pkg_name_tag}/{pkg_name_src}")
    if pkg_name_src != pkg_name_tag:
        sys.exit("\t\tMISMATCH!")
    print(f"\tPackage version: {pkg_version_tag}/{pkg_version_src}")
    if pkg_version_src != pkg_version_tag:
        sys.exit("\t\tMISMATCH!")

    # Set the outputs for GitHub Actions
    print(f"::set-output name=package_name::{pkg_name_tag}")
    print(f"::set-output name=package_version::{pkg_version_tag}")


if __name__ == "__main__":
    main()
