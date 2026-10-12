from __future__ import annotations

import argparse

from .config import DEFAULT_CUSTOMERS_PATH, DEFAULT_ORDERS_PATH, DEFAULT_PRODUCTS_PATH, load_sql_server_config
from .db import load_sales_to_sql_server
from .etl import run_pipeline


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Sales ETL pipeline.")
    parser.add_argument("--customers", default=DEFAULT_CUSTOMERS_PATH)
    parser.add_argument("--orders", default=DEFAULT_ORDERS_PATH)
    parser.add_argument("--products", default=DEFAULT_PRODUCTS_PATH)
    parser.add_argument("--load-sql-server", action="store_true", help="Load the Sales table into SQL Server using .env configuration.")
    args = parser.parse_args()

    sales, report = run_pipeline(args.customers, args.orders, args.products)
    print(f"Sales rows produced: {len(sales)}")
    print("Sales columns:", ", ".join(sales.columns))
    print("Data quality report:", report.summary() or "no issues")
    print(sales.to_string(index=False))

    if args.load_sql_server:
        config = load_sql_server_config()
        loaded = load_sales_to_sql_server(sales, config)
        print(f"Loaded {loaded} rows into SQL Server Sales table.")
    else:
        print("SQL Server load skipped. Pass --load-sql-server only after configuration and authorization.")


if __name__ == "__main__":
    main()
