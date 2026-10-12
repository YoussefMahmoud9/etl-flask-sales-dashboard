from __future__ import annotations

from flask import Flask, render_template

from .config import PROJECT_ROOT, load_sql_server_config
from .db import read_sales_from_sql_server
from .sample import demo_sales_data


def create_app() -> Flask:
    app = Flask(
        __name__,
        template_folder=str(PROJECT_ROOT / "templates"),
        static_folder=str(PROJECT_ROOT / "static"),
    )

    @app.get("/")
    def dashboard():
        config = load_sql_server_config()
        mode = "SQL Server"
        error = None

        if config.is_complete:
            try:
                sales = read_sales_from_sql_server(config)
            except Exception as exc:
                sales = demo_sales_data()
                mode = "Development demo data"
                error = str(exc)
        else:
            sales = demo_sales_data()
            mode = "Development demo data"
            error = "SQL Server is not configured. Set SQLSERVER_* variables in .env to use verified database output."

        total_sales = float(sales["total_amount"].sum()) if not sales.empty else 0.0
        order_count = int(sales["order_id"].nunique()) if not sales.empty else 0
        average_order_value = total_sales / order_count if order_count else 0.0

        return render_template(
            "dashboard.html",
            mode=mode,
            error=error,
            total_sales=total_sales,
            order_count=order_count,
            average_order_value=average_order_value,
            rows=sales.to_dict(orient="records"),
        )

    return app


app = create_app()
