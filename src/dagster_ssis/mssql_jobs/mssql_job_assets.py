from typing import Any, Sequence

from dagster import (
    AssetSpec,
)


class MSSQLJobAsset:
    _job_name: str

    _key_prefix: Sequence[str]
    _asset_list: Sequence[AssetSpec]
    _include_job_asset: bool
    _asset_spec_kwargs: dict[str, Any]

    @property
    def fqn(self):
        return f"{self._job_name}"

    def __init__(
        self,
        job_name: str,
        key_prefix: list[str] = ["MSSQLJobs"],
        asset_list: list[AssetSpec] = [],
        include_job_asset: bool = True,
        asset_spec_kwargs: dict[str, Any] | None = None,
    ):
        """Create an asset representing a MSSQL job.

        Args:
            job_name (str): name of job
            key_prefix (list[str], optional): key prefixes to pass to AssetSpec. Defaults to ["SSIS"].
            asset_list (list[AssetSpec], optional): List of assets associated with the package. Defaults to [].
            include_job_asset (bool, optional): Should the `asset_specs` property include an asset for the package itself. Defaults to True.
            asset_spec_kwargs (dict[str, Any], optional): Parameters to pass to AssetSpec
        """
        self._job_name = job_name

        self._key_prefix = key_prefix
        self._asset_list = asset_list
        self._include_job_asset = include_job_asset

        asset_spec_kwargs = asset_spec_kwargs if asset_spec_kwargs is not None else {}
        self._asset_spec_kwargs = asset_spec_kwargs

    def __repr__(self):
        return self.fqn

    @property
    def job_asset_spec(self):
        key = self._key_prefix + [self._job_name]
        spec_args = self._asset_spec_kwargs | {"key": key}
        return AssetSpec(**spec_args)

    @property
    def asset_specs(self):
        """
        Returns the list of asset specs for the Job Asset.

        If include_job_asset is set to false on creation,
        the asset representing the job itself is not included.
        """
        ssis_asset = [self.job_asset_spec] if self._include_job_asset else []
        return ssis_asset + self._asset_list


def build_mssql_job_assets(
    job_name: str,
    key_prefix: list[str] = ["MSSQLJobs"],
    asset_list: list[str] = [],
    include_job_asset: bool = True,
    asset_spec_kwargs: dict[str, Any] | None = None,
):
    """
    Construct a MSSQLJob asset, and bundle together the list of assets provided.
    This places the assets in `asset_list` within the key structure
    of the job asset to allow it to check for events.
    """
    base_key = key_prefix + [job_name]
    table_specs = []
    asset_spec_kwargs = asset_spec_kwargs if asset_spec_kwargs is not None else {}
    for _asset in asset_list:
        spec_args = asset_spec_kwargs | {
            "key": base_key + [_asset],
        }
        _spec = AssetSpec(**spec_args)
        table_specs.append(_spec)

    _asset = MSSQLJobAsset(
        job_name=job_name,
        key_prefix=key_prefix + [job_name],
        asset_list=table_specs,
        include_job_asset=include_job_asset,
        asset_spec_kwargs=asset_spec_kwargs,
    )

    return _asset
