import datetime
import json
from textwrap import dedent

from dagster import (
    AssetMaterialization,
    MetadataValue,
    SensorEvaluationContext,
    SensorResult,
    sensor,
)

from dagster_ssis.sql_server_resource import SQLServerResource

from .ssis_assets import SSISAsset

from typing import Sequence


def build_ssis_asset_sensor(
    ssis_assets: Sequence[SSISAsset],
    sensor_name: str,
    database_resource_key: str,
    minimum_interval_seconds: int = 60,
):
    """
    Return a sensor that checks for the status of the SSIS packages
    Sensor will return materialization events for the assets defined in
    `SSISAsset.asset_list`
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

        fqn_dict = {_.fqn: _ for _ in ssis_assets}
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
            fqn = item[0]
            start_time = item[5]
            end_time = item[6]
            execution_time = item[7]
            execution_id = item[8]

            # get the asset from the provided set
            asset_obj = fqn_dict.get(fqn)
            if asset_obj is None:
                continue

            dt_format = "%Y-%m-%d %H:%M:%S.%f %z"

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

                for _asset in asset_obj.asset_specs:
                    asset_materialization = AssetMaterialization(
                        _asset.key,
                        metadata=dict(
                            folder_name=asset_obj._folder_name,
                            project_name=asset_obj._project_name,
                            package_name=asset_obj._package_name,
                            start_time=MetadataValue.timestamp(start_time),
                            end_time=MetadataValue.timestamp(end_time),
                            duration_in_seconds=execution_time,
                            execution_id=execution_id,
                        ),
                    )
                    materializations_to_trigger.append(asset_materialization)

            new_cursor_state[fqn] = cursor_time

        context.update_cursor(json.dumps(new_cursor_state))

        for _ in cursor:
            if _ not in new_cursor_state:
                new_cursor_state[_] = cursor[_]

        return SensorResult(asset_events=materializations_to_trigger)

    return _sensor


def get_packages_state(connection):
    """Returns the state of packages that have succeeded for comparison to last state"""
    sql = dedent(
        """
        with base as (
            select
                folder_name + '/' + project_name + '/' + package_name as fqn,
                folder_name,
                project_name,
                package_name,
                status,
                convert(datetimeoffset(6), start_time) as start_time,
                convert(datetimeoffset(6), end_time) as end_time,
                DATEDIFF(SECOND, start_time, end_time) as execution_in_seconds,
                execution_id
            from
                ssisdb.catalog.executions
        ),

        rt as (
            select
                folder_name,
                project_name,
                package_name,
                max(end_time) last_run_time
            from 
                base
            where status = 7 or status = 9
            group by
                folder_name,
                project_name,
                package_name
        )

        select distinct base.*
        from 
            base
        inner join
            rt
            on
                base.folder_name = rt.folder_name
                and
                base.project_name = rt.project_name
                and
                base.package_name = rt.package_name
                and
                base.end_time = rt.last_run_time
        """.strip()
    )

    result = connection.exec_driver_sql(sql)
    if result is None:
        return None

    return result.fetchall()
