from __future__ import annotations

import os
from unittest.mock import patch

import pandas as pd

from sales_dashboard.app import create_app


SALES_COLUMNS = ["order_id", "customer", "product", "quantity", "unit_price", "total_amount"]


def test_dashboard_handles_empty_sql_server_result():
    os.environ["SQLSERVER_SERVER"] = "server"
    os.environ["SQLSERVER_DATABASE"] = "database"
    os.environ["SQLSERVER_AUTH_MODE"] = "trusted"

    app = create_app()
    client = app.test_client()
    empty_sales = pd.DataFrame(columns=SALES_COLUMNS)

    with patch("sales_dashboard.app.read_sales_from_sql_server", return_value=empty_sales):
        response = client.get("/")

    html = response.get_data(as_text=True)
    assert response.status_code == 200
    assert "0.00" in html
    assert "No sales rows available." in html


def test_dashboard_falls_back_to_labeled_demo_data_on_database_error():
    os.environ["SQLSERVER_SERVER"] = "server"
    os.environ["SQLSERVER_DATABASE"] = "database"
    os.environ["SQLSERVER_AUTH_MODE"] = "trusted"

    app = create_app()
    client = app.test_client()

    with patch("sales_dashboard.app.read_sales_from_sql_server", side_effect=RuntimeError("simulated db failure")):
        response = client.get("/")

    html = response.get_data(as_text=True)
    assert response.status_code == 200
    assert "Development demo data" in html
    assert "simulated db failure" in html
