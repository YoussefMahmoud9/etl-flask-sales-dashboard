from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy.engine import URL


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
DEFAULT_CUSTOMERS_PATH = DATA_DIR / "customers.csv"
DEFAULT_ORDERS_PATH = DATA_DIR / "orders.parquet"
DEFAULT_PRODUCTS_PATH = DATA_DIR / "products.csv"


@dataclass(frozen=True)
class SqlServerConfig:
    driver: str
    server: str
    database: str
    trusted_connection: bool = False
    username: str | None = None
    password: str | None = None

    @property
    def is_complete(self) -> bool:
        if not self.driver or not self.server or not self.database:
            return False
        if self.trusted_connection:
            return True
        return bool(self.username and self.password)

    def connection_url(self) -> URL:
        if not self.is_complete:
            raise ValueError("SQL Server configuration is incomplete.")

        query = {"driver": self.driver}
        if self.trusted_connection:
            query["Trusted_Connection"] = "yes"

        return URL.create(
            "mssql+pyodbc",
            username=None if self.trusted_connection else self.username,
            password=None if self.trusted_connection else self.password,
            host=self.server,
            database=self.database,
            query=query,
        )


def load_sql_server_config(env_file: str | Path | None = None) -> SqlServerConfig:
    if env_file:
        load_dotenv(env_file)
    else:
        load_dotenv(PROJECT_ROOT / ".env")

    auth_mode = os.getenv("SQLSERVER_AUTH_MODE", "").strip().lower()
    trusted = auth_mode in {"trusted", "windows", "integrated"}
    return SqlServerConfig(
        driver=os.getenv("SQLSERVER_DRIVER", "ODBC Driver 17 for SQL Server").strip(),
        server=os.getenv("SQLSERVER_SERVER", "").strip(),
        database=os.getenv("SQLSERVER_DATABASE", "").strip(),
        trusted_connection=trusted,
        username=os.getenv("SQLSERVER_USERNAME") or None,
        password=os.getenv("SQLSERVER_PASSWORD") or None,
    )
