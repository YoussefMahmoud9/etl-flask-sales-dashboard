from __future__ import annotations

import pandas as pd


def demo_sales_data() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"order_id": 1001, "customer": "Demo Customer", "product": "Laptop", "quantity": 2, "unit_price": 25000.0, "total_amount": 50000.0},
            {"order_id": 1002, "customer": "Demo Buyer", "product": "Mouse", "quantity": 1, "unit_price": 500.0, "total_amount": 500.0},
            {"order_id": 1003, "customer": "Demo Analyst", "product": "Monitor", "quantity": 1, "unit_price": 7000.0, "total_amount": 7000.0},
        ]
    )
