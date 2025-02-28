from dagster_ssis import ssis
from dagster_ssis.sql_server_resource import SQLServerResource
from dagster import DagsterInstance, build_sensor_context, Definitions

table_data = """
CREATE TABLE ssisdb.catalog.executions (
folder_name nvarchar(128),
project_name nvarchar(128),
package_name nvarchar(256),
status int,
start_time datetimeoffset(7),
end_time datetimeoffset(7),
execution_id bigint
)
"""


seed = """
INSERT INTO catalog.executions (
    folder_name,
    project_name,
    package_name,
    status,
    start_time,
    end_time,
    execution_id
)
VALUES
(
    'Catalog','Weather','HourlyClimate.dtsx', 7,'2024-10-17 09:00:01.232371 -04:00','2024-10-17 09:00:03.400390 -04:00',119648
)
"""

seed_new_run = """
INSERT INTO catalog.executions (
    folder_name,
    project_name,
    package_name,
    status,
    start_time,
    end_time,
    execution_id
)
VALUES
(
    'Catalog','Weather','HourlyClimate.dtsx', 7,'2024-10-18 09:00:01.232371 -04:00','2024-10-18 09:00:03.400390 -04:00',119649
)
"""


def test_ssis(io_resources_fixture, test_db: SQLServerResource):
    with test_db.connect() as connection:
        connection.exec_driver_sql("USE ssisdb")
        test_db.create_schema(connection, "catalog")
        test_db.drop_table(connection, "catalog", "executions")
        connection.exec_driver_sql(table_data)

        connection.exec_driver_sql(seed)

    assets = ssis.build_ssis_assets(
        project_name="Weather",
        package_name="HourlyClimate.dtsx",
        asset_list=["dataset.schema__table", "dataset.schema__table2"],
        include_ssis_asset=False,
    )
    assert len(assets.asset_specs) == 2

    assets = ssis.build_ssis_assets(
        project_name="Weather",
        package_name="HourlyClimate.dtsx",
        asset_list=["dataset.schema__table", "dataset.schema__table2"],
    )
    assert len(assets.asset_specs) == 3

    ssis_sensor = ssis.build_ssis_asset_sensor(
        [assets], "test_ssis_sensor", "db_resource"
    )

    results = []
    with DagsterInstance.ephemeral() as instance:
        cursor = None
        ctx = build_sensor_context(
            cursor=cursor,
            instance=instance,
            resources=io_resources_fixture,
            definitions=Definitions(
                assets=assets.asset_specs,
                sensors=[ssis_sensor],
                resources=io_resources_fixture,
            ),
        )

        # first run should be 0
        result = ssis_sensor.evaluate_tick(ctx)
        cursor = result.cursor
        assert len(result.asset_events) == 0

        # next run should have same state so no change
        result = ssis_sensor.evaluate_tick(ctx)
        cursor = result.cursor

        # new run so should trigger events
        with test_db.connect() as connection:
            connection.exec_driver_sql("USE ssisdb")
            connection.exec_driver_sql(seed_new_run)

        result = ssis_sensor.evaluate_tick(ctx)
        cursor = result.cursor
        assert len(result.asset_events) == 3
