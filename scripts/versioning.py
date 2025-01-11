import subprocess
import typing
from datetime import datetime

from hatchling.metadata.plugin.interface import MetadataHookInterface
from hatchling.plugin import hookimpl
from packaging.version import Version


class CalendarVersionMetadataHook(MetadataHookInterface):
    """
    Hatch metadata hook to populate 'project.version' based on the current date.
    """

    PLUGIN_NAME = "calendar-versions"

    def update(self, metadata: dict) -> None:
        """
        Update the project table's metadata.

        Parameters
        ----------
        metadata : dict
            A dictionary containing the project's metadata.

        Raises
        ------
        ValueError
            If 'version' is not listed in 'project.dynamic'.

        Notes
        -----
        This function checks if the version is already set using the command:
        `git tag --points-at HEAD`. If installed via uv, the git tags are not visible,
        unless the following is set in the configuration (pyproject.toml):
        [tool.uv]
        # https://docs.astral.sh/uv/reference/settings/#cache-keys
        cache-keys = [{ git = { commit = true, tags = true } }]

        """

        if "version" not in metadata.get("dynamic", []):
            raise ValueError(
                "Cannot setup 'version' when 'version' is not listed in 'project.dynamic'."
            )

        date_format: str = self.config.get("date-format", "%y.%m")
        vsc_counts = self.config.get("vsc-counts", True)
        vsc_prefix = self.config.get("vsc-prefix", "v")
        datetime_now = datetime.now()

        # check if the version is already seated
        # git tag --points-at HEAD
        # if installed via uv, the git tags are not visible, unless this is set
        # [tool.uv]
        # # https://docs.astral.sh/uv/reference/settings/#cache-keys
        # cache-keys = [{ git = { commit = true, tags = true } }]
        tags_list = subprocess.check_output(
            ["git", "tag", "--points-at", "HEAD"], text=True
        ).splitlines()

        if tags_list:
            tags_match = [tag for tag in tags_list if tag.startswith(vsc_prefix)]
            if tags_match:
                metadata["version"] = tags_match[0]
                return

        new_version = Version(datetime_now.strftime(date_format))

        if vsc_counts:
            version_query = "{}{}*".format(vsc_prefix, new_version)
            tags_list = subprocess.check_output(
                ["git", "tag", "-l", version_query],
                text=True,
            )
            new_version = "{}.{}".format(new_version, len(tags_list.splitlines()))

        metadata["version"] = str(new_version)


@hookimpl
def hatch_register_metadata_hook() -> typing.Type[CalendarVersionMetadataHook]:
    return CalendarVersionMetadataHook
