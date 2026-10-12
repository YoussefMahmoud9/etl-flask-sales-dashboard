from __future__ import annotations

import pandas as pd
import pytest

from sales_dashboard.etl import (
    SALES_COLUMNS,
    DataQualityReport,
    build_sales_table,
    clean_customers,
    clean_orders,
    clean_products,
    run_pipeline,
)


def test_customer_cleaning_standardizes_and_reports_issues():
    report = DataQualityReport()
    customers = pd.DataFrame(
        [
            {"customer_id": 1, "first_name": "Ana", "last_name": "Saleh", "city": "cairo", "age": 25, "email": ""},
            {"customer_id": 1, "first_name": "Ana", "last_name": "Saleh", "city": "cairo", "age": 25, "email": ""},
            {"customer_id": 2, "first_name": "Kid", "last_name": "User", "city": "giza", "age": 17, "email": "kid@example.com"},
        ]
    )

    cleaned = clean_customers(customers, report)

    assert cleaned.loc[cleaned["customer_id"] == 1, "city"].item() == "Cairo"
    assert cleaned.loc[cleaned["customer_id"] == 1, "email"].item() == "unknown@example.com"
    assert cleaned.loc[cleaned["customer_id"] == 1, "full_name"].item() == "Ana Saleh"
    assert report.summary()["duplicate_customer_rows"] == 1
    assert report.summary()["missing_customer_email"] == 2
    assert report.summary()["invalid_customer_age"] == 1


def test_order_cleaning_removes_duplicate_invalid_and_bad_customer():
    report = DataQualityReport()
    orders = pd.DataFrame(
        [
            {"order_id": 10, "customer_id": 1, "product_id": 101, "quantity": 2, "order_date": "2026-09-01"},
            {"order_id": 10, "customer_id": 1, "product_id": 101, "quantity": 2, "order_date": "2026-09-01"},
            {"order_id": 11, "customer_id": 99, "product_id": 101, "quantity": 1, "order_date": "2026-09-02"},
            {"order_id": 12, "customer_id": 1, "product_id": 101, "quantity": 0, "order_date": "bad"},
        ]
    )

    cleaned = clean_orders(orders, {1}, report)

    assert cleaned["order_id"].tolist() == [10]
    assert report.summary()["duplicate_order_ids"] == 2
    assert report.summary()["orders_with_invalid_customer_id"] == 1
    assert report.summary()["invalid_order_quantity"] == 1
    assert report.summary()["invalid_order_date"] == 1


def test_products_cleaning_validates_price_and_key_uniqueness():
    report = DataQualityReport()
    products = pd.DataFrame(
        [
            {"product_id": 101, "product_name": "laptop", "category": "electronics", "unit_price": "25000"},
            {"product_id": 101, "product_name": "laptop", "category": "electronics", "unit_price": "25000"},
            {"product_id": 102, "product_name": "mouse", "category": "accessories", "unit_price": "-1"},
        ]
    )

    cleaned = clean_products(products, report)

    assert cleaned["product_name"].tolist() == ["Laptop"]
    assert report.summary()["duplicate_product_rows"] == 1
    assert report.summary()["invalid_product_price"] == 1


def test_build_sales_table_rejects_many_to_many_risk():
    report = DataQualityReport()
    orders = pd.DataFrame([{"order_id": 1, "customer_id": 1, "product_id": 101, "quantity": 1, "order_date": pd.Timestamp("2026-09-01")}])
    customers = pd.DataFrame(
        [
            {"customer_id": 1, "full_name": "A One"},
            {"customer_id": 1, "full_name": "A Duplicate"},
        ]
    )
    products = pd.DataFrame([{"product_id": 101, "product_name": "Laptop", "unit_price": 25000.0}])

    with pytest.raises(ValueError, match="Customer join key"):
        build_sales_table(orders, customers, products, report)


def test_pipeline_outputs_required_schema_with_real_data():
    sales, report = run_pipeline("data/customers.csv", "data/orders.parquet", "data/products.csv")

    assert list(sales.columns) == SALES_COLUMNS
    assert len(sales) == 10
    assert sales.loc[sales["order_id"] == 1001, "total_amount"].item() == 50000.0
    assert report.summary()["duplicate_order_ids"] == 2
    assert "orders_unmatched_customers" not in report.summary()
    assert "orders_unmatched_products" not in report.summary()
