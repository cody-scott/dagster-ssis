import datetime
import json
import zoneinfo
from textwrap import dedent

from dagster import (
    AssetMaterialization,
    MetadataValue,
    SensorEvaluationContext,
    SensorResult,
    sensor,
)

from dagster_ssis.sql_server_resource import SQLServerResource

from .mssql_job_assets import MSSQLJobAsset

from typing import Sequence


def build_mssql_job_asset_sensor(
    job_assets: Sequence[MSSQLJobAsset],
    sensor_name: str,
    database_resource_key: str,
    minimum_interval_seconds: int = 60,
):
    """
    Return a sensor that checks for the status of the MSSQL Jobs
    Sensor will return materialization events for the assets defined in
    `MSSQLJobAsset.asset_list`
    """

    @sensor(
        name=sensor_name,
        minimum_interval_seconds=minimum_interval_seconds,
        required_resource_keys={database_resource_key},
    )
    def _sensor(context: SensorEvaluationContext):
        """
        cursor will be fqn of the ssis package + last runtime
        """
        db_resource: SQLServerResource = context.resources.original_resource_dict[
            database_resource_key
        ]  # type: ignore

        fqn_dict = {_.fqn: _ for _ in job_assets}
        cursor = context.cursor
        if cursor is None:
            cursor = {}
        else:
            cursor = json.loads(cursor)

        with db_resource.connect() as connection:
            new_state = get_packages_state(connection)

        # if the state is none bail out
        if new_state is None:
            context.update_cursor(json.dumps(cursor))
            return

        new_cursor_state = {}

        materializations_to_trigger = []

        for item in new_state:
            fqn = item[1]
            start_time: datetime.datetime = item[5]
            end_time: datetime.datetime = item[6]
            execution_time = item[7]
            instance_id = item[3]

            # get the asset from the provided set
            asset_obj = fqn_dict.get(fqn)
            if asset_obj is None:
                continue

            dt_format = "%Y-%m-%d %H:%M:%S.%f"

            last_time_str = cursor.get(fqn)
            if last_time_str is None:
                new_cursor_state[fqn] = end_time.strftime(dt_format)
                continue

            last_time = datetime.datetime.strptime(last_time_str, dt_format)
            current_time = end_time

            cursor_time = last_time_str
            if current_time > last_time:
                # add to materializations_to_trigger
                cursor_time = end_time.strftime(dt_format)
                tz = zoneinfo.ZoneInfo("America/Toronto")
                for _asset in asset_obj.asset_specs:
                    asset_materialization = AssetMaterialization(
                        _asset.key,
                        metadata=dict(
                            job_name=asset_obj._job_name,
                            start_time=MetadataValue.timestamp(
                                start_time.replace(tzinfo=tz)
                            ),
                            end_time=MetadataValue.timestamp(
                                end_time.replace(tzinfo=tz)
                            ),
                            duration_in_seconds=execution_time,
                            instance_id=instance_id,
                        ),
                    )
                    materializations_to_trigger.append(asset_materialization)

            new_cursor_state[fqn] = cursor_time

        for _ in cursor:
            if _ not in new_cursor_state:
                new_cursor_state[_] = cursor[_]

        context.update_cursor(json.dumps(new_cursor_state))

        return SensorResult(asset_events=materializations_to_trigger)

    return _sensor


def get_packages_state(connection):
    """Returns the state of packages that have succeeded for comparison to last state"""
    sql = dedent(
        """
        WITH job_table AS (
            SELECT 
                job_id,
                name,
                enabled
        FROM [msdb].[dbo].[sysjobs]
        ),

        job_history AS (
            SELECT
                instance_id,
                job_id,
                run_status,
                shp.run_start,
                DATEADD(SECOND, shp.run_duration, shp.run_start) AS run_end,
                shp.run_duration
            FROM
                msdb.dbo.sysjobhistory

            CROSS APPLY (
                SELECT 
                    DATETIME2FROMPARTS(
                        run_date / 10000, -- years
                        run_date % 10000 / 100, -- months
                        run_date % 100, -- days
                        run_time / 10000, -- hours
                        run_time % 10000 / 100, -- minutes
                        run_time % 100, -- seconds
                        0, -- milliseconds,
                        6
                    ) AS run_start,
                    (
                        (run_duration / 10000) * 3600 -- convert hours to seconds, can be greater than 24
                        + ((run_duration % 10000) / 100) * 60 -- convert minutes to seconds
                        + (run_duration % 100) 
                    ) AS run_duration
                ) AS shp
            WHERE
                step_id = 0
                AND
                run_status = 1
        ),

        joined AS (
            SELECT
                job_table.job_id,
                job_table.name,
                job_table.enabled,
                job_history.instance_id,
                job_history.run_status,
                job_history.run_start,
                job_history.run_end,
                job_history.run_duration
            FROM
                job_table	
            INNER JOIN
                job_history
                ON
                    job_table.job_id = job_history.job_id
        ),

        last_run AS (
            SELECT
                job_id,
                MAX(run_end) as last_run_end
            FROM
                joined
            GROUP BY
                job_id
        )

        SELECT
            joined.*
        FROM
            joined
        INNER JOIN
            last_run
            ON
                joined.job_id = last_run.job_id
                AND
                joined.run_end = last_run.last_run_end
        """.strip()
    )

    result = connection.exec_driver_sql(sql)
    if result is None:
        return None

    return result.fetchall()
