from dagster_ssis.ssis import ssis_assets

from dagster_ssis import mssql_jobs
from dagster_ssis.mssql_jobs import mssql_job_sensor
from dagster import DagsterInstance, build_sensor_context, Definitions
import datetime

from unittest import mock

run_1_data = [
    (
        "71062765-4DDF-4EDE-A396-B804F7CD05AC",
        "TESTJOB",
        1,
        108956,
        1,
        datetime.datetime(2024, 11, 26, 1, 0, 0, 0),
        datetime.datetime(2024, 11, 26, 1, 2, 52, 0),
        172,
    )
]
run_2_data = run_1_data
run_3_data = [
    (
        "71062765-4DDF-4EDE-A396-B804F7CD05AC",
        "TESTJOB",
        1,
        108957,
        1,
        datetime.datetime(2024, 11, 27, 1, 0, 0, 0),
        datetime.datetime(2024, 11, 27, 1, 2, 52, 0),
        172,
    )
]
run_4_data = []


def test_mssql_job(monkeypatch, io_resources_fixture, test_db):
    rsc_mock = mock.Mock()
    rsc_mock.side_effect = [run_1_data, run_2_data, run_3_data, run_4_data]
    monkeypatch.setattr(mssql_job_sensor, "get_packages_state", rsc_mock)

    assets = mssql_jobs.build_mssql_job_assets(
        job_name="TESTJOB",
        asset_list=["dataset.schema__table", "dataset.schema__table2"],
        include_job_asset=False,
    )
    assert len(assets.asset_specs) == 2

    assets = mssql_jobs.build_mssql_job_assets(
        job_name="TESTJOB",
        asset_list=["dataset.schema__table", "dataset.schema__table2"],
    )
    assert len(assets.asset_specs) == 3

    _sensor = mssql_jobs.build_mssql_job_asset_sensor(
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
                sensors=[_sensor],
                resources=io_resources_fixture,
            ),
        )

        # first run should be 0
        result = _sensor.evaluate_tick(ctx)
        cursor = result.cursor
        assert len(result.asset_events) == 0

        # next run should have same state so no change
        result = _sensor.evaluate_tick(ctx)
        cursor = result.cursor

        result = _sensor.evaluate_tick(ctx)
        cursor = result.cursor
        assert len(result.asset_events) == 3

        result = _sensor.evaluate_tick(ctx)
        cursor = result.cursor
        cursor = result.cursor


def test_job_with_ssis(monkeypatch, io_resources_fixture, test_db):
    rsc_mock = mock.Mock()
    rsc_mock.side_effect = [run_1_data, run_2_data, run_3_data, run_4_data]
    monkeypatch.setattr(mssql_job_sensor, "get_packages_state", rsc_mock)

    ssis_asset_list = ssis_assets.build_ssis_assets(
        "Project", "Package.dtsx", asset_list=["a", "b", "c", "d"]
    )
    job_asset = mssql_jobs.MSSQLJobAsset(
        "TESTJOB", asset_list=ssis_asset_list.asset_specs, include_job_asset=False
    )

    _sensor = mssql_jobs.build_mssql_job_asset_sensor(
        [job_asset], "test_ssis_sensor", "db_resource"
    )

    results = []
    with DagsterInstance.ephemeral() as instance:
        cursor = None
        ctx = build_sensor_context(
            cursor=cursor,
            instance=instance,
            resources=io_resources_fixture,
            definitions=Definitions(
                assets=job_asset.asset_specs,
                sensors=[_sensor],
                resources=io_resources_fixture,
            ),
        )

        # first run should be 0
        result = _sensor.evaluate_tick(ctx)
        cursor = result.cursor
        assert len(result.asset_events) == 0

        # next run should have same state so no change
        result = _sensor.evaluate_tick(ctx)
        cursor = result.cursor

        result = _sensor.evaluate_tick(ctx)
        cursor = result.cursor
        assert len(result.asset_events) == 5

        result = _sensor.evaluate_tick(ctx)
        cursor = result.cursor
        cursor = result.cursor
