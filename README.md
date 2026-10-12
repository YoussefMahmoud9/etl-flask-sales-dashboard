# ETL Flask Sales Dashboard

Python 3.12 project for the DEPI ETL assignment. It reads customers, orders, and products data, validates and cleans the inputs, builds the required Sales table, and provides a Flask dashboard.

## Setup

```powershell
cd E:\Depi\Techincal\DEPI-Projects\etl-flask-sales-dashboard
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

## Data

Input files are stored in `data/`:

- `customers.csv`
- `orders.parquet`
- `products.csv`

The input files are kept locally and are excluded from the public repository because `customers.csv` contains customer names and email fields. Place the three assignment files in `data/` before running the pipeline. The original assignment files outside this project are not modified.

## Run The ETL

Preview the Sales table and data-quality report without loading SQL Server:

```powershell
$env:PYTHONPATH = "src"
python -m sales_dashboard.run_etl
```

Load SQL Server after `.env` is configured and the database connection is authorized:

```powershell
$env:PYTHONPATH = "src"
python -m sales_dashboard.run_etl --load-sql-server
```

## SQL Server Configuration

The verified local configuration for this assignment uses SQL Server Express and Windows Authentication. Keep the real settings in `.env`; `.gitignore` excludes that file. Public examples use placeholders for the server and Windows account.

```text
SQLSERVER_SERVER=YOUR_SQL_SERVER_INSTANCE
SQLSERVER_DATABASE=DEPI_Sales
SQLSERVER_AUTH_MODE=trusted
SQLSERVER_DRIVER=ODBC Driver 17 for SQL Server
```

Required variables:

- `SQLSERVER_DRIVER`
- `SQLSERVER_SERVER`
- `SQLSERVER_DATABASE`
- `SQLSERVER_AUTH_MODE`

The loader uses `mssql+pyodbc` with `Trusted_Connection=yes`; no SQL username or password is required.

The load command checks the dedicated database before writing. It creates `DEPI_Sales` only when it is missing, reuses it only when it has no user tables, and refuses to modify an existing database containing tables. The `Sales` table is created with `if_exists="fail"`, never replaced automatically.

After loading, these read-only queries verify the result in SSMS:

```sql
SELECT name, state_desc
FROM sys.databases
WHERE name = N'DEPI_Sales';

USE DEPI_Sales;

SELECT TABLE_SCHEMA, TABLE_NAME
FROM INFORMATION_SCHEMA.TABLES
WHERE TABLE_NAME = N'Sales';

SELECT COLUMN_NAME, DATA_TYPE
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_NAME = N'Sales'
ORDER BY ORDINAL_POSITION;

SELECT COUNT(*) AS row_count,
       COUNT(DISTINCT order_id) AS distinct_order_count,
       SUM(total_amount) AS total_sales
FROM dbo.Sales;

SELECT order_id, quantity, unit_price, total_amount
FROM dbo.Sales
WHERE total_amount <> quantity * unit_price;
```

## Start Flask

```powershell
$env:PYTHONPATH = "src"
python -m flask --app sales_dashboard.app run --host 127.0.0.1 --port 5057
```

When SQL Server is configured, the dashboard reads the live `Sales` table. Without SQL Server configuration, or if the database cannot be reached, it shows clearly labeled development demo data and the error message.

## Run Tests

```powershell
python -m pytest
```

The tests cover cleaning, validation, join cardinality, and final Sales schema. They do not require a live SQL Server.

## Verified Local Result

With the local assignment inputs and SQL Server Express configuration, the ETL produced and loaded 10 Sales rows. The live verification matched the ETL output exactly, with total sales of `138000.0`, no NULL required fields, no duplicate order IDs, and no `total_amount` mismatches. These local database details are documented generically here; machine-specific names and accounts are not published.
