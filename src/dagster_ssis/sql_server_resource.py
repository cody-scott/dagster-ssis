from dagster import ConfigurableResource
from contextlib import contextmanager
from typing import Generator, Any

from sqlalchemy import Connection, create_engine, URL


class SQLServerResource(ConfigurableResource):
    host: str
    database: str
    username: str = None
    password: str = None
    port: int = 1433
    query_props: dict[str, Any]  = {}
    py_driver: str = "mssql+pyodbc"

    @property
    def connection_config(self):
        db_config = dict(
            host=self.host,
            port=self.port,
            database=self.database,
            username=self.username,
            password=self.password,
            query=self.query_props,
            py_driver=self.py_driver,
        )
        return db_config

    @contextmanager
    def connect(self) -> Generator[Connection, None, None]:
        """
        Connects to a Microsoft SQL Server database using the provided configuration.

        Args:
            config (dict): A dictionary containing the connection configuration parameters.
            connection_only (bool, optional): If True, only a connection object is returned. If False, a transactional connection is returned. Defaults to False.

        Yields:
            Connection: A connection object to the Microsoft SQL Server database.

        """
        connection_url = self.generate_connection_url(self.connection_config)

        with create_engine(connection_url, hide_parameters=True).connect() as conn:
            yield conn



    def generate_connection_url(self, config):
        connection_url = URL(
            config['py_driver'],
            username=config.get("username"),
            password=config.get("password"),
            host=config.get("host"),
            port=config.get("port"),
            database=config.get("database"),
            query=config.get('query'),
        )

        return connection_url
