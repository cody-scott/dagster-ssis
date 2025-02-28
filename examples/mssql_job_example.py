from dagster import AssetSpec
from dagster_ssis import (
    MSSQLJobAsset,
    build_mssql_job_assets,
    build_mssql_job_asset_sensor,
)

# single asset
job_asset = MSSQLJobAsset(
    job_name="job_name",
)

# or adding specific specs to capture alongside
job_asset = MSSQLJobAsset(
    job_name="job_name", asset_list=[AssetSpec("a"), AssetSpec("b")]
)

# or

# single asset from helper with child assets
job_asset = build_mssql_job_assets("job_name", asset_list=["other_asset"])


sensor_def = build_mssql_job_asset_sensor(
    job_assets=[job_asset],
    sensor_name="my_sensor",
    database_resource_key="my_db_resource",
)
