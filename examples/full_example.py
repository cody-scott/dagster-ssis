import dagster as dg

from dagster_ssis import (
    MSSQLJobAsset,
    SQLServerResource,
    build_mssql_job_asset_sensor,
    build_ssis_asset_sensor,
    build_ssis_assets,
)

my_db_resource = SQLServerResource(
    host='localhost',
    database='MyDB',
    username='...',
    password='...',
    query_props={
        "driver": "ODBC Driver 18 for SQL Server",
        "TrustServerCertificate": "yes",
    }
)

ssis_asset_a = build_ssis_assets(
    project_name='Project',
    package_name='Package.dtsx',
    asset_list=['my_table', 'my_other_table'],
    asset_spec_kwargs={
        'owner': 'someone',
        'skippable': True,
        'metadata': {
            'my_meta': 'data'
        }
    }
)

ssis_asset_b = build_ssis_assets(
    project_name='Project2',
    package_name='Package.dtsx',
    asset_list=['something_else'],
    asset_spec_kwargs={
        'owner': 'someone',
        'skippable': True,
        'metadata': {
            'my_meta': 'data'
        }
    }
)

# a single job sensor
job_assets = MSSQLJobAsset(
    'job_name'
)

# tie ssis assets to a job exeuction check
# you probably want to exclude checking using ssis and use the job instead if adding ssis assets
ssis_job_assets = MSSQLJobAsset(
    'job_name_ssis',
    asset_list=ssis_asset_b.asset_specs
)

# only check for a, as b is now tied to a job sensor
ssis_sensor = build_ssis_asset_sensor(
    ssis_assets=[ssis_asset_a],
    sensor_name='ssis_sensor',
    database_resource_key='my_db_resource'
)

mssql_job_sensor = build_mssql_job_asset_sensor(
    [job_assets, ssis_job_assets],
    sensor_name='mssql_job_sensor',
    database_resource_key='my_db_resource'
)

dg.Definition(
    # add all the assets. only add either ssis_asset_b or the job specs otherwise it will find duplicates 
    assets=ssis_asset_a.asset_specs + ssis_job_assets.asset_specs + job_assets.asset_specs,
    sensors=[ssis_sensor, mssql_job_sensor],
    resources={
        'my_db_resource': my_db_resource
    }
)
