from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd


SALES_COLUMNS = ["order_id", "customer", "product", "quantity", "unit_price", "total_amount"]


@dataclass
class DataQualityReport:
    issues: dict[str, pd.DataFrame] = field(default_factory=dict)

    def add(self, name: str, frame: pd.DataFrame) -> None:
        if not frame.empty:
            self.issues[name] = frame.copy()

    @property
    def has_issues(self) -> bool:
        return bool(self.issues)

    def summary(self) -> dict[str, int]:
        return {name: len(frame) for name, frame in self.issues.items()}


def extract_customers(path: str | Path) -> pd.DataFrame:
    return pd.read_csv(path)


def extract_orders(path: str | Path) -> pd.DataFrame:
    return pd.read_parquet(path)


def extract_products(path: str | Path) -> pd.DataFrame:
    return pd.read_csv(path)


def clean_customers(customers: pd.DataFrame, report: DataQualityReport) -> pd.DataFrame:
    df = customers.copy()
    df["customer_id"] = pd.to_numeric(df["customer_id"], errors="coerce").astype("Int64")
    df["age"] = pd.to_numeric(df["age"], errors="coerce")
    for column in ["first_name", "last_name", "city", "email"]:
        df[column] = df[column].fillna("").astype(str).str.strip()

    report.add("duplicate_customer_rows", df[df.duplicated()])
    report.add("duplicate_customer_ids", df[df["customer_id"].duplicated(keep=False)])
    report.add("invalid_customer_age", df[df["age"].isna() | df["age"].lt(18) | df["age"].gt(120)])
    report.add("missing_customer_email", df[df["email"].eq("")])

    cleaned = df.drop_duplicates().copy()
    cleaned = cleaned[cleaned["customer_id"].notna()]
    cleaned = cleaned.drop_duplicates(subset=["customer_id"], keep="first")
    cleaned["city"] = cleaned["city"].str.title()
    cleaned["email"] = cleaned["email"].replace("", "unknown@example.com")
    cleaned["full_name"] = (cleaned["first_name"] + " " + cleaned["last_name"]).str.strip()
    return cleaned


def clean_orders(orders: pd.DataFrame, valid_customer_ids: set[int], report: DataQualityReport) -> pd.DataFrame:
    df = orders.copy()
    for column in ["order_id", "customer_id", "product_id", "quantity"]:
        df[column] = pd.to_numeric(df[column], errors="coerce").astype("Int64")
    df["order_date"] = pd.to_datetime(df["order_date"], errors="coerce")

    report.add("duplicate_order_ids", df[df["order_id"].duplicated(keep=False)])
    report.add("invalid_order_quantity", df[df["quantity"].isna() | df["quantity"].le(0)])
    report.add("invalid_order_date", df[df["order_date"].isna()])
    report.add("orders_with_invalid_customer_id", df[~df["customer_id"].isin(valid_customer_ids)])

    cleaned = df.drop_duplicates(subset=["order_id"], keep="first").copy()
    cleaned = cleaned[
        cleaned["order_id"].notna()
        & cleaned["customer_id"].notna()
        & cleaned["product_id"].notna()
        & cleaned["quantity"].gt(0)
        & cleaned["order_date"].notna()
    ]
    cleaned = cleaned[cleaned["customer_id"].isin(valid_customer_ids)]
    return cleaned


def clean_products(products: pd.DataFrame, report: DataQualityReport) -> pd.DataFrame:
    df = products.copy()
    df["product_id"] = pd.to_numeric(df["product_id"], errors="coerce").astype("Int64")
    df["unit_price"] = pd.to_numeric(df["unit_price"], errors="coerce")
    for column in ["product_name", "category"]:
        df[column] = df[column].fillna("").astype(str).str.strip()

    report.add("duplicate_product_rows", df[df.duplicated()])
    report.add("duplicate_product_ids", df[df["product_id"].duplicated(keep=False)])
    report.add("invalid_product_price", df[df["unit_price"].isna() | df["unit_price"].le(0)])

    cleaned = df.drop_duplicates().copy()
    cleaned = cleaned.drop_duplicates(subset=["product_id"], keep="first")
    cleaned = cleaned[cleaned["product_id"].notna() & cleaned["unit_price"].gt(0)]
    cleaned["product_name"] = cleaned["product_name"].str.title()
    cleaned["category"] = cleaned["category"].str.title()
    return cleaned


def validate_join_keys(orders: pd.DataFrame, customers: pd.DataFrame, products: pd.DataFrame, report: DataQualityReport) -> None:
    report.add("orders_unmatched_customers", orders[~orders["customer_id"].isin(set(customers["customer_id"]))])
    report.add("orders_unmatched_products", orders[~orders["product_id"].isin(set(products["product_id"]))])

    if customers["customer_id"].duplicated().any():
        raise ValueError("Customer join key is not unique after cleaning.")
    if products["product_id"].duplicated().any():
        raise ValueError("Product join key is not unique after cleaning.")
    if orders["order_id"].duplicated().any():
        raise ValueError("Order key is not unique after cleaning.")


def build_sales_table(orders: pd.DataFrame, customers: pd.DataFrame, products: pd.DataFrame, report: DataQualityReport) -> pd.DataFrame:
    validate_join_keys(orders, customers, products, report)
    matched_orders = orders[
        orders["customer_id"].isin(set(customers["customer_id"]))
        & orders["product_id"].isin(set(products["product_id"]))
    ].copy()

    sales = matched_orders.merge(
        customers[["customer_id", "full_name"]],
        on="customer_id",
        how="left",
        validate="many_to_one",
    ).merge(
        products[["product_id", "product_name", "unit_price"]],
        on="product_id",
        how="left",
        validate="many_to_one",
    )
    sales["total_amount"] = sales["quantity"].astype(float) * sales["unit_price"].astype(float)
    sales = sales.rename(columns={"full_name": "customer", "product_name": "product"})
    return sales[SALES_COLUMNS].sort_values("order_id").reset_index(drop=True)


def run_pipeline(customers_path: str | Path, orders_path: str | Path, products_path: str | Path) -> tuple[pd.DataFrame, DataQualityReport]:
    report = DataQualityReport()
    customers = clean_customers(extract_customers(customers_path), report)
    orders = clean_orders(extract_orders(orders_path), set(customers["customer_id"]), report)
    products = clean_products(extract_products(products_path), report)
    sales = build_sales_table(orders, customers, products, report)
    return sales, report
