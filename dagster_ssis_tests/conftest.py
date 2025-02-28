import os
from contextlib import contextmanager
from typing import Generator

import pytest
from sqlalchemy import URL, Connection, create_engine

from dagster_ssis import SQLServerResource


class TestDBConnection:
    host: str
    port: str
    database: str
    username: str
    password: str

    def __init__(self):
        self.host = os.environ["TARGET_DB__HOST"]
        self.port = os.environ["TARGET_DB__PORT"]
        self.database = os.environ["TARGET_DB__DATABASE"]
        self.username = os.environ["TARGET_DB__USERNAME"]
        self.password = os.environ["TARGET_DB__PASSWORD"]

    @property
    def connection_config(self):
        db_config = dict(
            host=self.host,
            port=self.port,
            database=self.database,
            username=self.username,
            password=self.password,
        )
        return db_config

    @contextmanager
    def connect(self, connection_only=False) -> Generator[Connection, None, None]:
        """
        Connects to a Microsoft SQL Server database using the provided configuration.

        Args:
            config (dict): A dictionary containing the connection configuration parameters.
            connection_only (bool, optional): If True, only a connection object is returned. If False, a transactional connection is returned. Defaults to False.

        Yields:
            Connection: A connection object to the Microsoft SQL Server database.

        """
        connection_url = self.generate_connection_url(self.connection_config)

        conn = None
        if connection_only:
            with create_engine(connection_url, hide_parameters=True).connect() as conn:
                yield conn
        else:
            with create_engine(
                connection_url, fast_executemany=True, hide_parameters=True
            ).begin() as conn:
                yield conn

    def generate_connection_url(self, config):
        connection_url = URL(
            "mssql+pyodbc",
            username=config.get("username"),
            password=config.get("password"),
            host=config.get("host"),
            port=int(config.get("port", "1433")),
            database=config.get("database"),
            query={
                "driver": "ODBC Driver 18 for SQL Server",
                "TrustServerCertificate": "yes",
            },  # type: ignore
        )

        return connection_url

    def drop_table(self, connection: Connection, schema, table):
        connection.exec_driver_sql(f"DROP TABLE IF EXISTS {schema}.{table}")

    def drop_tables(self, connection: Connection, schema: str, tables: list[str]):
        for _ in tables:
            self.drop_table(connection, schema, _)

    def drop_view(self, connection: Connection, schema, table):
        connection.exec_driver_sql(f"DROP VIEW IF EXISTS {schema}.{table}")

    def create_schema(self, connection: Connection, schema_name: str):
        create_schema = f"""
        IF NOT EXISTS (SELECT * FROM sys.schemas WHERE name = '{schema_name}')
        BEGIN
            EXEC('CREATE SCHEMA {schema_name}')
        END
        """
        connection.exec_driver_sql(create_schema)


@pytest.fixture
def test_db():
    yield TestDBConnection()


@pytest.fixture
def io_resources_fixture():
    """Returns a dict of the standard io managers"""
    host = os.environ["TARGET_DB__HOST"]
    port = os.environ["TARGET_DB__PORT"]
    database = os.environ["TARGET_DB__DATABASE"]
    username = os.environ["TARGET_DB__USERNAME"]
    password = os.environ["TARGET_DB__PASSWORD"]
    return {
        "db_resource": SQLServerResource(
            host=host,
            port=port,
            database=database,
            username=username,
            password=password,
            query_props={
                "driver": "ODBC Driver 18 for SQL Server",
                "TrustServerCertificate": "yes",
            },
        ),
    }
