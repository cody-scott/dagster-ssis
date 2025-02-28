from typing import Any, Sequence

from dagster import (
    AssetSpec,
)


class SSISAsset:
    _folder_name: str
    _project_name: str
    _package_name: str

    _key_prefix: Sequence[str]
    _asset_list: Sequence[AssetSpec]
    _include_ssis_asset: bool
    _asset_spec_kwargs: dict[str, Any]

    @property
    def fqn(self):
        return f"{self._folder_name}/{self._project_name}/{self._package_name}"

    def __init__(
        self,
        project_name: str,
        package_name: str,
        folder_name: str = "Catalog",
        key_prefix: Sequence[str] = ["SSIS"],
        asset_list: Sequence[AssetSpec] = [],
        include_ssis_asset: bool = True,
        asset_spec_kwargs: dict[str, Any] | None = None,
    ):
        """Create an asset representing an SSIS package.

        Args:
            project_name (str): name of ssis project
            package_name (str): name of ssis package including
            folder_name (str, optional): Name of folder. Defaults to "Catalog".
            key_prefix (Sequence[str], optional): key prefixes to pass to AssetSpec. Defaults to ["SSIS"].
            asset_list (Sequence[AssetSpec], optional): List of assets associated with the package. Defaults to [].
            include_ssis_asset (bool, optional): Should the `asset_specs` property include an asset for the package itself. Defaults to True.
            asset_spec_kwargs (dict[str, Any], optional): Parameters to pass to AssetSpec
        """
        self._folder_name = folder_name
        self._project_name = project_name
        self._package_name = package_name

        self._key_prefix = key_prefix
        self._asset_list = asset_list
        self._include_ssis_asset = include_ssis_asset

        asset_spec_kwargs = asset_spec_kwargs if asset_spec_kwargs is not None else {}
        self._asset_spec_kwargs = asset_spec_kwargs

    def __repr__(self):
        return self.fqn

    @property
    def ssis_asset_spec(self):
        key = self._key_prefix + [
            self._folder_name,
            self._project_name,
            self._package_name.replace(".", "_"),
            self._package_name.replace(".dtsx", ""),
        ]
        spec_args = self._asset_spec_kwargs | {"key": key}
        return AssetSpec(**spec_args)

    @property
    def asset_specs(self):
        """
        Returns the list of asset specs for the SSIS Asset.

        If include_ssis_asset is set to false on creation,
        the asset representing the package itself is not included.
        """
        ssis_asset = [self.ssis_asset_spec] if self._include_ssis_asset else []
        return ssis_asset + self._asset_list


def build_ssis_assets(
    project_name: str,
    package_name: str,
    folder_name: str = "Catalog",
    key_prefix: Sequence[str] = ["SSIS"],
    asset_list: Sequence[str] = [],
    include_ssis_asset: bool = True,
    asset_spec_kwargs: dict[str, Any] | None = None,
):
    """
    Construct an SSIS asset, and bundle together the list of assets provided.
    This places the assets in `asset_list` within the key structure
    of the SSIS asset to allow it to check for events.
    """
    base_key = key_prefix + [
        folder_name,
        project_name,
        package_name.replace(".", "_"),
    ]
    table_specs = []
    asset_spec_kwargs = asset_spec_kwargs if asset_spec_kwargs is not None else {}
    for _asset in asset_list:
        spec_args = asset_spec_kwargs | {
            "key": base_key + [_asset],
        }
        _spec = AssetSpec(**spec_args)
        table_specs.append(_spec)

    _asset = SSISAsset(
        project_name=project_name,
        package_name=package_name,
        folder_name=folder_name,
        key_prefix=key_prefix,
        asset_list=table_specs,
        include_ssis_asset=include_ssis_asset,
        asset_spec_kwargs=asset_spec_kwargs,
    )

    return _asset
