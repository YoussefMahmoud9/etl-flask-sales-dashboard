from __future__ import annotations

import re

import pandas as pd
import pyodbc
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

from .config import SqlServerConfig


class DatabaseSafetyError(RuntimeError):
    """Raised when a non-empty dedicated database must not be changed automatically."""


def _validate_table_name(table_name: str) -> str:
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", table_name):
        raise ValueError(f"Unsafe SQL table name: {table_name!r}")
    return table_name


def _odbc_connection_string(config: SqlServerConfig, database: str) -> str:
    if not config.is_complete:
        raise ValueError("SQL Server environment variables are incomplete.")
    if config.trusted_connection:
        return (
            f"DRIVER={{{config.driver}}};SERVER={config.server};"
            f"DATABASE={database};Trusted_Connection=yes;"
        )
    return (
        f"DRIVER={{{config.driver}}};SERVER={config.server};DATABASE={database};"
        f"UID={config.username};PWD={config.password};"
    )


def inspect_target_database(config: SqlServerConfig) -> dict[str, object]:
    """Inspect only the dedicated database before any create/load operation."""
    with pyodbc.connect(_odbc_connection_string(config, "master"), timeout=10) as connection:
        cursor = connection.cursor()
        cursor.execute(
            "SELECT name, state_desc, user_access_desc "
            "FROM sys.databases WHERE name = ?",
            config.database,
        )
        database = cursor.fetchone()
        if database is None:
            return {"exists": False, "tables": []}

        cursor.execute(
            "SELECT s.name AS schema_name, t.name AS table_name, "
            "SUM(p.rows) AS row_count "
            "FROM [" + config.database.replace("]", "]]") + "].sys.tables AS t "
            "JOIN [" + config.database.replace("]", "]]") + "].sys.schemas AS s ON s.schema_id = t.schema_id "
            "JOIN [" + config.database.replace("]", "]]") + "].sys.partitions AS p ON p.object_id = t.object_id "
            "AND p.index_id IN (0, 1) "
            "GROUP BY s.name, t.name ORDER BY s.name, t.name"
        )
        tables = [
            {"schema": row.schema_name, "table": row.table_name, "row_count": int(row.row_count or 0)}
            for row in cursor.fetchall()
        ]
        return {
            "exists": True,
            "state": database.state_desc,
            "user_access": database.user_access_desc,
            "tables": tables,
        }


def ensure_target_database(config: SqlServerConfig) -> dict[str, object]:
    inspection = inspect_target_database(config)
    if not inspection["exists"]:
        with pyodbc.connect(_odbc_connection_string(config, "master"), timeout=10, autocommit=True) as connection:
            database_name = config.database.replace("]", "]]")
            connection.execute(f"CREATE DATABASE [{database_name}]")
        return {"exists": True, "created": True, "tables": []}

    tables = inspection["tables"]
    if tables:
        table_summary = ", ".join(
            f"{table['schema']}.{table['table']} ({table['row_count']} rows)" for table in tables
        )
        raise DatabaseSafetyError(
            f"{config.database} already contains user tables: {table_summary}. "
            "No database or table changes were made. Review and approve reuse explicitly."
        )
    return {**inspection, "created": False}


def create_sql_server_engine(config: SqlServerConfig):
    if not config.is_complete:
        raise ValueError("SQL Server environment variables are incomplete.")
    return create_engine(config.connection_url(), fast_executemany=True)


def load_sales_to_sql_server(sales: pd.DataFrame, config: SqlServerConfig, table_name: str = "Sales") -> int:
    _validate_table_name(table_name)
    ensure_target_database(config)
    engine = create_sql_server_engine(config)
    with engine.begin() as connection:
        sales.to_sql(table_name, connection, if_exists="fail", index=False)
    return len(sales)


def read_sales_from_sql_server(config: SqlServerConfig, table_name: str = "Sales") -> pd.DataFrame:
    _validate_table_name(table_name)
    engine = create_sql_server_engine(config)
    try:
        with engine.connect() as connection:
            return pd.read_sql(
                text(f"SELECT order_id, customer, product, quantity, unit_price, total_amount FROM [{table_name}]"),
                connection,
            )
    except SQLAlchemyError as exc:
        raise RuntimeError(f"Could not read SQL Server table {table_name}: {exc}") from exc
