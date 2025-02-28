from dagster import AssetSpec
from dagster_ssis import SSISAsset, build_ssis_assets, build_ssis_asset_sensor

# Create a single SSIS Asset representing multiple other assets, such as table in MSSQL, or a stored proceedure
# This pattern is good if the asset should be defined differently then the package itself.

table_assets = [AssetSpec(key="my_table"), AssetSpec(key="my_other_table")]

ssis_asset = SSISAsset(
    project_name="Project", package_name="Package.dtsx", asset_list=table_assets
)
# get the list of all the assets, including the package asset
asset_spec = ssis_asset.asset_specs


# or

# using helper function `build_ssis_assets`, produce the same as above
# this assigns the key of the sub assets to the ssis path

# Good for composing the ssis package and all related assets together
ssis_asset = build_ssis_assets(
    project_name="Project",
    package_name="Package.dtsx",
    asset_list=["my_table", "my_other_table"],
)

# get the list of all the assets, including the package asset
asset_spec = ssis_asset.asset_specs


sensor_def = build_ssis_asset_sensor(
    ssis_assets=[ssis_asset],
    sensor_name="ssis_sensor",
    database_resource_key="my_db_resource",
)
